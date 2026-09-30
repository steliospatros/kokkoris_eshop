"""Public sitemaps for Google / search engines."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from products.catalog import get_catalog_queryset, get_product_detail_queryset
from products.company_pages import has_brand_page
from products.models import Company


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "home",
            "products:dogs",
            "products:cats",
            "products:all",
            "products:brands",
        ]

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return get_product_detail_queryset().order_by("slug")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("products:detail", kwargs={"slug": obj.slug})


class BrandSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        active_ids = (
            get_catalog_queryset()
            .values_list("company_id", flat=True)
            .distinct()
        )
        companies = Company.objects.filter(pk__in=active_ids).order_by("name")
        return [c for c in companies if has_brand_page(c.code)]

    def location(self, obj):
        return reverse("products:company", kwargs={"company_code": obj.code})
