from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from core import user_text

from .forms import NewsletterSubscribeForm
from .models import NewsletterSubscriber
from .recaptcha import verify_recaptcha


@require_POST
def subscribe(request):
    """
    Save a newsletter email from the footer form and redirect back.
    """
    form = NewsletterSubscribeForm(request.POST)
    if not form.is_valid():
        messages.error(request, user_text.NEWSLETTER_BAD_EMAIL)
        return redirect(request.POST.get("next") or "home")

    if not verify_recaptcha(
        form.cleaned_data.get("g_recaptcha_response"),
        remote_ip=request.META.get("REMOTE_ADDR"),
    ):
        messages.error(request, user_text.NEWSLETTER_RETRY)
        return redirect(request.POST.get("next") or "home")

    email = form.cleaned_data["email"].lower().strip()
    subscriber, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={"user": request.user if request.user.is_authenticated else None},
    )

    if created:
        messages.success(request, user_text.NEWSLETTER_THANKS)
        return redirect(request.POST.get("next") or "home")

    if not subscriber.is_active:
        subscriber.resubscribe()
        if request.user.is_authenticated and not subscriber.user_id:
            subscriber.user = request.user
            subscriber.save(update_fields=["user"])
        messages.success(request, user_text.NEWSLETTER_AGAIN)
        return redirect(request.POST.get("next") or "home")

    messages.info(request, user_text.NEWSLETTER_ALREADY)
    return redirect(request.POST.get("next") or "home")
