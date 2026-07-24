from __future__ import annotations

from typing import Optional, Tuple

import re

_DIGIT_RE = re.compile(r"\d")


def clean_phone(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:

    if raw is None:
        return None, "phone missing"

    raw_stripped = raw.strip()
    if not raw_stripped:
        return None, "phone missing"

    digits = "".join(_DIGIT_RE.findall(raw_stripped))

    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        return (
            None,
            f"phone '{raw}' has {len(digits)} digit(s) after stripping "
            f"formatting; expected exactly 10 (US number) -- too few/many "
            f"digits to confidently salvage",
        )

    return f"+1{digits}", None
