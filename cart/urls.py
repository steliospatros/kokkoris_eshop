from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("status/", views.status, name="status"),
    path("preview/", views.preview, name="preview"),
    path("add/", views.add, name="add"),
    path("update/", views.update, name="update"),
    path("clear/", views.clear, name="clear"),
]
