from django.contrib import admin, messages
from django.utils import timezone

from .models import Order, OrderItem
from .refunds import StripeRefundError, create_stripe_refund_for_order, order_requires_stripe_refund
from .stock import release_stock_for_order


class OrderItemInline(admin.TabularInline):
    """Allows viewing/editing an order's line items directly on the Order page."""
    model = OrderItem
    extra = 0
    fields = ("product_variant", "quantity", "price_at_purchase", "line_total")
    readonly_fields = ("line_total",)


@admin.action(description="Stripe επιστροφή + οριστική ακύρωση")
def process_stripe_refund_and_cancel(modeladmin, request, queryset):
    """
    Admin-only: refund a paid card order via Stripe, release stock, cancel.
    Use after reviewing a customer cancellation request.
    """
    processed = 0
    for order in queryset:
        if order.status not in (
            Order.STATUS_CANCELLATION_REQUESTED,
            Order.STATUS_PAID,
        ):
            messages.error(
                request,
                f"#{order.order_code}: μόνο πληρωμένες ή αιτήματα ακύρωσης.",
            )
            continue
        if not order_requires_stripe_refund(order):
            messages.error(
                request,
                f"#{order.order_code}: δεν είναι πληρωμή με κάρτα/Stripe.",
            )
            continue
        try:
            refund = create_stripe_refund_for_order(order)
        except StripeRefundError as exc:
            messages.error(request, f"#{order.order_code}: {exc}")
            continue

        release_stock_for_order(order)
        order.stripe_refund_id = refund.id
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["stripe_refund_id", "status"])
        processed += 1

    if processed:
        messages.success(
            request,
            f"Ολοκληρώθηκε επιστροφή χρημάτων και ακύρωση για {processed} παραγγελία/ες.",
        )


@admin.action(description="Οριστική ακύρωση (χωρίς Stripe — COD)")
def cancel_without_refund(modeladmin, request, queryset):
    """For cash-on-delivery orders that never went through Stripe."""
    processed = 0
    for order in queryset:
        if order.status == Order.STATUS_CANCELLED:
            continue
        release_stock_for_order(order)
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status"])
        processed += 1
    if processed:
        messages.success(request, f"Ακυρώθηκαν {processed} παραγγελία/ες.")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order management — cancellation requests and Stripe refunds handled here."""
    list_display = (
        "order_code",
        "id",
        "user",
        "order_date",
        "payment_method",
        "status",
        "cancellation_requested_at",
        "delivery_method",
        "total_cost",
    )
    list_editable = ("status",)
    list_filter = ("status", "payment_method", "delivery_method")
    search_fields = ("order_code", "user__email", "stripe_payment_intent_id", "id")
    date_hierarchy = "order_date"
    inlines = [OrderItemInline]
    actions = [process_stripe_refund_and_cancel, cancel_without_refund]
    readonly_fields = (
        "order_code",
        "order_date",
        "cancellation_requested_at",
        "stripe_payment_intent_id",
        "stripe_refund_id",
    )
    fieldsets = (
        (None, {
            "fields": (
                "order_code",
                "user",
                "order_date",
                "payment_method",
                "status",
                "cancellation_requested_at",
                "special_notes",
            ),
        }),
        ("Stripe", {
            "fields": ("stripe_payment_intent_id", "stripe_refund_id"),
        }),
        ("Κόστος", {
            "fields": ("cart_cost", "courier_fee", "total_cost"),
        }),
        ("Παράδοση (snapshot τη στιγμή της παραγγελίας)", {
            "fields": (
                "delivery_method",
                "delivery_phone_number",
                "delivery_city",
                "delivery_address",
                "delivery_postal_code",
                "delivery_floor",
                "delivery_latitude",
                "delivery_longitude",
                "delivery_notes",
                "preferred_delivery_time",
            ),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.GET.get("cancellation_queue") == "1":
            return qs.filter(status=Order.STATUS_CANCELLATION_REQUESTED)
        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        pending = Order.objects.filter(
            status=Order.STATUS_CANCELLATION_REQUESTED
        ).count()
        extra_context["cancellation_requests_pending"] = pending
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Standalone view of order lines, useful for scanning sales across all orders."""
    list_display = ("order", "product_variant", "quantity", "price_at_purchase", "line_total")
    search_fields = ("order__order_code", "order__id", "product_variant__product__name")
