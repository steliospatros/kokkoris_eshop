from collections import OrderedDict
from datetime import date, datetime, timedelta

from django.utils import timezone

from accounts.profile_labels import (
    DELIVERY_METHOD_LABELS,
    ORDER_STATUS_LABELS,
)
from orders.models import Order
from orders.presentation import (
    build_delivery_map_url,
    build_delivery_maps_link,
    build_order_detail_context,
    build_order_item_rows,
    build_payment_display,
)
from products.catalog import format_decimal_greek


PERIOD_DAY = "day"
PERIOD_WEEK = "week"
PERIOD_MONTH = "month"

PERIOD_CHOICES = (
    (PERIOD_DAY, "Ημέρα"),
    (PERIOD_WEEK, "Εβδομάδα"),
    (PERIOD_MONTH, "Μήνας"),
)

STATUS_UNDELIVERED = "undelivered"
STATUS_ALL = "all"
STATUS_COMPLETED = "completed"

STATUS_FILTER_CHOICES = (
    (STATUS_UNDELIVERED, "Ενεργές (μη παραδοθείσες)"),
    (STATUS_ALL, "Όλες οι παραγγελίες"),
    (STATUS_COMPLETED, "Ολοκληρωμένες"),
)

DELIVERY_ALL = "all"
DELIVERY_COURIER = "courier"
DELIVERY_COMPANY = "company"
DELIVERY_BOX_NOW = "box_now"

# Company delivery is the shop default (~all Athens orders). Keep it first
# and treat it as the implicit filter when the URL omits `delivery`.
DELIVERY_FILTER_CHOICES = (
    (DELIVERY_COMPANY, "Από υπάλληλο"),
    (DELIVERY_COURIER, "Courier"),
    (DELIVERY_BOX_NOW, "BOX NOW"),
    (DELIVERY_ALL, "Όλες"),
)
VALID_DELIVERY_FILTERS = {key for key, _label in DELIVERY_FILTER_CHOICES}

UNDELIVERED_STATUSES = Order.IN_PROGRESS_STATUSES + (
    Order.STATUS_CANCELLATION_REQUESTED,
)


def parse_anchor_date(raw):
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return timezone.localdate()


def parse_week_value(raw):
    """Parse HTML week input value ``YYYY-Www``."""
    if not raw:
        return None
    try:
        year_str, week_str = raw.upper().split("-W", 1)
        return datetime.strptime(f"{year_str}-W{week_str}-1", "%G-W%V-%u").date()
    except ValueError:
        return None


def parse_month_value(raw):
    """Parse HTML month input value ``YYYY-MM``."""
    if not raw:
        return None
    try:
        year_str, month_str = raw.split("-", 1)
        return date(int(year_str), int(month_str), 1)
    except (ValueError, TypeError):
        return None


def week_input_value(anchor_date):
    iso = anchor_date.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def month_input_value(anchor_date):
    return anchor_date.strftime("%Y-%m")


def week_bounds(anchor_date):
    """Monday–Sunday window containing anchor_date."""
    week_start = anchor_date - timedelta(days=anchor_date.weekday())
    return week_start, week_start + timedelta(days=7)


def month_bounds(anchor_date):
    month_start = anchor_date.replace(day=1)
    if anchor_date.month == 12:
        next_month = date(anchor_date.year + 1, 1, 1)
    else:
        next_month = date(anchor_date.year, anchor_date.month + 1, 1)
    return month_start, next_month


def filter_orders_by_period(queryset, period, anchor_date):
    if period == PERIOD_DAY:
        return queryset.filter(order_date__date=anchor_date)
    if period == PERIOD_WEEK:
        week_start, week_end = week_bounds(anchor_date)
        return queryset.filter(
            order_date__date__gte=week_start,
            order_date__date__lt=week_end,
        )
    if period == PERIOD_MONTH:
        month_start, next_month = month_bounds(anchor_date)
        return queryset.filter(
            order_date__date__gte=month_start,
            order_date__date__lt=next_month,
        )
    return queryset


def apply_status_filter(queryset, status_filter):
    if status_filter == STATUS_UNDELIVERED:
        return queryset.filter(status__in=UNDELIVERED_STATUSES)
    if status_filter == STATUS_COMPLETED:
        return queryset.filter(status=Order.STATUS_DELIVERED)
    return queryset


def apply_delivery_filter(queryset, delivery_filter):
    if delivery_filter == DELIVERY_COURIER:
        return queryset.filter(delivery_method=Order.DELIVERY_METHOD_COURIER)
    if delivery_filter == DELIVERY_BOX_NOW:
        return queryset.filter(delivery_method=Order.DELIVERY_METHOD_BOX_NOW)
    if delivery_filter == DELIVERY_COMPANY:
        return queryset.filter(delivery_method=Order.DELIVERY_METHOD_COMPANY)
    return queryset


def build_filter_query_params(
    *,
    status_filter,
    delivery_filter,
    period,
    anchor_date,
    week_value,
    month_value,
    user_email,
    use_period_filter,
):
    params = {"status": status_filter}
    if delivery_filter != DELIVERY_COMPANY:
        params["delivery"] = delivery_filter
    if user_email:
        params["user"] = user_email
    if use_period_filter:
        params["range"] = "1"
        params["period"] = period
        params["date"] = anchor_date.isoformat()
        if period == PERIOD_WEEK:
            params["week"] = week_value
        elif period == PERIOD_MONTH:
            params["month"] = month_value
    return params


def _delivery_address_display(order):
    parts = [order.delivery_address, order.delivery_city, order.delivery_postal_code]
    if order.delivery_floor:
        parts.insert(1, order.delivery_floor)
    return ", ".join(part for part in parts if part)


def build_order_row(order):
    item_rows = build_order_item_rows(order)
    return {
        "id": order.pk,
        "order_code": order.order_code,
        "public_code": order.public_code_display,
        "user_email": order.user.email,
        "user_name": order.user.get_full_name(),
        "order_date": order.order_date,
        "status": order.status,
        "status_label": ORDER_STATUS_LABELS.get(order.status, order.get_status_display()),
        "payment_method": order.payment_method,
        **build_payment_display(order),
        "delivery_method": order.delivery_method,
        "is_courier": order.delivery_method in (
            Order.DELIVERY_METHOD_COURIER,
            Order.DELIVERY_METHOD_BOX_NOW,
        ),
        "delivery_label": DELIVERY_METHOD_LABELS.get(
            order.delivery_method,
            order.get_delivery_method_display(),
        ),
        "total_display": format_decimal_greek(order.total_cost),
        "cart_display": format_decimal_greek(order.cart_cost),
        "courier_display": format_decimal_greek(order.courier_fee),
        "courier_is_free": order.courier_fee == 0,
        "item_rows": item_rows,
        "item_count": sum(row["quantity"] for row in item_rows),
        "delivery_address_display": _delivery_address_display(order),
        "delivery_phone": order.delivery_phone_number or "",
        "delivery_notes": order.delivery_notes or "",
        "preferred_delivery_time": order.preferred_delivery_time or "",
        "is_cancellation_request": order.status == Order.STATUS_CANCELLATION_REQUESTED,
        "cancellation_requested_at": order.cancellation_requested_at,
        "cancellation_reason": (order.cancellation_reason or "").strip(),
        "stripe_payment_intent_id": order.stripe_payment_intent_id,
        "stripe_refund_id": order.stripe_refund_id,
        "is_refunded": bool(order.stripe_refund_id),
        "detail_url": f"/administration/orders/{order.pk}/",
        "map_thumb_url": build_delivery_map_url(order, size="120x120", zoom=16),
        "map_url": build_delivery_map_url(order, size="640x320", zoom=16),
        "maps_link": build_delivery_maps_link(order),
    }


def _week_label(week_start):
    week_end = week_start + timedelta(days=6)
    return f"{week_start.strftime('%d/%m/%Y')} – {week_end.strftime('%d/%m/%Y')}"


def group_orders(orders, *, period=PERIOD_DAY, use_period_filter=False):
    """
    Group order rows for the admin list.

    - Default / day filter: by calendar day (newest first).
    - Week filter: by calendar day within the week.
    - Month filter: by ISO week ranges within the month.
    """
    rows = [build_order_row(order) for order in orders]

    if use_period_filter and period == PERIOD_MONTH:
        buckets = OrderedDict()
        for row in rows:
            day = timezone.localtime(row["order_date"]).date()
            week_start = day - timedelta(days=day.weekday())
            buckets.setdefault(week_start, []).append(row)
        return [
            {
                "date": week_start,
                "date_label": f"Εβδομάδα {_week_label(week_start)}",
                "orders": bucket_rows,
            }
            for week_start, bucket_rows in buckets.items()
        ]

    buckets = OrderedDict()
    for row in rows:
        day = timezone.localtime(row["order_date"]).date()
        buckets.setdefault(day, []).append(row)

    return [
        {
            "date": day,
            "date_label": day.strftime("%d/%m/%Y"),
            "orders": bucket_rows,
        }
        for day, bucket_rows in buckets.items()
    ]


def _period_range_label(period, anchor_date):
    if period == PERIOD_WEEK:
        week_start, week_end_exclusive = week_bounds(anchor_date)
        week_end = week_end_exclusive - timedelta(days=1)
        return f"{week_start.strftime('%d/%m/%Y')} – {week_end.strftime('%d/%m/%Y')}"
    if period == PERIOD_MONTH:
        month_start, next_month = month_bounds(anchor_date)
        month_end = next_month - timedelta(days=1)
        return f"{month_start.strftime('%d/%m/%Y')} – {month_end.strftime('%d/%m/%Y')}"
    return anchor_date.strftime("%d/%m/%Y")


def build_orders_panel_context(
    *,
    period,
    anchor_date,
    user_email="",
    status_filter=STATUS_UNDELIVERED,
    delivery_filter=DELIVERY_COMPANY,
    use_period_filter=False,
):
    base_qs = Order.objects.select_related("user").order_by("-order_date")
    request_qs = apply_delivery_filter(
        base_qs.filter(status=Order.STATUS_CANCELLATION_REQUESTED),
        delivery_filter,
    )

    cancellation_requests = [
        build_order_row(order)
        for order in request_qs.prefetch_related(
            "items__product_variant__product__company"
        )
    ]

    filtered_qs = apply_status_filter(base_qs, status_filter)
    filtered_qs = apply_delivery_filter(filtered_qs, delivery_filter)
    email = (user_email or "").strip()
    if email:
        filtered_qs = filtered_qs.filter(user__email__icontains=email)

    if use_period_filter:
        filtered_qs = filter_orders_by_period(filtered_qs, period, anchor_date)

    order_list = list(
        filtered_qs.prefetch_related("items__product_variant__product__company")[:500]
    )
    grouped_orders = group_orders(
        order_list,
        period=period,
        use_period_filter=use_period_filter,
    )

    period_label = dict(PERIOD_CHOICES).get(period, PERIOD_CHOICES[0][1])
    status_label = dict(STATUS_FILTER_CHOICES).get(status_filter, status_filter)
    delivery_label = dict(DELIVERY_FILTER_CHOICES).get(delivery_filter, delivery_filter)
    week_value = week_input_value(anchor_date)
    month_value = month_input_value(anchor_date)

    return {
        "period": period,
        "period_choices": PERIOD_CHOICES,
        "status_filter": status_filter,
        "status_filter_choices": STATUS_FILTER_CHOICES,
        "status_filter_label": status_label,
        "delivery_filter": delivery_filter,
        "delivery_filter_choices": DELIVERY_FILTER_CHOICES,
        "delivery_filter_label": delivery_label,
        "filter_query_params": build_filter_query_params(
            status_filter=status_filter,
            delivery_filter=delivery_filter,
            period=period,
            anchor_date=anchor_date,
            week_value=week_value,
            month_value=month_value,
            user_email=email,
            use_period_filter=use_period_filter,
        ),
        "anchor_date": anchor_date.isoformat(),
        "week_value": week_value,
        "month_value": month_value,
        "user_email": email,
        "use_period_filter": use_period_filter,
        "period_label": period_label,
        "range_label": _period_range_label(period, anchor_date),
        "cancellation_requests": cancellation_requests,
        "grouped_orders": grouped_orders,
        "orders_count": len(order_list),
    }


def build_admin_order_detail_context(order):
    return build_order_detail_context(order)


def build_payments_panel_context(
    *,
    period,
    anchor_date,
    user_email="",
    status_filter=STATUS_ALL,
    delivery_filter=DELIVERY_COMPANY,
    use_period_filter=False,
):
    """Payment history — card and cash-on-delivery orders with amounts."""
    base_qs = (
        Order.objects.select_related("user")
        .exclude(status=Order.STATUS_FAILED)
        .order_by("-order_date")
    )

    filtered_qs = apply_status_filter(base_qs, status_filter)
    filtered_qs = apply_delivery_filter(filtered_qs, delivery_filter)
    email = (user_email or "").strip()
    if email:
        filtered_qs = filtered_qs.filter(user__email__icontains=email)

    if use_period_filter:
        filtered_qs = filter_orders_by_period(filtered_qs, period, anchor_date)

    payment_list = list(
        filtered_qs.prefetch_related("items__product_variant__product__company")[:500]
    )
    grouped_payments = group_orders(
        payment_list,
        period=period,
        use_period_filter=use_period_filter,
    )

    period_label = dict(PERIOD_CHOICES).get(period, PERIOD_CHOICES[0][1])
    status_label = dict(STATUS_FILTER_CHOICES).get(status_filter, status_filter)
    delivery_label = dict(DELIVERY_FILTER_CHOICES).get(delivery_filter, delivery_filter)
    week_value = week_input_value(anchor_date)
    month_value = month_input_value(anchor_date)

    return {
        "period": period,
        "period_choices": PERIOD_CHOICES,
        "status_filter": status_filter,
        "status_filter_choices": STATUS_FILTER_CHOICES,
        "status_filter_label": status_label,
        "delivery_filter": delivery_filter,
        "delivery_filter_choices": DELIVERY_FILTER_CHOICES,
        "delivery_filter_label": delivery_label,
        "filter_query_params": build_filter_query_params(
            status_filter=status_filter,
            delivery_filter=delivery_filter,
            period=period,
            anchor_date=anchor_date,
            week_value=week_value,
            month_value=month_value,
            user_email=email,
            use_period_filter=use_period_filter,
        ),
        "anchor_date": anchor_date.isoformat(),
        "week_value": week_value,
        "month_value": month_value,
        "user_email": email,
        "use_period_filter": use_period_filter,
        "period_label": period_label,
        "range_label": _period_range_label(period, anchor_date),
        "grouped_payments": grouped_payments,
        "payments_count": len(payment_list),
    }
