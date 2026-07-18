from django.urls import path

from administration import views

app_name = "administration"

urlpatterns = [
    path("", views.administration_hub_view, name="hub"),
    path("products/", views.administration_products_view, name="products"),
    path("products/favourites/", views.administration_favourites_view, name="favourites"),
    path("products/inventory/", views.administration_inventory_view, name="inventory"),
    path("inventory/", views.administration_inventory_view, name="inventory_legacy"),
    path(
        "inventory/stock/<int:variant_id>/",
        views.administration_adjust_stock_view,
        name="adjust_stock",
    ),
    path(
        "inventory/pause/<int:product_id>/",
        views.administration_toggle_product_pause_view,
        name="toggle_product_pause",
    ),
    path("orders/", views.administration_orders_view, name="orders"),
    path("orders/<int:order_id>/", views.administration_order_detail_view, name="order_detail"),
    path("payments/", views.administration_payments_view, name="payments"),
]
