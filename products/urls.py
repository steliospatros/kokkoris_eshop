from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("search/", views.search_suggestions, name="search_suggestions"),
    path("dogs/", views.catalog_dogs, name="dogs"),
    path("cats/", views.catalog_cats, name="cats"),
    path("all/", views.catalog_all, name="all"),
    path("brands/", views.catalog_brands, name="brands"),
]
