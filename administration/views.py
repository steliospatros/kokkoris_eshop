from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from administration.decorators import administration_user_required
from administration.inventory import build_inventory_sections
from products.favourites import build_favourites_rows
from administration.order_queries import (
    DELIVERY_ALL,
    DELIVERY_COMPANY,
    DELIVERY_COURIER,
    PERIOD_DAY,
    PERIOD_MONTH,
    PERIOD_WEEK,
    STATUS_ALL,
    STATUS_COMPLETED,
    STATUS_NEW,
    STATUS_PAID,
    STATUS_UNDELIVERED,
    build_admin_order_detail_context,
    build_orders_panel_context,
    build_payments_panel_context,
    parse_anchor_date,
    parse_month_value,
    parse_week_value,
)
from administration.services import adjust_variant_stock, set_product_paused
from orders.models import Order
from products.models import Product, ProductVariant


@administration_user_required
def administration_hub_view(request):
    """Administration home — list of available management actions."""
    return render(
        request,
        "administration/hub.html",
        {
            "page_title": "Διαχείριση",
        },
    )


@administration_user_required
def administration_products_view(request):
    """Products section — redirects to favourites ranking."""
    return redirect("administration:favourites")


@administration_user_required
def administration_favourites_view(request):
    """Products ranked by purchase count (favourites table)."""
    return render(
        request,
        "administration/favourites.html",
        {
            "page_title": "Favourites",
            "products_section": "favourites",
            "favourite_rows": build_favourites_rows(),
        },
    )


@administration_user_required
def administration_inventory_view(request):
    """All product variants grouped by company, category and animal type."""
    inventory_sections, inventory_nav = build_inventory_sections()
    return render(
        request,
        "administration/inventory.html",
        {
            "page_title": "Απόθεμα προϊόντων",
            "products_section": "inventory",
            "inventory_sections": inventory_sections,
            "inventory_nav": inventory_nav,
        },
    )


@administration_user_required
@require_POST
def administration_adjust_stock_view(request, variant_id):
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)

    raw_delta = (request.POST.get("delta") or "").strip()
    try:
        delta = int(raw_delta)
    except ValueError:
        messages.error(request, "Μη έγκυρη ποσότητα.")
        return redirect("administration:inventory")

    if delta == 0:
        messages.info(request, "Δεν έγινε αλλαγή στο απόθεμα.")
        return redirect("administration:inventory")

    adjust_variant_stock(variant, delta)
    action = "προστέθηκαν" if delta > 0 else "αφαιρέθηκαν"
    messages.success(
        request,
        f"{variant.product.name} ({variant.weight}): {action} {abs(delta)} τεμ. · Νέο απόθεμα: {variant.stock}",
    )
    return redirect("administration:inventory")


@administration_user_required
@require_POST
def administration_toggle_product_pause_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    pause = request.POST.get("pause") == "1"
    set_product_paused(product, pause)

    if pause:
        messages.success(request, f"Το προϊόν «{product.name}» τέθηκε σε προσωρινή παύση.")
    else:
        messages.success(request, f"Το προϊόν «{product.name}» επανενεργοποιήθηκε στο e-shop.")
    return redirect("administration:inventory")


def _panel_filters(request):
    period = request.GET.get("period", PERIOD_DAY)
    if period not in {PERIOD_DAY, PERIOD_WEEK, PERIOD_MONTH}:
        period = PERIOD_DAY

    anchor_date = parse_anchor_date(request.GET.get("date"))
    if period == PERIOD_WEEK:
        week_anchor = parse_week_value(request.GET.get("week"))
        if week_anchor:
            anchor_date = week_anchor
    elif period == PERIOD_MONTH:
        month_anchor = parse_month_value(request.GET.get("month"))
        if month_anchor:
            anchor_date = month_anchor

    user_email = (request.GET.get("user") or "").strip()
    return period, anchor_date, user_email


def _orders_panel_filters(request):
    period, anchor_date, user_email = _panel_filters(request)
    status_filter = request.GET.get("status", STATUS_UNDELIVERED)
    valid_statuses = {STATUS_UNDELIVERED, STATUS_ALL, STATUS_COMPLETED, STATUS_NEW, STATUS_PAID}
    if status_filter not in valid_statuses:
        status_filter = STATUS_UNDELIVERED
    delivery_filter = request.GET.get("delivery", DELIVERY_ALL)
    valid_deliveries = {DELIVERY_ALL, DELIVERY_COURIER, DELIVERY_COMPANY}
    if delivery_filter not in valid_deliveries:
        delivery_filter = DELIVERY_ALL
    use_period_filter = request.GET.get("range") == "1"
    return period, anchor_date, user_email, status_filter, delivery_filter, use_period_filter


def _payments_panel_filters(request):
    period, anchor_date, user_email = _panel_filters(request)
    status_filter = request.GET.get("status", STATUS_ALL)
    valid_statuses = {STATUS_UNDELIVERED, STATUS_ALL, STATUS_COMPLETED, STATUS_NEW, STATUS_PAID}
    if status_filter not in valid_statuses:
        status_filter = STATUS_ALL
    delivery_filter = request.GET.get("delivery", DELIVERY_ALL)
    valid_deliveries = {DELIVERY_ALL, DELIVERY_COURIER, DELIVERY_COMPANY}
    if delivery_filter not in valid_deliveries:
        delivery_filter = DELIVERY_ALL
    use_period_filter = request.GET.get("range") == "1"
    return period, anchor_date, user_email, status_filter, delivery_filter, use_period_filter


@administration_user_required
def administration_orders_view(request):
    period, anchor_date, user_email, status_filter, delivery_filter, use_period_filter = (
        _orders_panel_filters(request)
    )
    context = build_orders_panel_context(
        period=period,
        anchor_date=anchor_date,
        user_email=user_email,
        status_filter=status_filter,
        delivery_filter=delivery_filter,
        use_period_filter=use_period_filter,
    )
    context["page_title"] = "Διαχείριση παραγγελιών"
    return render(request, "administration/orders.html", context)


@administration_user_required
def administration_order_detail_view(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("user").prefetch_related(
            "items__product_variant__product__company"
        ),
        pk=order_id,
    )
    context = build_admin_order_detail_context(order)
    context["page_title"] = f"Παραγγελία {order.public_code_display}"
    return render(request, "administration/order_detail.html", context)


@administration_user_required
def administration_payments_view(request):
    period, anchor_date, user_email, status_filter, delivery_filter, use_period_filter = (
        _payments_panel_filters(request)
    )
    context = build_payments_panel_context(
        period=period,
        anchor_date=anchor_date,
        user_email=user_email,
        status_filter=status_filter,
        delivery_filter=delivery_filter,
        use_period_filter=use_period_filter,
    )
    context["page_title"] = "Ιστορικό πληρωμών"
    return render(request, "administration/payments.html", context)
