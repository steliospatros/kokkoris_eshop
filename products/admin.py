from django.contrib import admin

from .models import AnimalType, Category, Company, Product, ProductVariant


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin configuration for the Company (brand) lookup table."""
    list_display = ("name", "code", "has_logo")
    search_fields = ("name", "code")

    @admin.display(boolean=True, description="Logo")
    def has_logo(self, obj):
        return bool(obj.logo)


@admin.register(AnimalType)
class AnimalTypeAdmin(admin.ModelAdmin):
    """Admin configuration for the AnimalType lookup table."""
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for the Category lookup table."""
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class ProductVariantInline(admin.TabularInline):
    """
    Allows editing a Product's variants (package sizes/prices/stock)
    directly from the Product edit page, instead of a separate screen.
    """
    model = ProductVariant
    extra = 1
    fields = ("weight", "sku", "price", "stock", "availability")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for the main Product catalog."""
    list_display = ("name", "company", "animal_type", "category", "is_active")
    list_filter = ("company", "animal_type", "category", "is_active")
    search_fields = ("name", "company__name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Admin configuration for standalone variant management. Optimized for a
    fast end-of-day stock update workflow: 'stock' is editable directly from
    the list view (like a spreadsheet), so many variants can be updated and
    saved in a single click instead of opening each one individually.
    """
    list_display = ("product", "weight", "sku", "price", "stock", "availability", "is_in_stock")
    list_display_links = ("product",)
    list_editable = ("stock", "availability")
    list_filter = ("product__category", "product__animal_type", "product__company", "availability")
    search_fields = ("product__name", "sku")
    list_per_page = 200
    ordering = ("product__name", "weight")
