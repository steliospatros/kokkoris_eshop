"""Unique public order codes shown to customers (e.g. #KPK4F8A2B1C)."""
import secrets
import string

ORDER_CODE_PREFIX = "KPK"
ORDER_CODE_RANDOM_LENGTH = 8
ORDER_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_order_code():
    """Return a new unique-looking order code without hitting the database."""
    suffix = "".join(
        secrets.choice(ORDER_CODE_ALPHABET)
        for _ in range(ORDER_CODE_RANDOM_LENGTH)
    )
    return f"{ORDER_CODE_PREFIX}{suffix}"


def assign_unique_order_code(order_model, *, max_attempts=20):
    """Pick a code that is not already stored on another order."""
    for _ in range(max_attempts):
        candidate = generate_order_code()
        if not order_model.objects.filter(order_code=candidate).exists():
            return candidate
    raise RuntimeError("Could not generate a unique order code.")
