from django.urls import path

from . import views

app_name = "checkout"

urlpatterns = [
    path("address/", views.checkout_address_view, name="address"),
    path("delivery/", views.checkout_delivery_view, name="delivery"),
    path("payment/", views.checkout_payment_view, name="payment"),
    path("confirmation/<int:order_id>/", views.order_confirmation_view, name="confirmation"),
]
