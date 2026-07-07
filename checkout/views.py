from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from cart.cart import get_cart
from orders.models import Order, OrderItem

from .delivery import calculate_courier_fee, is_within_athens_urban_area
from .forms import CheckoutAddressForm, PaymentMethodForm

# Single session key holding the whole in-progress checkout: address details
# from Step 1 (address.html), plus delivery_method/courier_fee once Step 2
# (delivery.html) has been completed. Cleared once the order is created.
SESSION_KEY = "checkout_data"


def _redirect_if_cart_empty(request):
    """Shared guard: every checkout step needs a non-empty cart."""
    cart = get_cart(request)
    if cart.total_items == 0:
        messages.error(request, "Το καλάθι σου είναι άδειο.")
        return redirect("home")
    return None


@login_required
def checkout_address_view(request):
    """
    Step 1: delivery address, with Google Maps Places Autocomplete + a
    draggable pin for precise location. Submitting the form both saves the
    profile fields permanently on request.user AND stashes the full
    checkout dataset (including preferred_delivery_time, which has no
    CustomUser field) in the session, ready to be "frozen" onto the Order
    once checkout completes.
    """
    empty_cart_redirect = _redirect_if_cart_empty(request)
    if empty_cart_redirect:
        return empty_cart_redirect

    if request.method == "POST":
        form = CheckoutAddressForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            request.session[SESSION_KEY] = {
                "phone_number": form.cleaned_data["phone_number"],
                "city": form.cleaned_data["city"],
                "address": form.cleaned_data["address"],
                "postal_code": form.cleaned_data["postal_code"],
                "floor": form.cleaned_data["floor"],
                "latitude": str(form.cleaned_data["latitude"]),
                "longitude": str(form.cleaned_data["longitude"]),
                "delivery_notes": form.cleaned_data["delivery_notes"],
                "preferred_delivery_time": form.cleaned_data["preferred_delivery_time"],
            }
            return redirect("checkout:delivery")
    else:
        form = CheckoutAddressForm(instance=request.user)

    return render(request, "checkout/address.html", {
        "form": form,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
def checkout_delivery_view(request):
    """
    Step 2: delivery method. Within the Athens urban area (postal codes
    10-18), the customer freely picks free company delivery vs courier;
    outside that area, courier is mandatory and no free option is shown.
    The final total for every available option is computed server-side (via
    calculate_courier_fee) and shown up front, so the page can update the
    displayed total instantly (plain inline JS, no AJAX needed) as soon as
    the customer picks an option - before they even submit.
    """
    empty_cart_redirect = _redirect_if_cart_empty(request)
    if empty_cart_redirect:
        return empty_cart_redirect

    checkout_data = request.session.get(SESSION_KEY)
    if not checkout_data:
        messages.info(request, "Συμπλήρωσε πρώτα τη διεύθυνση παράδοσης.")
        return redirect("checkout:address")

    postal_code = checkout_data["postal_code"]
    within_urban_area = is_within_athens_urban_area(postal_code)
    cart = get_cart(request)
    cart_total = cart.total

    options = []
    if within_urban_area:
        options.append({
            "value": Order.DELIVERY_METHOD_COMPANY,
            "label": "Δωρεάν παράδοση από υπάλληλο (3-4 εργάσιμες ημέρες)",
            "fee": Decimal("0.00"),
            "total": cart_total,
        })
    courier_fee = calculate_courier_fee(postal_code, Order.DELIVERY_METHOD_COURIER)
    options.append({
        "value": Order.DELIVERY_METHOD_COURIER,
        "label": "Courier",
        "fee": courier_fee,
        "total": cart_total + courier_fee,
    })
    valid_values = {option["value"] for option in options}

    if request.method == "POST":
        delivery_method = request.POST.get("delivery_method")
        if delivery_method not in valid_values:
            messages.error(request, "Επίλεξε έναν έγκυρο τρόπο παράδοσης.")
        else:
            # Recomputed server-side - never trust a fee value from the client.
            fee = calculate_courier_fee(postal_code, delivery_method)
            data = dict(checkout_data)
            data["delivery_method"] = delivery_method
            data["courier_fee"] = str(fee)
            request.session[SESSION_KEY] = data
            return redirect("checkout:payment")

    return render(request, "checkout/delivery.html", {
        "options": options,
        "within_urban_area": within_urban_area,
        "cart_total": cart_total,
    })


@login_required
def checkout_payment_view(request):
    """
    Step 3: payment method selection + actual Order/OrderItem creation.
    Card payments are NOT actually charged here - no card form exists yet
    (real Stripe integration, where card details go straight to Stripe and
    never touch our server/database, is a separate future step). Choosing
    "Card" here is just a stated intent; the order is created as 'pending'
    either way, and staff mark it 'paid' manually via the admin once money
    has actually been received.
    """
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
    cart_total = cart.total
    courier_fee = Decimal(checkout_data["courier_fee"])
    total_cost = cart_total + courier_fee

    if request.method == "POST":
        form = PaymentMethodForm(request.POST)
        stock_issues = cart.get_stock_issues()
        if stock_issues:
            for item, issue in stock_issues.items():
                messages.error(request, f"{item.product_variant}: {issue}")
        elif form.is_valid():
            order = Order.objects.create(
                user=request.user,
                payment_method=form.cleaned_data["payment_method"],
                status=Order.STATUS_NEW,
                cart_cost=cart_total,
                courier_fee=courier_fee,
                total_cost=total_cost,
                delivery_method=checkout_data["delivery_method"],
                delivery_phone_number=checkout_data["phone_number"],
                delivery_city=checkout_data["city"],
                delivery_address=checkout_data["address"],
                delivery_postal_code=checkout_data["postal_code"],
                delivery_floor=checkout_data.get("floor", ""),
                delivery_latitude=Decimal(checkout_data["latitude"]),
                delivery_longitude=Decimal(checkout_data["longitude"]),
                delivery_notes=checkout_data.get("delivery_notes", ""),
                preferred_delivery_time=checkout_data.get("preferred_delivery_time", ""),
            )
            for item in list(cart.items):
                OrderItem.objects.create(
                    order=order,
                    product_variant=item.product_variant,
                    quantity=item.quantity,
                    price_at_purchase=item.product_variant.price,
                )
            cart.clear()
            del request.session[SESSION_KEY]
            return redirect("checkout:confirmation", order_id=order.id)
    else:
        form = PaymentMethodForm()

    return render(request, "checkout/payment.html", {
        "form": form,
        "cart": cart,
        "checkout_data": checkout_data,
        "cart_total": cart_total,
        "courier_fee": courier_fee,
        "total_cost": total_cost,
    })


@login_required
def order_confirmation_view(request, order_id):
    """
    Simple placeholder confirmation page shown right after an order is
    created. Full order-history UI comes later (Part 5+); for now this is
    also the only place the customer can cancel a fresh order from (see
    orders.views.cancel_order_view) - the button/logic will be reused as-is
    once a proper order history page exists.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "checkout/confirmation.html", {"order": order})
