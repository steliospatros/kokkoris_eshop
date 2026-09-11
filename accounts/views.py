import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.http import require_POST

from allauth.account.forms import LoginForm, ResetPasswordForm
from allauth.account.internal.flows.signup import complete_signup
from allauth.core import ratelimit

from accounts.phone_verification import effective_phone_verified, phone_verification_enabled
from newsletter.services import subscribe_newsletter
from orders.presentation import build_order_item_rows, build_payment_display
from products.catalog import format_decimal_greek

from .forms import KokkorisSignupForm, ProfileForm
from .password_help import form_errors_el
from .address_utils import resolve_greek_city
from .floor_options import FLOOR_OTHER_LABEL, FLOOR_PRESET_OPTIONS
from .profile_labels import (
    DELIVERY_METHOD_LABELS,
    ORDER_STATUS_LABELS,
    PROFILE_EDITABLE_FIELDS,
)


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


def _validation_message(exc: ValidationError) -> str:
    if getattr(exc, "messages", None):
        return str(exc.messages[0])
    if getattr(exc, "message", None):
        return str(exc.message)
    return "Μη έγκυρο αίτημα."


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

    return JsonResponse({
        "ok": True,
        "redirect": next_url,
        "phone_verified": effective_phone_verified(request.user),
    })


@require_POST
def api_signup(request):
    if request.user.is_authenticated:
        return JsonResponse({"ok": True, "redirect": reverse("home")})

    payload = _json_body(request)
    next_url = _safe_next_url(request, payload.get("next"))

    form = KokkorisSignupForm(
        data={
            "email": (payload.get("email") or "").strip(),
            "phone_number": (payload.get("phone_number") or "").strip(),
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

    newsletter_opt_in = payload.get("newsletter_subscribe", True)
    if isinstance(newsletter_opt_in, str):
        newsletter_opt_in = newsletter_opt_in.lower() in ("1", "true", "yes", "on")
    if newsletter_opt_in:
        subscribe_newsletter(email=request.user.email, user=request.user)

    return JsonResponse({
        "ok": True,
        "redirect": next_url,
        "phone_verified": effective_phone_verified(request.user),
    })


@login_required
@require_POST
def api_phone_send_otp(request):
    if not phone_verification_enabled():
        return JsonResponse({"ok": False, "error": "Η επιβεβαίωση κινητού δεν είναι ενεργή."}, status=503)

    from accounts.phone_verification import send_otp
    from accounts.sms import SMSDeliveryError

    payload = _json_body(request)
    phone = (payload.get("phone_number") or "").strip()
    try:
        result = send_otp(phone, user_id=request.user.pk)
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": _validation_message(exc)}, status=400)
    except SMSDeliveryError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=503)

    return JsonResponse({
        "ok": True,
        "phone_number": result.phone,
        "sms_sent": result.sms_sent,
    })


@login_required
@require_POST
def api_phone_verify_otp(request):
    if not phone_verification_enabled():
        return JsonResponse({"ok": False, "error": "Η επιβεβαίωση κινητού δεν είναι ενεργή."}, status=503)

    from django.utils import timezone

    from accounts.phone_verification import verify_otp

    payload = _json_body(request)
    phone = (payload.get("phone_number") or "").strip()
    code = (payload.get("code") or "").strip()
    try:
        normalized = verify_otp(phone, code)
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": _validation_message(exc)}, status=400)

    request.user.phone_number = normalized
    request.user.phone_verified_at = timezone.now()
    request.user.save(update_fields=["phone_number", "phone_verified_at"])
    return JsonResponse({"ok": True, "phone_number": normalized})


@login_required
@require_POST
def api_phone_reset_verification(request):
    request.user.phone_verified_at = None
    request.user.save(update_fields=["phone_verified_at"])
    return JsonResponse({"ok": True})


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
def account_hub_view(request):
    """Main account menu after login (person icon in nav)."""
    return render(request, "accounts/hub.html")


PROFILE_ADDRESS_SEARCH_FIELD = "address"
PROFILE_ADDRESS_AUTO_FIELDS = (
    "city",
    "area",
    "street",
    "street_number",
    "postal_code",
)
PROFILE_ADDRESS_MAP_FIELDS = {PROFILE_ADDRESS_SEARCH_FIELD}
PROFILE_ADDRESS_EXTRA_FIELDS = ("floor", "doorbell_name", "delivery_notes")


def _profile_field_row(user, form, field_name, label):
    if form is not None and field_name in form.data:
        value = (form.data.get(field_name) or "").strip()
    else:
        value = getattr(user, field_name, "") or ""
    error = ""
    if form is not None and field_name in form.errors:
        error = " ".join(str(e) for e in form.errors[field_name])
    return {
        "name": field_name,
        "label": label,
        "value": value,
        "display": value if value else "—",
        "multiline": field_name == "delivery_notes",
        "error": error,
    }


def _profile_field_rows(user, form=None):
    """Build display rows for the editable profile fields."""
    rows = []
    skip = (
        PROFILE_ADDRESS_MAP_FIELDS
        | set(PROFILE_ADDRESS_EXTRA_FIELDS)
        | set(PROFILE_ADDRESS_AUTO_FIELDS)
    )
    for field_name, label in PROFILE_EDITABLE_FIELDS:
        if field_name in skip:
            continue
        rows.append(_profile_field_row(user, form, field_name, label))
    return rows


@login_required
def account_details_view(request):
    """
    «Τα στοιχεία μου» — read-only list with per-field pencil edit;
    saves only when the customer submits the whole form.
    Email is never editable; password changes only via allauth link.
    """
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Οι αλλαγές σου αποθηκεύτηκαν.")
            return redirect("accounts:details")
        messages.error(request, "Διόρθωσε τα σφάλματα και δοκίμασε ξανά.")
    else:
        form = ProfileForm(instance=request.user)

    return render(
        request,
        "accounts/details.html",
        {
            "form": form,
            "field_rows": _profile_field_rows(request.user, form=form),
            "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
            "address_search_row": _profile_address_search_row(request.user, form=form),
            "address_auto_rows": _profile_address_auto_rows(request.user, form=form),
            "address_extra_rows": _profile_address_extra_rows(request.user, form=form),
            "floor_preset_options": FLOOR_PRESET_OPTIONS,
            "floor_other_label": FLOOR_OTHER_LABEL,
        },
    )


def _profile_address_search_row(user, form=None):
    labels = dict(PROFILE_EDITABLE_FIELDS)
    row = _profile_field_row(
        user, form, PROFILE_ADDRESS_SEARCH_FIELD, labels[PROFILE_ADDRESS_SEARCH_FIELD]
    )
    if form is not None and "street" in form.data:
        street = (form.data.get("street") or "").strip()
        number = (form.data.get("street_number") or "").strip()
    else:
        street = getattr(user, "street", "") or ""
        number = getattr(user, "street_number", "") or ""
    row["search_hint"] = " ".join(part for part in (street, number) if part).strip()
    if form is not None and form.errors.get("address_search"):
        row["error"] = " ".join(str(e) for e in form.errors["address_search"])
    return row


def _profile_address_auto_rows(user, form=None):
    labels = dict(PROFILE_EDITABLE_FIELDS)
    rows = []
    for field_name in PROFILE_ADDRESS_AUTO_FIELDS:
        row = _profile_field_row(user, form, field_name, labels[field_name])
        if field_name == "city":
            postal = getattr(user, "postal_code", "") or ""
            if form is not None and PROFILE_ADDRESS_AUTO_FIELDS[-1] in form.data:
                postal = (form.data.get("postal_code") or "").strip() or postal
            normalized = resolve_greek_city(row["value"], postal)
            row["value"] = normalized
            row["display"] = normalized if normalized else "—"
        rows.append(row)
    return rows


def _profile_address_map_rows(user, form=None):
    rows = []
    for field_name, label in PROFILE_EDITABLE_FIELDS:
        if field_name not in PROFILE_ADDRESS_MAP_FIELDS:
            continue
        rows.append(_profile_field_row(user, form, field_name, label))
    return rows


def _profile_address_extra_rows(user, form=None):
    rows = []
    labels = dict(PROFILE_EDITABLE_FIELDS)
    for field_name in PROFILE_ADDRESS_EXTRA_FIELDS:
        rows.append(_profile_field_row(user, form, field_name, labels[field_name]))
    return rows


def _profile_field_rows_for_address(user, form=None):
    """Deprecated alias — kept for any external callers."""
    return _profile_address_map_rows(user, form=form)


@login_required
def account_orders_view(request):
    """Order and payment history for the logged-in customer."""
    orders = (
        request.user.orders.prefetch_related("items__product_variant__product")
        .order_by("-order_date")
    )
    order_rows = []
    for order in orders:
        item_rows = build_order_item_rows(order)
        order_rows.append(
            {
                "order": order,
                "status_label": ORDER_STATUS_LABELS.get(
                    order.status, order.get_status_display()
                ),
                **build_payment_display(order),
                "delivery_label": DELIVERY_METHOD_LABELS.get(
                    order.delivery_method, order.get_delivery_method_display()
                ),
                "order_code_display": order.public_code_display,
                "order_date_display": timezone.localtime(order.order_date).strftime(
                    "%d/%m/%Y %H:%M"
                ),
                "total_cost_display": format_decimal_greek(order.total_cost),
                "thumbnail_urls": [
                    row["image_url"] for row in item_rows[:4] if row["image_url"]
                ],
            }
        )
    return render(
        request,
        "accounts/orders.html",
        {"order_rows": order_rows},
    )


def account_cart_view(request):
    """«Το καλάθι μου» — summary of cart lines before checkout."""
    from cart.cart import get_cart
    from cart.presentation import build_cart_summary

    summary = build_cart_summary(get_cart(request))
    from products.shipping_promo import build_free_shipping_promo

    return render(
        request,
        "accounts/cart.html",
        {
            "cart_lines": summary["lines"],
            "cart_total": summary["total"],
            "cart_total_display": summary["total_display"],
            "cart_total_items": summary["total_items"],
            "free_shipping_promo": build_free_shipping_promo(summary["total"]),
        },
    )


@login_required
def profile_view(request):
    """Legacy URL — redirect to the account hub."""
    return redirect("accounts:hub")
