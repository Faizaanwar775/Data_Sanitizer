
from __future__ import annotations

import re
from typing import Optional, Tuple

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def clean_email(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    
    if raw is None:
        return None, "email missing"

    email = raw.strip()
    if not email:
        return None, "email missing"

    if "@" not in email:
        return None, f"email '{raw}' has no @ symbol"

    local, _, domain = email.partition("@")
    normalized = f"{local}@{domain.lower()}"

    if not _EMAIL_RE.fullmatch(normalized):
        return None, f"email '{raw}' fails structural validity check"

    return normalized, None
