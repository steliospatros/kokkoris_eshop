from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("<int:order_id>/cancel/", views.cancel_order_view, name="cancel_order"),
]
