from django.conf import settings


def breadcrumbs(request):
    return {"breadcrumbs": getattr(request, "breadcrumbs", [])}


def brand(request):
    return {"brand_contact_email": settings.BRAND_CONTACT_EMAIL}
