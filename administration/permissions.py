from django.db.utils import OperationalError, ProgrammingError

from administration.models import AdministrationUser


def user_is_administration_user(user):
    """True when the logged-in user's email is on the administration allow-list."""
    if not user.is_authenticated:
        return False
    email = (user.email or "").strip()
    if not email:
        return False
    try:
        return AdministrationUser.objects.filter(email__iexact=email, is_active=True).exists()
    except (OperationalError, ProgrammingError):
        return False
