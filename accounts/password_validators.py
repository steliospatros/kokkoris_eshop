import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class PasswordHasDigitValidator:
    """Require at least one digit (0–9) in the password."""

    def validate(self, password, user=None):
        if not re.search(r"\d", password):
            raise ValidationError(
                _("Ο κωδικός πρέπει να περιλαμβάνει τουλάχιστον έναν αριθμό."),
                code="password_no_digit",
            )

    def get_help_text(self):
        return _("Ο κωδικός πρέπει να περιλαμβάνει τουλάχιστον έναν αριθμό.")
