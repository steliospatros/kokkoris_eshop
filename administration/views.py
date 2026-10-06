from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from administration.decorators import administration_user_required, shop_admin_required
from administration.inventory import ADMIN_AVAILABILITY_CHOICES, build_inventory_sections
from products.favourites import build_favourites_rows
from administration.order_queries import (
    DELIVERY_COMPANY,
    PERIOD_DAY,
    PERIOD_MONTH,
    PERIOD_WEEK,
    STATUS_ALL,
    STATUS_COMPLETED,
    STATUS_UNDELIVERED,
    VALID_DELIVERY_FILTERS,
    build_admin_order_detail_context,
    build_orders_panel_context,
    parse_anchor_date,
    parse_month_value,
    parse_week_value,
)
from administration.order_actions import (
    ADMIN_STATUS_CHOICES,
    apply_order_admin_action,
)
from administration.money import build_payments_dashboard_context
from administration.deliveries import (
    SHOW_PENDING,
    apply_delivery_action,
    build_deliveries_panel_context,
)
from administration.offers import (
    build_offer_admin_rows,
    parse_money,
    parse_offer_lines_from_post,
    save_offer,
    variant_picker_options,
)
from administration.permissions import user_is_shop_admin
from administration.services import (
    parse_variant_price,
    set_product_paused,
    set_variant_inventory,
)
from orders.models import Order
from products.catalog import AVAILABILITY_LABELS, format_decimal_greek
from products.models import Offer, Product, ProductVariant


@administration_user_required
def administration_hub_view(request):
    """Administration home — list of available management actions."""
    if not user_is_shop_admin(request.user):
        return redirect("administration:deliveries")
    return render(
        request,
        "administration/hub.html",
        {
            "page_title": "Διαχείριση",
        },
    )


@shop_admin_required
def administration_products_view(request):
    """Products section — redirects to favourites ranking."""
    return redirect("administration:favourites")


@shop_admin_required
def administration_favourites_view(request):
    """Products ranked by dynamic favourite score."""
    return render(
        request,
        "administration/favourites.html",
        {
            "page_title": "Δημοφιλή",
            "products_section": "favourites",
            "favourite_rows": build_favourites_rows(),
        },
    )


@shop_admin_required
def administration_inventory_view(request):
    """All product variants grouped by company, category and animal type."""
    inventory_blocks, inventory_nav = build_inventory_sections()
    return render(
        request,
        "administration/inventory.html",
        {
            "page_title": "Απόθεμα προϊόντων",
            "products_section": "inventory",
            "inventory_blocks": inventory_blocks,
            "inventory_nav": inventory_nav,
            "availability_choices": ADMIN_AVAILABILITY_CHOICES,
        },
    )


@shop_admin_required
def administration_offers_view(request):
    """List active and inactive package offers."""
    return render(
        request,
        "administration/offers.html",
        {
            "page_title": "Προσφορές",
            "products_section": "offers",
            "offer_rows": build_offer_admin_rows(),
        },
    )


@shop_admin_required
def administration_offer_edit_view(request, offer_id=None):
    """Create or update a package offer."""
    offer = None
    if offer_id is not None:
        offer = get_object_or_404(Offer.objects.prefetch_related("items__variant__product"), pk=offer_id)

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        try:
            price = parse_money(request.POST.get("price"))
            lines = parse_offer_lines_from_post(request.POST)
            is_active = request.POST.get("is_active") == "1"
            saved = save_offer(
                title=title,
                price=price,
                is_active=is_active,
                lines=lines,
                offer=offer,
            )
        except ValueError as exc:
            code = str(exc)
            if code == "title_required":
                messages.error(request, "Για πακέτο με πολλά προϊόντα χρειάζεται τίτλος.")
            elif code == "price_not_discount":
                messages.error(
                    request,
                    "Η τιμή προσφοράς πρέπει να είναι μικρότερη από το άθροισμα των κανονικών τιμών.",
                )
            else:
                messages.error(
                    request,
                    "Έλεγξε τιμή και προϊόντα (τουλάχιστον μία συσκευασία με ποσότητα ≥ 1).",
                )
            return redirect(request.path)
        return redirect("administration:offers")

    selected_lines = []
    offer_mode = "single"
    if offer:
        selected_lines = [
            {"variant_id": item.variant_id, "quantity": item.quantity}
            for item in offer.items.all()
        ]
        if len(selected_lines) > 1:
            offer_mode = "package"
    return render(
        request,
        "administration/offer_edit.html",
        {
            "page_title": "Επεξεργασία προσφοράς" if offer else "Νέα προσφορά",
            "products_section": "offers",
            "offer": offer,
            "offer_mode": offer_mode,
            "offer_price_display": format_decimal_greek(offer.price) if offer else "",
            "variant_options": variant_picker_options(),
            "selected_lines": selected_lines,
        },
    )


@shop_admin_required
@require_POST
def administration_offer_delete_view(request, offer_id):
    offer = get_object_or_404(Offer, pk=offer_id)
    title = offer.title
    offer.delete()
    messages.success(request, f"Η προσφορά «{title}» διαγράφηκε.")
    return redirect("administration:offers")


def _inventory_redirect(request, variant_id=None):
    url = reverse("administration:inventory")
    if variant_id:
        url += f"#variant-{variant_id}"
    return url


@shop_admin_required
@require_POST
def administration_adjust_stock_view(request, variant_id):
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)

    raw_stock = (request.POST.get("stock") or "").strip()
    raw_price = (request.POST.get("price") or "").strip()
    availability = (request.POST.get("availability") or "").strip() or None
    try:
        stock = int(raw_stock)
    except ValueError:
        messages.error(request, "Γράψε την ποσότητα σε τεμάχια (π.χ. 12).")
        return redirect(_inventory_redirect(request, variant.pk))

    if stock < 0:
        messages.error(request, "Το απόθεμα δεν μπορεί να είναι αρνητικό.")
        return redirect(_inventory_redirect(request, variant.pk))

    try:
        price = parse_variant_price(raw_price)
    except ValueError:
        messages.error(request, "Γράψε έγκυρη τιμή σε ευρώ (π.χ. 18 ή 18,50).")
        return redirect(_inventory_redirect(request, variant.pk))

    previous_stock = variant.stock
    previous_availability = variant.availability
    previous_price = variant.selling_price
    set_variant_inventory(
        variant, stock=stock, availability=availability, price=price
    )
    variant.refresh_from_db()

    if (
        variant.stock == previous_stock
        and variant.availability == previous_availability
        and variant.selling_price == previous_price
    ):
        messages.info(request, "Δεν έγινε αλλαγή.")
    else:
        status_label = AVAILABILITY_LABELS.get(
            variant.availability, variant.availability
        )
        price_part = f"{variant.selling_price} €"
        if variant.availability == ProductVariant.AVAILABILITY_ON_ORDER:
            messages.success(
                request,
                f"{variant.product.name} ({variant.weight}): "
                f"{price_part} · Κατόπιν παραγγελίας (χωρίς τεμάχια καταστήματος)",
            )
        else:
            messages.success(
                request,
                f"{variant.product.name} ({variant.weight}): "
                f"{price_part} · {variant.stock} τεμ. · {status_label}",
            )
    return redirect(_inventory_redirect(request, variant.pk))


@shop_admin_required
@require_POST
def administration_toggle_product_pause_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    pause = request.POST.get("pause") == "1"
    set_product_paused(product, pause)

    if pause:
        messages.success(request, f"Το προϊόν «{product.name}» κρύφτηκε από το κατάστημα.")
    else:
        messages.success(request, f"Το προϊόν «{product.name}» εμφανίζεται ξανά στο κατάστημα.")
    variant_id = product.variants.order_by("weight").values_list("pk", flat=True).first()
    return redirect(_inventory_redirect(request, variant_id))


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
    valid_statuses = {STATUS_UNDELIVERED, STATUS_ALL, STATUS_COMPLETED}
    if status_filter not in valid_statuses:
        status_filter = STATUS_UNDELIVERED
    delivery_filter = request.GET.get("delivery", DELIVERY_COMPANY)
    if delivery_filter not in VALID_DELIVERY_FILTERS:
        delivery_filter = DELIVERY_COMPANY
    use_period_filter = request.GET.get("range") == "1"
    return period, anchor_date, user_email, status_filter, delivery_filter, use_period_filter


@shop_admin_required
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
    context["admin_status_choices"] = ADMIN_STATUS_CHOICES
    context["order_next"] = request.get_full_path()
    return render(request, "administration/orders.html", context)


@shop_admin_required
def administration_order_detail_view(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("user").prefetch_related(
            "items__product_variant__product__company"
        ),
        pk=order_id,
    )
    context = build_admin_order_detail_context(order)
    context["page_title"] = f"Παραγγελία {order.public_code_display}"
    context["admin_status_choices"] = ADMIN_STATUS_CHOICES
    context["order_next"] = request.get_full_path()
    return render(request, "administration/order_detail.html", context)


@shop_admin_required
@require_POST
def administration_update_order_view(request, order_id):
    order = get_object_or_404(Order.objects.select_related("user"), pk=order_id)
    ok, message = apply_order_admin_action(
        order,
        action=(request.POST.get("action") or "").strip(),
        status=(request.POST.get("status") or "").strip(),
        payment_method=(request.POST.get("payment_method") or "").strip(),
        cancellation_reason=request.POST.get("cancellation_reason") or "",
    )
    if ok:
        messages.success(request, message)
    else:
        messages.error(request, message)
    next_url = request.POST.get("next") or ""
    if not next_url.startswith("/administration/orders"):
        next_url = reverse("administration:orders")
    return redirect(next_url)


@administration_user_required
def administration_deliveries_view(request):
    """Courier tool: pending deliveries oldest-first, one-tap mark delivered."""
    show = request.GET.get("show", SHOW_PENDING)
    priority = request.GET.get("priority", "")
    delivery_filter = request.GET.get("delivery", DELIVERY_COMPANY)
    if delivery_filter not in VALID_DELIVERY_FILTERS:
        delivery_filter = DELIVERY_COMPANY
    context = build_deliveries_panel_context(
        show=show,
        priority=priority,
        delivery_filter=delivery_filter,
    )
    context["page_title"] = "Παραδόσεις"
    return render(request, "administration/deliveries.html", context)


@administration_user_required
@require_POST
def administration_mark_delivery_view(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("user"),
        pk=order_id,
    )
    delivered = request.POST.get("delivered") == "1"
    collected_payment = (request.POST.get("collected_payment") or "").strip()
    action = (request.POST.get("action") or "").strip()
    reason = (request.POST.get("reason") or "").strip()
    if not action:
        action = "deliver" if delivered else "undeliver"
    ok, message = apply_delivery_action(
        order,
        action=action,
        collected_payment=collected_payment,
        reason=reason,
    )
    if ok:
        messages.success(request, message)
        if action == "undeliver":
            show = SHOW_PENDING
        elif action == "deliver":
            show = SHOW_PENDING
        else:
            show = request.POST.get("show") or request.GET.get("show") or SHOW_PENDING
    else:
        messages.error(request, message)
        show = request.POST.get("show") or request.GET.get("show") or SHOW_PENDING
    priority = request.POST.get("priority") or request.GET.get("priority") or ""
    delivery = request.POST.get("delivery") or request.GET.get("delivery") or DELIVERY_COMPANY
    query = f"?show={show}"
    if priority:
        query += f"&priority={priority}"
    if delivery != DELIVERY_COMPANY:
        query += f"&delivery={delivery}"
    return redirect(f"{reverse('administration:deliveries')}{query}")


@shop_admin_required
def administration_payments_view(request):
    period = request.GET.get("period", PERIOD_MONTH)
    if period not in {PERIOD_DAY, PERIOD_WEEK, PERIOD_MONTH}:
        period = PERIOD_MONTH

    anchor_date = parse_anchor_date(request.GET.get("date"))
    if period == PERIOD_WEEK:
        week_anchor = parse_week_value(request.GET.get("week"))
        if week_anchor:
            anchor_date = week_anchor
    elif period == PERIOD_MONTH:
        month_anchor = parse_month_value(request.GET.get("month"))
        if month_anchor:
            anchor_date = month_anchor

    context = build_payments_dashboard_context(
        period=period,
        anchor_date=anchor_date,
    )
    context["page_title"] = "Πληρωμές"
    return render(request, "administration/payments.html", context)
