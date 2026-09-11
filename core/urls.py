"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core import views as core_views
from products import views as products_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('administration/', include('administration.urls')),
    path('checkout/', include('checkout.urls')),
    path('orders/', include('orders.urls')),
    path('products/', include('products.urls')),
    path('newsletter/', include('newsletter.urls')),
    path('cart/', include('cart.urls')),
    path('wishlist/', include('wishlist.urls')),
    path('', include('pages.urls')),
    path('', products_views.home, name='home'),
]

handler400 = core_views.bad_request
handler403 = core_views.permission_denied
handler404 = core_views.page_not_found
handler500 = core_views.server_error

# Serve user-uploaded media files during local development.
# In production, this is handled by the web server (e.g. Nginx) instead.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
