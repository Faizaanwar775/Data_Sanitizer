from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DedupeResult:
    unique_records: List[dict]
    duplicates_removed: int
    duplicate_examples: List[dict] = field(default_factory=list)


def dedupe_key(record: dict) -> str:

    return record["email"].strip().lower()


def _completeness(record: dict) -> int:

    return sum(1 for v in record.values() if v not in (None, ""))


def pick_best(existing: dict, incoming: dict) -> dict:
    
    existing_date = existing.get("signup_date")
    incoming_date = incoming.get("signup_date")

    if existing_date and incoming_date and existing_date != incoming_date:
        return incoming if incoming_date > existing_date else existing

    if _completeness(incoming) != _completeness(existing):
        return incoming if _completeness(incoming) > _completeness(existing) else existing

    return existing  # stable tie-break: keep whichever was seen first


def remove_duplicates(records: List[dict], max_examples: int = 8) -> DedupeResult:
    
    seen: Dict[str, dict] = {}
    order: List[str] = []
    examples: List[dict] = []
    duplicates_removed = 0

    for record in records:
        key = dedupe_key(record)
        if key in seen:
            duplicates_removed += 1
            previous = dict(seen[key])
            kept = pick_best(seen[key], record)
            seen[key] = kept
            if len(examples) < max_examples:
                examples.append(
                    {
                        "key": key,
                        "existing": previous,
                        "incoming": dict(record),
                        "kept": dict(kept),
                    }
                )
        else:
            seen[key] = record
            order.append(key)

    unique_records = [seen[k] for k in order]
    return DedupeResult(unique_records, duplicates_removed, examples)


def remove_exact_duplicates(rows: List[dict]) -> tuple[List[dict], int]:

    seen_signatures = set()
    unique_rows = []
    duplicates = 0
    for row in rows:
        
        signature = tuple(
            (k, tuple(v) if isinstance(v, list) else v)
            for k, v in sorted(row.items(), key=lambda kv: str(kv[0]))
            if k not in ("_source_line", None)
        )
        if signature in seen_signatures:
            duplicates += 1
            continue
        seen_signatures.add(signature)
        unique_rows.append(row)
    return unique_rows, duplicates
