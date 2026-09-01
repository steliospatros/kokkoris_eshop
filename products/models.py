from django.db import models
from django.utils.text import slugify
from unidecode import unidecode


def generate_ascii_slug(text):
    """
    Builds a clean, ASCII-only, URL-friendly slug from arbitrary text.

    Greek (or any non-Latin) input is first transliterated to Latin
    characters via unidecode, since Django's default slugify() strips
    non-ASCII characters entirely, which can otherwise produce empty
    or colliding slugs for e.g. Greek-only names.
    """
    return slugify(unidecode(text))


def unique_ascii_slug(instance, text, *, field="slug"):
    """
    Like generate_ascii_slug, but guaranteed not to clash with an existing row.

    Catalogue names are edited after import — the English names shipped in the
    supplier documents are later translated to Greek while the slug keeps its
    original value — so a fresh import can produce a name that transliterates
    onto a slug another row already owns. Appending a counter keeps the save
    from raising IntegrityError.
    """
    base = generate_ascii_slug(text) or "item"
    queryset = instance.__class__.objects.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    candidate = base
    counter = 2
    while queryset.filter(**{field: candidate}).exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


class Company(models.Model):
    """
    Represents a pet food brand/manufacturer (e.g. OWNAT, PROFINE, EVERCLEAN).
    Stored as a lookup table so new brands can be added via the admin
    panel without requiring any code changes.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Brand/manufacturer name, e.g. 'OWNAT'."
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short unique code for the company, e.g. 'OWN'."
    )
    logo = models.ImageField(
        upload_to="companies/logos/",
        blank=True,
        null=True,
        help_text="Optional brand logo image."
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AnimalType(models.Model):
    """
    Represents the target animal for a product (e.g. Dog, Cat).
    Stored as a lookup table so new animal types (e.g. Rabbit, Bird)
    can be added later without requiring any code changes.
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Animal name, e.g. 'Dog', 'Cat'."
    )
    slug = models.SlugField(
        max_length=60,
        unique=True,
        blank=True,
        help_text="URL-friendly identifier, auto-generated from the name."
    )

    class Meta:
        verbose_name = "Animal Type"
        verbose_name_plural = "Animal Types"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        # Auto-generate the slug from the name if it has not been set manually.
        if not self.slug:
            self.slug = unique_ascii_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(models.Model):
    """
    Represents a product category (e.g. Dry Food, Canned Food, Sachets, Litter).
    Stored as a lookup table so new categories can be added via the admin
    panel without requiring any code changes.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name, e.g. 'Dry Food'."
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
        help_text="URL-friendly identifier, auto-generated from the name."
    )
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        # Auto-generate the slug from the name if it has not been set manually.
        if not self.slug:
            self.slug = unique_ascii_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    The 'parent' product record. Holds all information that stays constant
    regardless of package size (e.g. name, brand, ingredients, description).
    Pricing and stock, which vary per package size, live on ProductVariant.
    """
    name = models.CharField(
        max_length=200,
        help_text="Product name, e.g. 'OWNAT Adult Medium'."
    )
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        help_text="URL-friendly identifier, auto-generated from the name."
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="The brand/manufacturer of this product."
    )
    animal_type = models.ForeignKey(
        AnimalType,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="The target animal for this product."
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="The category this product belongs to."
    )
    components = models.TextField(
        blank=True,
        help_text="Ingredients/composition list. Shared across all package sizes."
    )
    description = models.TextField(blank=True)
    bundle_contents = models.TextField(
        blank=True,
        help_text=(
            "For 'Bundle' category products only: a short, Latin-character summary "
            "of what individual items/flavors are mixed inside this pack, "
            "e.g. '2x Chicken in Gravy, 2x Salmon in Jelly'."
        ),
    )
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this product is currently available for sale."
    )
    # Physical shipping attributes used for Box Now locker sizing
    # (chargeable weight = max of real vs volumetric). Courier door
    # delivery is a flat fee and no longer uses these dimensions.
    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Shipping weight in kilograms (kg) for courier billing.",
    )
    length = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Package length in centimetres (cm) for volumetric weight.",
    )
    width = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Package width in centimetres (cm) for volumetric weight.",
    )
    height = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Package height in centimetres (cm) for volumetric weight.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Auto-generate the slug from the name if it has not been set manually.
        if not self.slug:
            self.slug = unique_ascii_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company.name} - {self.name}"


class Favourite(models.Model):
    """
    Popularity tracker for administration — one row per product.
    ``purchase_count`` starts at 0 and increments on each completed purchase.
    """

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="favourite",
    )
    purchase_count = models.PositiveIntegerField(
        default=0,
        help_text="Total units sold across all variants; higher = more popular.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "favourites"
        verbose_name = "Favourite"
        verbose_name_plural = "Favourites"
        ordering = ["-purchase_count", "product__name"]

    def __str__(self):
        return f"{self.product.name} ({self.purchase_count})"


class ProductVariant(models.Model):
    """
    A specific purchasable version of a Product for a given package size
    (e.g. 2kg, 10kg, 15kg). Holds everything that changes per package size:
    weight, price and stock availability.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        help_text="The parent product this variant belongs to."
    )
    # Stored as a plain number; the unit of measurement (kg/L) is resolved
    # in the presentation layer (templates) based on the product's category.
    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Package size as a number (e.g. 2, 10, 15). Unit is inferred from category."
    )
    sku = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Optional unique stock-keeping unit code for this specific variant."
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Price for this specific package size."
    )
    stock = models.PositiveIntegerField(
        default=20,
        help_text="Number of units currently available for this package size."
    )

    AVAILABILITY_AVAILABLE_NOW = "available_now"
    AVAILABILITY_ON_ORDER = "on_order"
    AVAILABILITY_OUT_OF_STOCK = "out_of_stock"
    AVAILABILITY_CHOICES = [
        (AVAILABILITY_AVAILABLE_NOW, "Immediately Available"),
        (AVAILABILITY_ON_ORDER, "On Order (special order from supplier)"),
        (AVAILABILITY_OUT_OF_STOCK, "Out of Stock"),
    ]
    availability = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default=AVAILABILITY_AVAILABLE_NOW,
        help_text=(
            "Set manually by staff - NOT derived automatically from 'stock'. "
            "Used to tell the customer whether this ships from current shop "
            "stock right away, or needs to be specially ordered from the "
            "supplier first (which implies a delivery delay)."
        ),
    )

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        ordering = ["product", "weight"]
        # Prevent duplicate variants of the same weight for the same product.
        constraints = [
            models.UniqueConstraint(
                fields=["product", "weight"],
                name="unique_product_weight"
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.weight}"

    @property
    def is_in_stock(self):
        """Convenience property used across the site to check availability."""
        return self.stock > 0

    @property
    def unit_label(self):
        """kg for food products, L for litter — inferred from category name."""
        if self.product.category.name == "Litter":
            return "L"
        return "kg"

    @property
    def unit_price(self):
        """Price per kg/L for catalog cards (computed, not stored)."""
        if self.weight and self.weight > 0:
            return self.price / self.weight
        return None
