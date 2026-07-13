from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.account_hub_view, name="hub"),
    path("details/", views.account_details_view, name="details"),
    path("orders/", views.account_orders_view, name="orders"),
    path("cart/", views.account_cart_view, name="cart"),
    path("profile/", views.profile_view, name="profile"),
    path("api/login/", views.api_login, name="api_login"),
    path("api/signup/", views.api_signup, name="api_signup"),
    path("api/password/reset/", views.api_password_reset, name="api_password_reset"),
    path("api/phone/send-otp/", views.api_phone_send_otp, name="api_phone_send_otp"),
    path("api/phone/verify-otp/", views.api_phone_verify_otp, name="api_phone_verify_otp"),
    path("api/phone/reset/", views.api_phone_reset_verification, name="api_phone_reset"),
]
