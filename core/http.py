import logging
from functools import wraps

from django.http import JsonResponse

from core.user_text import GENERIC

logger = logging.getLogger("kokkoris")


def json_error(message, *, status=400, **extra):
    payload = {"ok": False, "error": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def json_safe(view):
    """Keep JSON endpoints from returning an HTML crash page."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except Exception:
            logger.exception("JSON view failed: %s", request.path)
            return json_error(GENERIC, status=500)

    return wrapped
