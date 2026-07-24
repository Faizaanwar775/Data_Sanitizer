from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cleaning.date_cleaner import clean_date
from cleaning.email_cleaner import clean_email
from cleaning.name_cleaner import clean_name
from cleaning.phone_cleaner import clean_phone
from dedupe.dedupe import remove_duplicates, remove_exact_duplicates
from io_ops.reader import read_raw_rows
from io_ops.writer import write_clean_csv, write_rejected_csv
from reporting.audit import audit_raw_rows, format_audit_report
from reporting.summary import log_summary
from schema.models import CleanRecord

logger = logging.getLogger("datasanitizer")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


def clean_row(raw: dict) -> Tuple[dict | None, dict | None]:

    reasons: List[str] = []

    name = clean_name(raw.get("full_name"))
    email, email_err = clean_email(raw.get("email"))
    phone, phone_err = clean_phone(raw.get("phone"))
    signup_date, date_err = clean_date(raw.get("signup_date"))

    if name is None:
        reasons.append("full_name missing/empty after trimming")
    if email_err:
        reasons.append(email_err)
    if phone_err:
        reasons.append(phone_err)
    if date_err:
        reasons.append(date_err)

    original = {
        "full_name": raw.get("full_name", "") or "",
        "email": raw.get("email", "") or "",
        "phone": raw.get("phone", "") or "",
        "signup_date": raw.get("signup_date", "") or "",
    }

    if reasons:
        return None, {**original, "reason": "; ".join(reasons)}

    candidate = {
        "full_name": name,
        "email": email,
        "phone": phone,
        "signup_date": signup_date,
    }

    try:
        validated = CleanRecord(**candidate)
    except Exception as exc:  # Pydantic ValidationError or anything unexpected
        return None, {**original, "reason": f"schema validation failed: {exc}"}

    clean_dict = {
        "full_name": validated.full_name,
        "email": validated.email,
        "phone": validated.phone,
        "signup_date": validated.signup_date.isoformat(),
    }
    return clean_dict, None


def process_rows(raw_rows: List[dict]) -> Tuple[List[dict], List[dict]]:

    cleaned: List[dict] = []
    rejected: List[dict] = []

    for row in raw_rows:
        line_no = row.get("_source_line", "?")
        try:
            clean_record, reject_record = clean_row(row)
        except Exception as exc:  # belt-and-suspenders: never crash the run
            logger.error("Unexpected error processing row at line %s: %s", line_no, exc)
            rejected.append(
                {
                    "full_name": row.get("full_name", "") or "",
                    "email": row.get("email", "") or "",
                    "phone": row.get("phone", "") or "",
                    "signup_date": row.get("signup_date", "") or "",
                    "reason": f"unexpected processing error: {exc}",
                }
            )
            continue

        if clean_record is not None:
            cleaned.append(clean_record)
        else:
            logger.debug("Row at line %s rejected: %s", line_no, reject_record["reason"])
            rejected.append(reject_record)

    return cleaned, rejected


def run_pipeline(input_path: str, output_path: str, rejects_path: str) -> None:
    logger.info("Reading raw rows from %s", input_path)
    raw_rows = list(read_raw_rows(input_path))
    rows_read = len(raw_rows)

    audit = audit_raw_rows(raw_rows)
    logger.info("\n%s", format_audit_report(audit))

    deduped_raw_rows, exact_duplicates_removed = remove_exact_duplicates(raw_rows)
    logger.info(
        "Exact-duplicate removal: %d fully identical row(s) removed (of %d read)",
        exact_duplicates_removed,
        rows_read,
    )

    cleaned_records, rejected_records = process_rows(deduped_raw_rows)
    logger.info(
        "Cleaning complete: %d row(s) cleaned successfully, %d row(s) rejected",
        len(cleaned_records),
        len(rejected_records),
    )

    dedupe_result = remove_duplicates(cleaned_records)
    logger.info(
        "Near-duplicate removal: %d duplicate(s) removed (of %d cleaned rows)",
        dedupe_result.duplicates_removed,
        len(cleaned_records),
    )

    final_written = write_clean_csv(output_path, dedupe_result.unique_records)
    write_rejected_csv(rejects_path, rejected_records)
    logger.info("Wrote %d clean row(s) to %s", final_written, output_path)
    logger.info("Wrote %d rejected row(s) to %s", len(rejected_records), rejects_path)

    log_summary(
        rows_read=rows_read,
        exact_duplicates_removed=exact_duplicates_removed,
        rejected_count=len(rejected_records),
        near_duplicates_removed=dedupe_result.duplicates_removed,
        final_written=final_written,
        duplicate_examples=dedupe_result.duplicate_examples,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datasanitizer",
        description="Clean, deduplicate, and validate a messy user-records CSV.",
    )
    parser.add_argument("--input", required=True, help="Path to the raw messy input CSV")
    parser.add_argument("--output", required=True, help="Path to write the cleaned output CSV")
    parser.add_argument("--rejects", required=True, help="Path to write rejected_rows.csv")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    configure_logging(args.log_level)

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error("Input file does not exist: %s", input_path)
        sys.exit(1)

    if output_path.resolve() == input_path.resolve():
        logger.error("Refusing to overwrite the original input file. Choose a different --output path.")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Path(args.rejects).parent.mkdir(parents=True, exist_ok=True)

    run_pipeline(str(input_path), args.output, args.rejects)


if __name__ == "__main__":
    main()
