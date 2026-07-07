from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("status/", views.status, name="status"),
    path("add/", views.add, name="add"),
    path("update/", views.update, name="update"),
]
