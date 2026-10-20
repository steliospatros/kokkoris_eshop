from django.conf import settings
from django.templatetags.static import static


def breadcrumbs(request):
    return {"breadcrumbs": getattr(request, "breadcrumbs", [])}


def brand(request):
    base = (settings.SITE_BASE_URL or "").rstrip("/")
    if not base and getattr(request, "get_host", None):
        base = f"{request.scheme}://{request.get_host()}".rstrip("/")
    logo_path = static("images/brand/icon-512.png")
    favicon_48_path = static("images/brand/favicon-48.png")
    return {
        "brand_contact_email": settings.BRAND_CONTACT_EMAIL,
        "site_base_url": base,
        "brand_logo_url": f"{base}{logo_path}" if base else logo_path,
        "brand_favicon_48_url": (
            f"{base}{favicon_48_path}" if base else favicon_48_path
        ),
    }
