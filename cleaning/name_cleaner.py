
from __future__ import annotations

import re
from typing import Optional

_WHITESPACE_RE = re.compile(r"\s+")

_NAME_SPLIT_RE = re.compile(r"([\s\-'])")


def clean_name(raw: Optional[str]) -> Optional[str]:

    if raw is None:
        return None

    name = raw.strip()
    name = _WHITESPACE_RE.sub(" ", name)
    if not name:
        return None

    parts = _NAME_SPLIT_RE.split(name)
    rebuilt = []
    for part in parts:
        if part in (" ", "-", "'"):
            rebuilt.append(part)
        elif part:
            
            rebuilt.append(part[0].upper() + part[1:].lower())
    return "".join(rebuilt)
