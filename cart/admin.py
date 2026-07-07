from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    """Allows viewing a user's cart contents directly on the Cart page."""
    model = CartItem
    extra = 0
    fields = ("product_variant", "quantity", "subtotal")
    readonly_fields = ("subtotal",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Admin configuration for persistent (registered-user) carts. Guest
    carts are never stored in the database, so they cannot and do not
    appear here - by design.
    """
    list_display = ("id", "user", "total_items", "total", "updated_at")
    search_fields = ("user__email",)
    inlines = [CartItemInline]

    @admin.display(description="Items")
    def total_items(self, cart):
        return cart.total_items

    @admin.display(description="Total (EUR)")
    def total(self, cart):
        return cart.total


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Standalone view of cart lines, useful for scanning what's in active carts."""
    list_display = ("cart", "product_variant", "quantity", "subtotal", "added_at")
    search_fields = ("cart__user__email", "product_variant__product__name")
