from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from administration.permissions import user_is_administration_user


def administration_user_required(view_func):
    """Require login plus an active AdministrationUser record for the account email."""

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_is_administration_user(request.user):
            return HttpResponseForbidden("Δεν έχετε πρόσβαση στη διαχείριση.")
        return view_func(request, *args, **kwargs)

    return _wrapped
