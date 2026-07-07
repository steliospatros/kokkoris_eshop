from django.conf import settings


def recaptcha(request):
    return {
        "RECAPTCHA_ENABLED": settings.RECAPTCHA_ENABLED,
        "RECAPTCHA_SITE_KEY": settings.RECAPTCHA_SITE_KEY,
    }
