"""Greek password rules and validation messages for auth UI."""

PASSWORD_RULES = (
    {
        "id": "min_length",
        "hint": "Τουλάχιστον 8 χαρακτήρες.",
        "error": "Ο κωδικός πρέπει να έχει τουλάχιστον 8 χαρακτήρες.",
    },
    {
        "id": "has_digit",
        "hint": "Τουλάχιστον ένας αριθμός (0–9).",
        "error": "Ο κωδικός πρέπει να περιλαμβάνει τουλάχιστον έναν αριθμό.",
    },
)

MIN_PASSWORD_LENGTH = 8

_ERROR_CODE_MESSAGES = {
    "password_too_short": PASSWORD_RULES[0]["error"],
    "password_no_digit": PASSWORD_RULES[1]["error"],
    "invalid_login": "Μη έγκυρο email ή κωδικός.",
    "email_password_mismatch": "Μη έγκυρο email ή κωδικός.",
    "unknown_email": "Δεν βρέθηκε λογαριασμός με αυτό το email.",
    "duplicate_email": "Υπάρχει ήδη λογαριασμός με αυτό το email.",
    "email_taken": "Υπάρχει ήδη λογαριασμός με αυτό το email.",
}


def first_password_error(password):
    """Return the first violated rule message, or None if valid."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return PASSWORD_RULES[0]["error"]
    if not any(char.isdigit() for char in password):
        return PASSWORD_RULES[1]["error"]
    return None


def translate_form_error(error):
    code = getattr(error, "code", None)
    if code and code in _ERROR_CODE_MESSAGES:
        return _ERROR_CODE_MESSAGES[code]
    message = str(error)
    if "too short" in message.lower():
        return _ERROR_CODE_MESSAGES["password_too_short"]
    if "digit" in message.lower() or "αριθμ" in message.lower():
        return _ERROR_CODE_MESSAGES["password_no_digit"]
    if "must type the same password" in message.lower():
        return "Οι δύο κωδικοί δεν ταιριάζουν."
    return message


def form_errors_el(form):
    errors = {}
    for field, field_errors in form.errors.as_data().items():
        translated = [translate_form_error(error) for error in field_errors]
        if field in ("password1", "password2"):
            seen = set()
            unique = []
            for msg in translated:
                if msg not in seen:
                    seen.add(msg)
                    unique.append(msg)
            translated = unique[:1] if field == "password1" else translated
        errors[field] = translated
    return errors
