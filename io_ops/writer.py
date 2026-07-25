
from __future__ import annotations

import csv
from typing import Iterable

CLEAN_FIELDS = ["full_name", "email", "phone", "signup_date"]
REJECT_FIELDS = ["full_name", "email", "phone", "signup_date", "reason"]


def write_clean_csv(path: str, records: Iterable[dict]) -> int:
  
    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CLEAN_FIELDS)
        writer.writeheader()
        for rec in records:
            writer.writerow({field: rec.get(field, "") for field in CLEAN_FIELDS})
            count += 1
    return count


def write_rejected_csv(path: str, rejected: Iterable[dict]) -> int:
   
    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REJECT_FIELDS)
        writer.writeheader()
        for rec in rejected:
            writer.writerow({field: rec.get(field, "") for field in REJECT_FIELDS})
            count += 1
    return count
