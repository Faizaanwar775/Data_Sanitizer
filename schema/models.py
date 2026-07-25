from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, EmailStr, field_validator

PHONE_TARGET_PATTERN = re.compile(r"^\+1\d{10}$")


class CleanRecord(BaseModel):


    full_name: str
    email: EmailStr
    phone: str
    signup_date: date

    @field_validator("full_name")
    @classmethod
    def full_name_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("full_name cannot be empty after cleaning")
        return value

    @field_validator("phone")
    @classmethod
    def phone_must_match_target_format(cls, value: str) -> str:
        if not PHONE_TARGET_PATTERN.match(value):
            raise ValueError(
                f"phone '{value}' does not match the required target format "
                f"+1XXXXXXXXXX"
            )
        return value

    model_config = {
        # Reject unexpected/extra fields silently sneaking into clean output.
        "extra": "forbid",
    }
