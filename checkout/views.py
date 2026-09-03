from decimal import Decimal
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.profile_context import build_profile_form_context
from cart.cart import get_cart
from orders.models import Order, OrderItem
from orders.presentation import build_order_detail_context
from orders.stock import InsufficientStockError, reserve_stock_for_cart
from products.favourites import increment_favourite_counts

from .boxnow_service import schedule_boxnow_delivery
from .boxnow_webhooks import (
    BoxNowWebhookError,
    apply_boxnow_parcel_event,
    verify_boxnow_signature,
)
from .delivery import build_delivery_options, calculate_courier_fee
from .forms import CheckoutProfileForm, PaymentMethodForm
from .payment_options import build_payment_options
from .helpers import (
    SESSION_KEY,
    CHECKOUT_STEP_ADDRESS,
    CHECKOUT_STEP_DELIVERY,
    CHECKOUT_STEP_PAYMENT,
    build_checkout_sidebar,
    build_checkout_steps,
    stash_checkout_address,
)
from .stripe_service import (
    StripeNotConfiguredError,
    StripePaymentError,
    card_order_status,
    create_checkout_payment_intent,
    find_order_for_payment_intent,
    stripe_payments_enabled,
    verify_card_payment_intent,
)


def _redirect_if_cart_empty(request):
    """Shared guard: every checkout step needs a non-empty cart."""
    cart = get_cart(request)
    if cart.total_items == 0:
        messages.error(request, "Το καλάθι σου είναι άδειο.")
        return redirect("accounts:cart")
    return None


def _checkout_sidebar_context(request, *, courier_fee=None, show_shipping_breakdown=False):
    cart = get_cart(request)
    return build_checkout_sidebar(
        cart,
        courier_fee=courier_fee,
        show_shipping_breakdown=show_shipping_breakdown,
    )


def _delivery_sidebar_fee(postal_code, delivery_method, cart, cart_total):
    """Shipping fee for the sidebar based on the selected delivery method."""
    if delivery_method in (
        Order.DELIVERY_METHOD_COURIER,
        Order.DELIVERY_METHOD_BOX_NOW,
    ):
        return calculate_courier_fee(
            postal_code,
            delivery_method,
            cart=cart,
            cart_total=cart_total,
        )
    return Decimal("0.00")


def _get_checkout_payment_context(request):
    """Shared guards and totals for payment step + PaymentIntent API."""
    checkout_data = request.session.get(SESSION_KEY)
    if not checkout_data or "delivery_method" not in checkout_data:
        return None, None, None, None, None

    cart = get_cart(request)
    cart_total = cart.total
    base_courier_fee = Decimal(checkout_data["courier_fee"])
    cod_courier_fee = calculate_courier_fee(
        checkout_data["postal_code"],
        checkout_data["delivery_method"],
        cart=cart,
        cart_total=cart_total,
        is_cash_on_delivery=True,
    )
    return checkout_data, cart, cart_total, base_courier_fee, cod_courier_fee


def _redirect_if_stock_issues(request, cart, *, redirect_to="accounts:cart"):
    """Block checkout when cart lines no longer have enough stock."""
    stock_issues = cart.get_stock_issues()
    if not stock_issues:
        return None
    for item, issue in stock_issues.items():
        messages.error(request, f"{item.product_variant}: {issue}")
    return redirect(redirect_to)


def _report_stock_error(request, exc: InsufficientStockError):
    for item, issue in exc.issues.items():
        messages.error(request, f"{item.product_variant}: {issue}")


def _create_order_from_checkout(
    request,
    *,
    cart,
    checkout_data,
    payment_method,
    courier_fee,
    cart_total,
    total_cost,
    order_status,
    stripe_payment_intent_id="",
):
    with transaction.atomic():
        reserve_stock_for_cart(cart)
        order = Order.objects.create(
            user=request.user,
            payment_method=payment_method,
            status=order_status,
            cart_cost=cart_total,
            courier_fee=courier_fee,
            total_cost=total_cost,
            stripe_payment_intent_id=stripe_payment_intent_id,
            delivery_method=checkout_data["delivery_method"],
            delivery_phone_number=checkout_data["phone_number"],
            delivery_city=checkout_data["city"],
            delivery_address=checkout_data["address"],
            delivery_postal_code=checkout_data["postal_code"],
            delivery_floor=checkout_data.get("floor", ""),
            delivery_latitude=Decimal(checkout_data["latitude"]),
            delivery_longitude=Decimal(checkout_data["longitude"]),
            delivery_notes=checkout_data.get("delivery_notes", ""),
            boxnow_locker_id=checkout_data.get("boxnow_locker_id", ""),
            boxnow_locker_name=checkout_data.get("boxnow_locker_name", ""),
            boxnow_locker_address=checkout_data.get("boxnow_locker_address", ""),
            boxnow_locker_postal_code=checkout_data.get("boxnow_locker_postal_code", ""),
        )
        for item in list(cart.items):
            OrderItem.objects.create(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity,
                price_at_purchase=item.product_variant.selling_price,
            )
        increment_favourite_counts(cart.items)
        cart.clear()

    if order.delivery_method == Order.DELIVERY_METHOD_BOX_NOW:
        schedule_boxnow_delivery(order)

    del request.session[SESSION_KEY]
    return order


@login_required
def checkout_index_view(request):
    """Entry point for checkout — separate from the cart page."""
    empty_cart_redirect = _redirect_if_cart_empty(request)
    if empty_cart_redirect:
        return empty_cart_redirect

    cart = get_cart(request)
    stock_redirect = _redirect_if_stock_issues(request, cart)
    if stock_redirect:
        return stock_redirect

    return redirect("checkout:address")


@login_required
def checkout_address_view(request):
    """Step 1: delivery profile (same fields as «Τα στοιχεία μου») with locked cart sidebar."""
    empty_cart_redirect = _redirect_if_cart_empty(request)
    if empty_cart_redirect:
        return empty_cart_redirect

    cart = get_cart(request)
    stock_redirect = _redirect_if_stock_issues(request, cart)
    if stock_redirect:
        return stock_redirect

    sidebar = _checkout_sidebar_context(request)

    if request.method == "POST":
        form = CheckoutProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            stash_checkout_address(request, request.user)
            return redirect("checkout:delivery")
        messages.error(request, "Διόρθωσε τα σφάλματα και δοκίμασε ξανά.")
    else:
        form = CheckoutProfileForm(instance=request.user)

    checkout_data = request.session.get(SESSION_KEY, {})
    context = {
        **sidebar,
        **build_profile_form_context(request.user, form=form),
        "form_id": "checkout-address-form",
        "map_container_id": "checkout-address-map",
        "checkout_mode": True,
        "checkout_step": CHECKOUT_STEP_ADDRESS,
        "checkout_steps": build_checkout_steps(CHECKOUT_STEP_ADDRESS, checkout_data),
        "checkout_data": checkout_data,
    }
    return render(request, "checkout/address.html", context)


@login_required
def checkout_delivery_view(request):
    """Step 2: delivery method with locked cart sidebar."""
    empty_cart_redirect = _redirect_if_cart_empty(request)
    if empty_cart_redirect:
        return empty_cart_redirect

    checkout_data = request.session.get(SESSION_KEY)
    if not checkout_data:
        messages.info(request, "Συμπλήρωσε πρώτα τη διεύθυνση παράδοσης.")
        return redirect("checkout:address")

    cart = get_cart(request)
    stock_redirect = _redirect_if_stock_issues(request, cart)
    if stock_redirect:
        return stock_redirect

    postal_code = checkout_data["postal_code"]
    cart_total = cart.total
    options, within_urban_area = build_delivery_options(
        cart_total=cart_total,
        postal_code=postal_code,
        cart=cart,
    )
    valid_values = {
        option["value"] for option in options if not option.get("disabled")
    }

    if request.method == "POST":
        delivery_method = request.POST.get("delivery_method")
        if delivery_method not in valid_values:
            messages.error(request, "Επίλεξε έναν έγκυρο τρόπο παράδοσης.")
        elif delivery_method == Order.DELIVERY_METHOD_BOX_NOW and not request.POST.get(
            "boxnow_locker_id", ""
        ).strip():
            messages.error(
                request,
                "Επίλεξε σημείο παραλαβής BOX NOW από τον χάρτη πριν συνεχίσεις.",
            )
        else:
            fee = _delivery_sidebar_fee(
                postal_code,
                delivery_method,
                cart,
                cart_total,
            )
            data = dict(checkout_data)
            data["delivery_method"] = delivery_method
            data["courier_fee"] = str(fee)
            if delivery_method == Order.DELIVERY_METHOD_BOX_NOW:
                data["boxnow_locker_id"] = request.POST.get("boxnow_locker_id", "").strip()
                data["boxnow_locker_name"] = request.POST.get(
                    "boxnow_locker_name", ""
                ).strip()
                data["boxnow_locker_address"] = request.POST.get(
                    "boxnow_locker_address", ""
                ).strip()
                data["boxnow_locker_postal_code"] = request.POST.get(
                    "boxnow_locker_postal_code", ""
                ).strip()
            else:
                for key in (
                    "boxnow_locker_id",
                    "boxnow_locker_name",
                    "boxnow_locker_address",
                    "boxnow_locker_postal_code",
                ):
                    data.pop(key, None)
            request.session[SESSION_KEY] = data
            return redirect("checkout:payment")

    selected_method = checkout_data.get("delivery_method")
    default_delivery_method = (
        Order.DELIVERY_METHOD_COMPANY
        if within_urban_area
        else Order.DELIVERY_METHOD_COURIER
    )
    if not selected_method or selected_method not in valid_values or (
        not within_urban_area
        and selected_method == Order.DELIVERY_METHOD_COMPANY
    ):
        selected_method = default_delivery_method

    sidebar_fee = _delivery_sidebar_fee(
        postal_code,
        selected_method,
        cart,
        cart_total,
    )
    sidebar = _checkout_sidebar_context(
        request,
        courier_fee=sidebar_fee,
        show_shipping_breakdown=True,
    )

    return render(request, "checkout/delivery.html", {
        **sidebar,
        "options": options,
        "within_urban_area": within_urban_area,
        "cart_total": cart_total,
        "checkout_step": CHECKOUT_STEP_DELIVERY,
        "checkout_steps": build_checkout_steps(CHECKOUT_STEP_DELIVERY, checkout_data),
        "checkout_data": checkout_data,
        "selected_method": selected_method,
        "boxnow_widget_enabled": settings.BOXNOW_WIDGET_ENABLED,
        "boxnow_partner_id": settings.BOXNOW_PARTNER_ID or "",
        "boxnow_required_size": next(
            (
                option.get("compartment_size")
                for option in options
                if option["value"] == Order.DELIVERY_METHOD_BOX_NOW
                and option.get("compartment_size")
            ),
            1,
        ),
        "checkout_postal_code": postal_code,
    })


def _finalize_card_checkout(
    request,
    *,
    cart,
    checkout_data,
    cart_total,
    base_courier_fee,
    stripe_payment_intent_id,
):
    """Create a paid order after Stripe confirms the PaymentIntent."""
    stock_issues = cart.get_stock_issues()
    if stock_issues:
        for item, issue in stock_issues.items():
            messages.error(request, f"{item.product_variant}: {issue}")
        raise StripePaymentError("Υπάρχει πρόβλημα αποθέματος στο καλάθι.")

    existing = find_order_for_payment_intent(
        stripe_payment_intent_id,
        user=request.user,
    )
    if existing:
        return existing

    total_cost = cart_total + base_courier_fee
    verify_card_payment_intent(
        stripe_payment_intent_id,
        user=request.user,
        checkout_session_key=request.session.session_key,
        expected_total=total_cost,
    )
    try:
        return _create_order_from_checkout(
            request,
            cart=cart,
            checkout_data=checkout_data,
            payment_method=Order.PAYMENT_METHOD_CARD,
            courier_fee=base_courier_fee,
            cart_total=cart_total,
            total_cost=total_cost,
            order_status=card_order_status(),
            stripe_payment_intent_id=stripe_payment_intent_id,
        )
    except InsufficientStockError as exc:
        _report_stock_error(request, exc)
        raise StripePaymentError("Υπάρχει πρόβλημα αποθέματος στο καλάθι.") from exc


@login_required
def checkout_payment_view(request):
    """Step 3: payment method + order creation."""
    empty_cart_redirect = _redirect_if_cart_empty(request)
    if empty_cart_redirect:
        return empty_cart_redirect

    checkout_data = request.session.get(SESSION_KEY)
    if not checkout_data:
        messages.info(request, "Συμπλήρωσε πρώτα τη διεύθυνση παράδοσης.")
        return redirect("checkout:address")
    if "delivery_method" not in checkout_data:
        messages.info(request, "Επίλεξε πρώτα τρόπο παράδοσης.")
        return redirect("checkout:delivery")

    cart = get_cart(request)
    stock_redirect = _redirect_if_stock_issues(
        request,
        cart,
        redirect_to="checkout:payment",
    )
    if stock_redirect:
        return stock_redirect

    cart_total = cart.total
    base_courier_fee = Decimal(checkout_data["courier_fee"])
    cod_courier_fee = calculate_courier_fee(
        checkout_data["postal_code"],
        checkout_data["delivery_method"],
        cart=cart,
        cart_total=cart_total,
        is_cash_on_delivery=True,
    )
    payment_options = build_payment_options(
        base_courier_fee=base_courier_fee,
        cod_courier_fee=cod_courier_fee,
        cart_total=cart_total,
        delivery_method=checkout_data["delivery_method"],
    )
    selected_payment_method = Order.PAYMENT_METHOD_CARD
    total_cost = cart_total + base_courier_fee
    sidebar = _checkout_sidebar_context(
        request,
        courier_fee=base_courier_fee,
        show_shipping_breakdown=True,
    )

    # Return from Stripe 3D Secure redirect — complete order server-side.
    if request.method == "GET":
        redirect_status = request.GET.get("redirect_status")
        payment_intent_id = (request.GET.get("payment_intent") or "").strip()
        if redirect_status == "succeeded" and payment_intent_id and stripe_payments_enabled():
            try:
                order = _finalize_card_checkout(
                    request,
                    cart=cart,
                    checkout_data=checkout_data,
                    cart_total=cart_total,
                    base_courier_fee=base_courier_fee,
                    stripe_payment_intent_id=payment_intent_id,
                )
                return redirect("checkout:confirmation", order_id=order.id)
            except StripePaymentError as exc:
                messages.error(request, str(exc))
        elif redirect_status == "failed":
            messages.error(request, "Η πληρωμή με κάρτα απέτυχε. Δοκίμασε ξανά.")

    if request.method == "POST":
        form = PaymentMethodForm(request.POST)
        selected_payment_method = request.POST.get(
            "payment_method",
            Order.PAYMENT_METHOD_CARD,
        )
        stock_issues = cart.get_stock_issues()
        if stock_issues:
            for item, issue in stock_issues.items():
                messages.error(request, f"{item.product_variant}: {issue}")
        elif form.is_valid():
            payment_method = form.cleaned_data["payment_method"]
            if (
                checkout_data["delivery_method"] == Order.DELIVERY_METHOD_BOX_NOW
                and payment_method == Order.PAYMENT_METHOD_COD
            ):
                messages.error(
                    request,
                    "Η παράδοση σε BOX NOW locker δεν υποστηρίζει αντικαταβολή.",
                )
                return redirect("checkout:payment")
            is_cod = payment_method == Order.PAYMENT_METHOD_COD
            courier_fee = cod_courier_fee if is_cod else base_courier_fee
            total_cost = cart_total + courier_fee
            order_status = Order.STATUS_NEW
            stripe_payment_intent_id = ""

            if payment_method == Order.PAYMENT_METHOD_CARD:
                if not stripe_payments_enabled():
                    messages.error(
                        request,
                        "Η πληρωμή με κάρτα δεν είναι διαθέσιμη αυτή τη στιγμή.",
                    )
                    return redirect("checkout:payment")
                stripe_payment_intent_id = request.POST.get(
                    "stripe_payment_intent_id",
                    "",
                ).strip()
                try:
                    order = _finalize_card_checkout(
                        request,
                        cart=cart,
                        checkout_data=checkout_data,
                        cart_total=cart_total,
                        base_courier_fee=base_courier_fee,
                        stripe_payment_intent_id=stripe_payment_intent_id,
                    )
                except StripePaymentError as exc:
                    messages.error(request, str(exc))
                    return redirect("checkout:payment")
                return redirect("checkout:confirmation", order_id=order.id)

            try:
                order = _create_order_from_checkout(
                    request,
                    cart=cart,
                    checkout_data=checkout_data,
                    payment_method=payment_method,
                    courier_fee=courier_fee,
                    cart_total=cart_total,
                    total_cost=total_cost,
                    order_status=order_status,
                    stripe_payment_intent_id=stripe_payment_intent_id,
                )
            except InsufficientStockError as exc:
                _report_stock_error(request, exc)
                return redirect("checkout:payment")
            return redirect("checkout:confirmation", order_id=order.id)
    else:
        form = PaymentMethodForm()

    return render(request, "checkout/payment.html", {
        **sidebar,
        "form": form,
        "cart": cart,
        "checkout_data": checkout_data,
        "cart_total": cart_total,
        "courier_fee": base_courier_fee,
        "cod_courier_fee": cod_courier_fee,
        "total_cost": total_cost,
        "payment_options": payment_options,
        "selected_payment_method": selected_payment_method,
        "stripe_enabled": stripe_payments_enabled(),
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "checkout_step": CHECKOUT_STEP_PAYMENT,
        "checkout_steps": build_checkout_steps(CHECKOUT_STEP_PAYMENT, checkout_data),
    })


@login_required
@require_POST
def create_payment_intent_view(request):
    """Create a Stripe PaymentIntent for the current checkout card payment."""
    empty_cart_redirect = _redirect_if_cart_empty(request)
    if empty_cart_redirect:
        return JsonResponse({"error": "Το καλάθι είναι άδειο."}, status=400)

    checkout_data, cart, cart_total, base_courier_fee, _cod_fee = _get_checkout_payment_context(
        request
    )
    if checkout_data is None:
        return JsonResponse({"error": "Μη ολοκληρωμένο checkout."}, status=400)

    stock_issues = cart.get_stock_issues()
    if stock_issues:
        return JsonResponse({"error": "Πρόβλημα αποθέματος στο καλάθι."}, status=400)

    total_cost = cart_total + base_courier_fee
    try:
        intent = create_checkout_payment_intent(
            total_cost=total_cost,
            user=request.user,
            checkout_session_key=request.session.session_key,
        )
    except StripeNotConfiguredError:
        return JsonResponse(
            {"error": "Η πληρωμή με κάρτα δεν είναι διαθέσιμη."},
            status=503,
        )

    return JsonResponse(
        {
            "clientSecret": intent.client_secret,
            "paymentIntentId": intent.id,
        }
    )


@csrf_exempt
def stripe_webhook_view(request):
    """
    Stripe webhook endpoint — verifies signatures and handles payment events.

    Use `stripe listen --forward-to localhost:8000/checkout/stripe/webhook/`
    during local development.
    """
    import stripe

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse({"error": "Webhook not configured"}, status=503)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return JsonResponse({"error": "Invalid payload"}, status=400)

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        Order.objects.filter(
            stripe_payment_intent_id=intent["id"],
            status__in=(Order.STATUS_PENDING, Order.STATUS_NEW),
        ).update(status=Order.STATUS_PAID)
    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        Order.objects.filter(
            stripe_payment_intent_id=intent["id"],
            status__in=(Order.STATUS_PENDING, Order.STATUS_NEW),
        ).update(status=Order.STATUS_FAILED)

    return JsonResponse({"received": True})


@csrf_exempt
@require_POST
def boxnow_webhook_view(request):
    """
    BOX NOW parcel events (CloudEvents). Register this URL in the partner portal:

        https://<your-domain>/checkout/boxnow/webhook/
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        verify_boxnow_signature(
            request.body,
            payload.get("datasignature") or request.META.get("HTTP_X_BOXNOW_SIGNATURE", ""),
        )
        apply_boxnow_parcel_event(payload)
    except BoxNowWebhookError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"received": True})


@login_required
def order_confirmation_view(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product_variant__product"),
        id=order_id,
        user=request.user,
    )
    context = build_order_detail_context(order, show_success_banner=True)
    return render(request, "checkout/confirmation.html", context)
