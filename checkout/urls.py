from django.urls import path

from . import views

app_name = "checkout"

urlpatterns = [
    path("", views.checkout_index_view, name="index"),
    path("address/", views.checkout_address_view, name="address"),
    path("delivery/", views.checkout_delivery_view, name="delivery"),
    path("payment/", views.checkout_payment_view, name="payment"),
    path("api/payment-intent/", views.create_payment_intent_view, name="payment_intent"),
    path("stripe/webhook/", views.stripe_webhook_view, name="stripe_webhook"),
    path("boxnow/webhook/", views.boxnow_webhook_view, name="boxnow_webhook"),
    path("confirmation/<int:order_id>/", views.order_confirmation_view, name="confirmation"),
]
