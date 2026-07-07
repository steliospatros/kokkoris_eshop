from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Allows viewing/editing an order's line items directly on the Order page."""
    model = OrderItem
    extra = 0
    fields = ("product_variant", "quantity", "price_at_purchase", "line_total")
    readonly_fields = ("line_total",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin configuration for Orders. Useful right now for manually inspecting
    test orders; will become the main order-management screen once Part 4
    (checkout) is wired up to actually create real orders.
    """
    list_display = (
        "id", "user", "order_date", "payment_method", "status",
        "delivery_method", "cart_cost", "courier_fee", "total_cost",
    )
    list_editable = ("status",)
    list_filter = ("status", "payment_method", "delivery_method")
    search_fields = ("user__email", "id")
    date_hierarchy = "order_date"
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {
            "fields": ("user", "order_date", "payment_method", "status", "special_notes"),
        }),
        ("Κόστος", {
            "fields": ("cart_cost", "courier_fee", "total_cost"),
        }),
        ("Παράδοση (snapshot τη στιγμή της παραγγελίας)", {
            "fields": (
                "delivery_method", "delivery_phone_number", "delivery_city",
                "delivery_address", "delivery_postal_code", "delivery_floor",
                "delivery_latitude", "delivery_longitude", "delivery_notes",
                "preferred_delivery_time",
            ),
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Standalone view of order lines, useful for scanning sales across all orders."""
    list_display = ("order", "product_variant", "quantity", "price_at_purchase", "line_total")
    search_fields = ("order__id", "product_variant__product__name")
