import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from allauth.account.forms import LoginForm, ResetPasswordForm, SignupForm
from allauth.account.internal.flows.signup import complete_signup
from allauth.core import ratelimit

from .forms import ProfileForm
from .password_help import form_errors_el


def _json_body(request):
    if request.content_type == "application/json":
        try:
            return json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST


def _safe_next_url(request, candidate):
    if candidate and candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return reverse("home")


@require_POST
def api_login(request):
    if request.user.is_authenticated:
        return JsonResponse({"ok": True, "redirect": reverse("home")})

    payload = _json_body(request)
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    next_url = _safe_next_url(request, payload.get("next"))

    form = LoginForm(
        request=request,
        data={"login": email, "password": password},
    )
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form_errors_el(form)}, status=400)

    form.login(request, redirect_url=next_url)
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "ok": False,
                "errors": {
                    "__all__": ["Η σύνδεση δεν ολοκληρώθηκε. Έλεγξε το email σου."]
                },
            },
            status=400,
        )

    return JsonResponse({"ok": True, "redirect": next_url})


@require_POST
def api_signup(request):
    if request.user.is_authenticated:
        return JsonResponse({"ok": True, "redirect": reverse("home")})

    payload = _json_body(request)
    next_url = _safe_next_url(request, payload.get("next"))

    form = SignupForm(
        data={
            "email": (payload.get("email") or "").strip(),
            "password1": payload.get("password1") or "",
            "password2": payload.get("password2") or "",
        },
    )
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form_errors_el(form)}, status=400)

    user, pending_response = form.try_save(request)
    if user is None:
        return JsonResponse({"ok": True, "redirect": next_url})

    complete_signup(request, user=user, redirect_url=next_url)
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "ok": False,
                "errors": {
                    "__all__": ["Η εγγραφή δεν ολοκληρώθηκε. Δοκίμασε ξανά."]
                },
            },
            status=400,
        )

    return JsonResponse({"ok": True, "redirect": next_url})


@require_POST
def api_password_reset(request):
    if request.user.is_authenticated:
        return JsonResponse({"ok": True})

    payload = _json_body(request)
    email = (payload.get("email") or "").strip()

    form = ResetPasswordForm(data={"email": email})
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form_errors_el(form)}, status=400)

    rate_limited = ratelimit.consume_or_429(
        request,
        action="reset_password",
        key=email.lower(),
    )
    if rate_limited:
        return JsonResponse(
            {
                "ok": False,
                "errors": {
                    "__all__": ["Πάρα πολλά αιτήματα. Δοκίμασε ξανά σε λίγο."]
                },
            },
            status=429,
        )

    form.save(request)
    return JsonResponse(
        {
            "ok": True,
            "email": email,
            "message": (
                f"Στείλαμε email επαναφοράς κωδικού στο {email}. "
                "Άνοιξε το mail σου και ακολούθησε τον σύνδεσμο."
            ),
        }
    )


@login_required
def profile_view(request):
    """
    Displays and lets the customer edit their own profile: name and
    delivery details. Registration itself only asks for email/password
    (handled by allauth); everything here is optional and usually filled
    in around the time of a customer's first order.
    """
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Το προφίλ σου ενημερώθηκε.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "accounts/profile.html", {"form": form})
