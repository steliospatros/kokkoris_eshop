"""Money received vs expected for the administration payments page."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import DecimalField, Q, Sum
from django.db.models.functions import Coalesce

from administration.order_queries import (
    PERIOD_CHOICES,
    PERIOD_DAY,
    PERIOD_MONTH,
    PERIOD_WEEK,
    _period_range_label,
    month_bounds,
    month_input_value,
    week_bounds,
    week_input_value,
)
from orders.models import Order
from products.catalog import format_decimal_greek


EXCLUDED_STATUSES = (
    Order.STATUS_CANCELLED,
    Order.STATUS_FAILED,
)

PREPAID_RECEIVED_STATUSES = (
    Order.STATUS_PAID,
    Order.STATUS_DELIVERED,
)

EXPECTED_STATUSES = (
    Order.STATUS_NEW,
    Order.STATUS_PENDING,
)


def period_date_bounds(period, anchor_date):
    if period == PERIOD_WEEK:
        return week_bounds(anchor_date)
    if period == PERIOD_MONTH:
        return month_bounds(anchor_date)
    return anchor_date, anchor_date + timedelta(days=1)


def _sum_cost(queryset):
    return queryset.aggregate(
        total=Coalesce(
            Sum("total_cost"),
            Decimal("0.00"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )["total"]


def _money_block(cash, card):
    total = cash + card
    return {
        "cash": cash,
        "card": card,
        "total": total,
        "cash_display": format_decimal_greek(cash),
        "card_display": format_decimal_greek(card),
        "total_display": format_decimal_greek(total),
    }


def _in_period(field_prefix, start, end):
    return {
        f"{field_prefix}__date__gte": start,
        f"{field_prefix}__date__lt": end,
    }


def build_payments_dashboard_context(*, period, anchor_date):
    start, end = period_date_bounds(period, anchor_date)
    base = Order.objects.exclude(status__in=EXCLUDED_STATUSES)

    prepaid = base.filter(
        payment_method=Order.PAYMENT_METHOD_CARD,
        stripe_payment_intent_id__gt="",
        stripe_refund_id="",
        status__in=PREPAID_RECEIVED_STATUSES,
        **_in_period("order_date", start, end),
    )
    door_card = base.filter(
        status=Order.STATUS_DELIVERED,
        collected_payment_method=Order.PAYMENT_METHOD_CARD,
        stripe_payment_intent_id="",
        **_in_period("delivered_at", start, end),
    )
    door_cash = base.filter(
        status=Order.STATUS_DELIVERED,
        **_in_period("delivered_at", start, end),
    ).filter(
        Q(collected_payment_method=Order.PAYMENT_METHOD_COD)
        | Q(
            collected_payment_method="",
            payment_method=Order.PAYMENT_METHOD_COD,
        )
    )

    received_card = _sum_cost(prepaid) + _sum_cost(door_card)
    received_cash = _sum_cost(door_cash)

    expected_qs = base.filter(
        status__in=EXPECTED_STATUSES,
        **_in_period("order_date", start, end),
    ).filter(
        Q(payment_method=Order.PAYMENT_METHOD_COD)
        | Q(stripe_payment_intent_id="")
    )
    expected_cash = _sum_cost(expected_qs.filter(payment_method=Order.PAYMENT_METHOD_COD))
    expected_card = _sum_cost(
        expected_qs.exclude(payment_method=Order.PAYMENT_METHOD_COD)
    )

    return {
        "period": period,
        "period_choices": PERIOD_CHOICES,
        "anchor_date": anchor_date.isoformat(),
        "week_value": week_input_value(anchor_date),
        "month_value": month_input_value(anchor_date),
        "period_label": dict(PERIOD_CHOICES).get(period, period),
        "range_label": _period_range_label(period, anchor_date),
        "received": _money_block(received_cash, received_card),
        "expected": _money_block(expected_cash, expected_card),
        "received_count": prepaid.count() + door_card.count() + door_cash.count(),
        "expected_count": expected_qs.count(),
    }
