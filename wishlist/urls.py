from django.urls import path

from . import views

app_name = "wishlist"

urlpatterns = [
    path("", views.list_view, name="list"),
    path("toggle/", views.toggle, name="toggle"),
    path("status/", views.status, name="status"),
]
