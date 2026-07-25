from __future__ import annotations

import re
from collections import Counter
from typing import List


_PHONE_FORMAT_PATTERNS = {
    "digits_only (10)": re.compile(r"^\d{10}$"),
    "dashed (415-555-1234)": re.compile(r"^\d{3}-\d{3}-\d{4}$"),
    "parenthesized ((415) 555-1234)": re.compile(r"^\(\d{3}\)\s?\d{3}-\d{4}$"),
    "dotted (415.555.1234)": re.compile(r"^\d{3}\.\d{3}\.\d{4}$"),
    "with_country_code (+1 415 555 1234)": re.compile(
        r"^\+?1[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{4}$"
    ),
}


def audit_raw_rows(rows: List[dict]) -> dict:

    columns = [c for c in rows[0].keys() if c != "_source_line"] if rows else []
    total = len(rows)
    missing_counts = {col: 0 for col in columns}
    phone_format_counts: Counter = Counter()
    non_utf8_rows = 0

    for row in rows:
        for col in columns:
            value = row.get(col)
            if value is None or not str(value).strip():
                missing_counts[col] += 1
            elif "\ufffd" in str(value):
                non_utf8_rows += 1

        phone_raw = (row.get("phone") or "").strip()
        matched_label = None
        for label, pattern in _PHONE_FORMAT_PATTERNS.items():
            if pattern.match(phone_raw):
                matched_label = label
                break
        if phone_raw:
            phone_format_counts[matched_label or "other/malformed"] += 1

    return {
        "total_rows": total,
        "columns": columns,
        "missing_counts": missing_counts,
        "phone_format_distribution": dict(phone_format_counts),
        "non_utf8_rows": non_utf8_rows,
    }


def format_audit_report(audit: dict) -> str:
    
    lines = [
        "=== Pre-Cleaning Audit ===",
        f"Total rows read: {audit['total_rows']}",
        f"Columns detected: {', '.join(audit['columns'])}",
        "Missing-value counts by column:",
    ]
    for col, count in audit["missing_counts"].items():
        lines.append(f"  - {col}: {count} missing")
    lines.append("Phone format distribution (raw, pre-cleaning):")
    for label, count in audit["phone_format_distribution"].items():
        lines.append(f"  - {label}: {count}")
    lines.append(f"Rows with non-UTF-8 characters detected: {audit['non_utf8_rows']}")
    return "\n".join(lines)
