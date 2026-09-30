from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse

from core import user_text
from core.http import json_error


def robots_txt(request):
    """Allow crawlers on public pages; point them at the XML sitemap."""
    sitemap_path = reverse("django.contrib.sitemaps.views.sitemap")
    base = (settings.SITE_BASE_URL or "").rstrip("/")
    if base:
        sitemap_url = f"{base}{sitemap_path}"
    else:
        sitemap_url = request.build_absolute_uri(sitemap_path)
    body = render_to_string(
        "robots.txt",
        {"sitemap_url": sitemap_url},
        request=request,
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


def _wants_json(request):
    accept = request.headers.get("Accept") or ""
    content_type = request.content_type or ""
    return (
        "application/json" in accept
        or content_type.startswith("application/json")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def csrf_failure(request, reason=""):
    """Cart/wishlist POSTs must stay JSON — not the HTML 403 page."""
    if _wants_json(request):
        return json_error(
            user_text.AUTH_SESSION_EXPIRED,
            status=403,
            code="AUTH_SESSION_EXPIRED",
        )
    return permission_denied(request)


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
