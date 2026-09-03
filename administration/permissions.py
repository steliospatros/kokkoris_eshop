from django.db.utils import OperationalError, ProgrammingError

from administration.models import AdministrationUser


def get_administration_record(user):
    """Active AdministrationUser row for this login email, or None."""
    if not user or not user.is_authenticated:
        return None
    email = (user.email or "").strip()
    if not email:
        return None
    try:
        return AdministrationUser.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()
    except (OperationalError, ProgrammingError):
        return None


def user_is_administration_user(user):
    """True when the logged-in user's email is on the administration allow-list."""
    return get_administration_record(user) is not None


def user_is_shop_admin(user):
    """True for full administration access (not courier-only)."""
    record = get_administration_record(user)
    return bool(record and record.is_shop_admin)


def user_is_courier(user):
    """True when the allow-list role is courier."""
    record = get_administration_record(user)
    return bool(record and record.is_courier)
