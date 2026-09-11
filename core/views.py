from django.http import HttpResponseServerError
from django.shortcuts import render
from django.template.loader import render_to_string

from core import user_text


def _error_context(*, title, lead):
    return {
        "page_title": title,
        "error_title": title,
        "error_lead": lead,
        "home_link_label": user_text.HOME_LINK,
    }


def _error_response(request, *, status, title, lead):
    return render(
        request,
        "errors/error.html",
        _error_context(title=title, lead=lead),
        status=status,
    )


def page_not_found(request, exception=None):
    return _error_response(
        request,
        status=404,
        title=user_text.ERROR_404_TITLE,
        lead=user_text.ERROR_404_LEAD,
    )


def permission_denied(request, exception=None):
    return _error_response(
        request,
        status=403,
        title=user_text.ERROR_403_TITLE,
        lead=user_text.ERROR_403_LEAD,
    )


def bad_request(request, exception=None):
    return _error_response(
        request,
        status=400,
        title=user_text.ERROR_400_TITLE,
        lead=user_text.ERROR_400_LEAD,
    )


def server_error(request):
    """Standalone 500 page — no request context processors that could fail again."""
    context = _error_context(
        title=user_text.ERROR_500_TITLE,
        lead=user_text.ERROR_500_LEAD,
    )
    try:
        html = render_to_string("errors/error.html", context)
    except Exception:
        html = (
            "<!DOCTYPE html><html lang='el'><head><meta charset='utf-8'>"
            f"<title>{user_text.ERROR_500_TITLE}</title></head><body>"
            f"<h1>{user_text.ERROR_500_TITLE}</h1>"
            f"<p>{user_text.ERROR_500_LEAD}</p>"
            f"<p><a href='/'>{user_text.HOME_LINK}</a></p>"
            "</body></html>"
        )
    return HttpResponseServerError(html)
