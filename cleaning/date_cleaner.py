from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Tuple

_KNOWN_FORMATS = [
    "%Y-%m-%d",     # 2024-01-15          (already ISO 8601)
    "%Y/%m/%d",      # 2024/01/15
    "%B %d, %Y",     # January 15, 2024
    "%b %d, %Y",     # Jan 15, 2024
    "%B %d %Y",      # March 3 2024 (written month, no comma)
    "%b %d %Y",      # Mar 3 2024
    "%d-%b-%Y",      # 15-Jan-2024
    "%d %B %Y",      # 15 January 2024
]

_SLASH_NUMERIC_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$")


def clean_date(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    
    if raw is None:
        return None, "signup_date missing"

    value = raw.strip()
    if not value:
        return None, "signup_date missing"

    match = _SLASH_NUMERIC_RE.match(value)
    if match:
        first, second, year = match.groups()
        first_i, second_i = int(first), int(second)
        year_fmt = "%y" if len(year) == 2 else "%Y"

        if first_i <= 12 and second_i <= 12 and first_i != second_i:
            return None, (
                f"signup_date '{raw}' is ambiguous: could be "
                f"MM/DD/YYYY or DD/MM/YYYY"
            )

        try:
            if first_i > 12:
                dt = datetime.strptime(value, f"%d/%m/{year_fmt}")
            else:
                dt = datetime.strptime(value, f"%m/%d/{year_fmt}")
            return dt.date().isoformat(), None
        except ValueError:
            return None, f"signup_date '{raw}' could not be parsed as a valid date"

    for fmt in _KNOWN_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.date().isoformat(), None
        except ValueError:
            continue

    return None, f"signup_date '{raw}' does not match any recognized date format"
