import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordComplexityValidator:
    """Enforce minimum password complexity for all Django password entry points."""

    def validate(self, password, user=None):
        if len(password) < 10:
            raise ValidationError(
                _(
                    "Password must be at least 10 characters long and include lowercase, uppercase, digit, and special character."
                ),
                code="password_too_weak",
            )

        has_lower = re.search(r"[a-z]", password) is not None
        has_upper = re.search(r"[A-Z]", password) is not None
        has_digit = re.search(r"[0-9]", password) is not None
        has_special = re.search(r"[^A-Za-z0-9]", password) is not None

        if not (has_lower and has_upper and has_digit and has_special):
            raise ValidationError(
                _(
                    "Password must be at least 10 characters long and include lowercase, uppercase, digit, and special character."
                ),
                code="password_too_weak",
            )

    def get_help_text(self):
        return _(
            "Your password must be at least 10 characters long and include lowercase, uppercase, digit, and special character."
        )
