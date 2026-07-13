from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("plhrofories-katastimatos/", views.info_page_view, {"slug": "store"}, name="store"),
    path("epikoinonia/", views.info_page_view, {"slug": "contact"}, name="contact"),
    path("tropos-apostolis/", views.info_page_view, {"slug": "shipping"}, name="shipping"),
    path("kostos-apostolis/", views.info_page_view, {"slug": "shipping-cost"}, name="shipping_cost"),
    path("politiki-epistrofon/", views.info_page_view, {"slug": "returns"}, name="returns"),
    path("tropos-pliromis/", views.info_page_view, {"slug": "payment"}, name="payment"),
    path("politiki-aporritou/", views.info_page_view, {"slug": "privacy"}, name="privacy"),
]
