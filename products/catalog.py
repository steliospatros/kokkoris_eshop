"""
Catalog presentation helpers — card data for the product grid UI.
"""
import math
import os
import random
import secrets
from decimal import Decimal
from functools import lru_cache
from urllib.parse import urlencode

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Min, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.urls import reverse

from .models import Category, Company, Product, ProductVariant

PER_PAGE_OPTIONS = (24, 36, 48)
DEFAULT_PER_PAGE = 24
PER_PAGE_ALL = "all"

SORT_DEFAULT = "default"
SORT_PRICE_ASC = "price_asc"
SORT_PRICE_DESC = "price_desc"
SORT_STOCK_DESC = "stock_desc"
SORT_UNIT_PRICE_ASC = "unit_price_asc"
SORT_UNIT_PRICE_DESC = "unit_price_desc"

SORT_OPTIONS = (
    (SORT_DEFAULT, "Προεπιλογή"),
    (SORT_PRICE_ASC, "Τιμή αύξουσα"),
    (SORT_PRICE_DESC, "Τιμή φθίνουσα"),
    (SORT_STOCK_DESC, "Ποσότητα"),
    (SORT_UNIT_PRICE_ASC, "Τιμή/κιλό αύξουσα"),
    (SORT_UNIT_PRICE_DESC, "Τιμή/κιλό φθίνουσα"),
)

CATEGORY_LABELS = {
    "Dry Food": "Ξηρά τροφή",
    "Canned Food": "Κονσέρβες",
    "Sachets": "Φακελάκια",
    "Litter": "Άμμος",
    "Bundle": "Πακέτα",
}

DRY_FOOD_CATEGORY_SLUG = "dry-food"
DRY_FOOD_CATEGORY_NAME = "Dry Food"


def shows_unit_price(product):
    """€/kg is only shown for dry-food bags."""
    category = getattr(product, "category", None)
    if category is None:
        return False
    return category.slug == DRY_FOOD_CATEGORY_SLUG or category.name == DRY_FOOD_CATEGORY_NAME

AVAILABILITY_FILTER_IN_STORE = "in_store"
AVAILABILITY_FILTER_ON_ORDER = "on_order"

AVAILABILITY_FILTER_OPTIONS = (
    (AVAILABILITY_FILTER_IN_STORE, "Διαθέσιμο στο κατάστημα"),
    (AVAILABILITY_FILTER_ON_ORDER, "Κατόπιν παραγγελίας"),
)

AVAILABILITY_FILTER_KEYS = {key for key, _ in AVAILABILITY_FILTER_OPTIONS}

ANIMAL_FILTER_OPTIONS = (
    ("dog", "Σκύλος"),
    ("cat", "Γάτα"),
)

ANIMAL_FILTER_KEYS = {key for key, _ in ANIMAL_FILTER_OPTIONS}

ANIMAL_SLUG_LABELS = {
    "dog": "Σκύλος",
    "cat": "Γάτα",
}

# Category tiles shown on /products/dogs/ and /products/cats/ landing pages.
ANIMAL_CATEGORY_SLUGS = {
    "dog": ["dry-food", "canned-food", "sachets", "bundle"],
    "cat": ["dry-food", "canned-food", "sachets", "litter", "bundle"],
}

CATEGORY_SLUG_LABELS = {
    "dry-food": "Ξηρά τροφή",
    "canned-food": "Κονσέρβες",
    "sachets": "Φακελάκια",
    "litter": "Άμμος",
    "bundle": "Πακέτα",
}

CATEGORY_TILE_IMAGES = {
    "dry-food": "images/category-tiles/dry-food.png",
    "canned-food": "images/category-tiles/canned-food.png",
    "sachets": "images/category-tiles/sachets.png",
    "litter": "images/category-tiles/litter.png",
    "bundle": "images/category-tiles/bundles.png",
}

# Test 1_TROFES.pdf — page 1 cats (orange, 4 circles), page 2 dogs (teal, 3).
ANIMAL_LANDING = {
    "cat": {
        "band": "images/animal-landing/cats-band.png",
        "band_px": (2667, 942),
        "categories": ("dry-food", "canned-food", "sachets", "litter"),
        # Pixel-measured from cats-band.png circle rims.
        "cx": (18.97, 39.71, 60.40, 81.10),
        "cy": 44.48,
        "size": 15.45,
    },
    "dog": {
        "band": "images/animal-landing/dogs-band.png",
        "band_px": (2667, 957),
        "categories": ("dry-food", "canned-food", "sachets"),
        # Pixel-measured from dogs-band.png circle rims.
        "cx": (22.08, 49.23, 76.38),
        "cy": 48.80,
        "size": 15.37,
    },
}

# Reference sachet photo: CLUB4PAWS Adult - Rabbit in Jelly 0,08 kg (830×1083).
SACHET_REFERENCE_IMAGE_SIZE = (830, 1083)
SACHET_IMAGE_SCALE_MIN = 0.85
SACHET_IMAGE_SCALE_MAX = 1.55


@lru_cache(maxsize=512)
def _cached_image_pixel_size(image_name):
    from PIL import Image
    from django.core.files.storage import default_storage

    with default_storage.open(image_name, "rb") as handle:
        return Image.open(handle).size


def get_product_image_display_scale(product):
    """
    Sachets with smaller source photos are scaled up to match the reference
    Rabbit in Jelly pouch appearance inside the 120px image slot.
    """
    if not product.category_id or product.category.slug != "sachets":
        return 1.0
    if not product.image:
        return 1.0
    try:
        _width, height = _cached_image_pixel_size(product.image.name)
    except Exception:
        return 1.0

    _ref_w, ref_h = SACHET_REFERENCE_IMAGE_SIZE
    scale = ref_h / height
    return round(max(SACHET_IMAGE_SCALE_MIN, min(scale, SACHET_IMAGE_SCALE_MAX)), 3)


def format_decimal_greek(value, places=2):
    """Format a number with comma as decimal separator (Greek convention)."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        text = f"{value:.{places}f}"
    else:
        text = f"{float(value):.{places}f}"
    return text.replace(".", ",")


def _format_amount_greek(amount: Decimal, *, max_decimals: int | None = None) -> str:
    """Format a Decimal without trailing zeros, without stripping whole tens (10 → 10)."""
    if max_decimals is not None:
        text = format(amount, f".{max_decimals}f")
    else:
        text = format(amount, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def format_weight(weight, unit_label="kg"):
    """
    Human-readable package size with unit.

    Values under 1 kg are shown in grams (e.g. 85 g), not 0,085 kg.
    Litter under 1 L uses ml. Larger amounts keep kg / L.
    """
    if weight is None:
        return ""

    amount = Decimal(weight)
    unit = (unit_label or "kg").strip().lower()

    if unit in {"kg", "κιλό", "κιλά"}:
        if amount > 0 and amount < 1:
            grams = amount * Decimal("1000")
            if grams == grams.to_integral_value():
                text = _format_amount_greek(grams.to_integral_value())
            else:
                text = _format_amount_greek(grams, max_decimals=1)
            return f"{text} g"
        return f"{_format_amount_greek(amount)} kg"

    if unit in {"l", "lt", "λίτρο", "λίτρα"}:
        if amount > 0 and amount < 1:
            millilitres = amount * Decimal("1000")
            if millilitres == millilitres.to_integral_value():
                text = _format_amount_greek(millilitres.to_integral_value())
            else:
                text = _format_amount_greek(millilitres, max_decimals=1)
            return f"{text} ml"
        return f"{_format_amount_greek(amount)} L"

    return f"{_format_amount_greek(amount)} {unit_label}"


SHOP_VISIBLE_AVAILABILITIES = (
    ProductVariant.AVAILABILITY_AVAILABLE_NOW,
    ProductVariant.AVAILABILITY_ON_ORDER,
)


def shop_visible_variant_queryset():
    return ProductVariant.objects.filter(
        availability__in=SHOP_VISIBLE_AVAILABILITIES,
    ).order_by("weight")


def get_default_variant(product):
    """Largest package that is actually offered in the shop."""
    variants = [
        variant
        for variant in product.variants.all()
        if variant.availability in SHOP_VISIBLE_AVAILABILITIES
    ]
    if not variants:
        return None
    return max(variants, key=lambda variant: variant.weight)


AVAILABILITY_LABELS = {
    ProductVariant.AVAILABILITY_AVAILABLE_NOW: "Άμεσα διαθέσιμο",
    ProductVariant.AVAILABILITY_ON_ORDER: "Κατόπιν παραγγελίας",
    ProductVariant.AVAILABILITY_OUT_OF_STOCK: "Μη διαθέσιμο",
}

STOCK_STATUS_AVAILABLE = "available"
STOCK_STATUS_LIMITED = "limited"
STOCK_STATUS_OUT = "out"
STOCK_STATUS_ON_ORDER = "on_order"


def get_stock_display(variant):
    """
    Customer-facing stock state for catalog cards and cart limits.

    For immediately-available variants the label/colour/button state
    follows real stock levels.  On-order variants ignore stock; manual
    out-of-stock is always blocked.
    """
    if variant.availability == ProductVariant.AVAILABILITY_ON_ORDER:
        return {
            "status": STOCK_STATUS_ON_ORDER,
            "label": AVAILABILITY_LABELS[ProductVariant.AVAILABILITY_ON_ORDER],
            "color_class": "text-slate-500",
            "can_add": True,
            "max_quantity": None,
            "button_label": "Αγορά",
        }

    if variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK:
        return {
            "status": STOCK_STATUS_OUT,
            "label": "Έλλειψη",
            "color_class": "text-red-600",
            "can_add": False,
            "max_quantity": 0,
        }

    if variant.stock == 0:
        return {
            "status": STOCK_STATUS_OUT,
            "label": "Έλλειψη",
            "color_class": "text-red-600",
            "can_add": False,
            "max_quantity": 0,
        }

    if variant.stock <= 10:
        return {
            "status": STOCK_STATUS_LIMITED,
            "label": "Περιορισμένη διαθεσιμότητα",
            "color_class": "text-kokkoris-dot-orange",
            "can_add": True,
            "max_quantity": variant.stock,
        }

    return {
        "status": STOCK_STATUS_AVAILABLE,
        "label": "",
        "color_class": "text-slate-500",
        "can_add": True,
        "max_quantity": variant.stock,
    }


def get_display_title(product, variant):
    """Computed card title: Brand + product name + package size."""
    if not variant:
        return product.name
    unit = variant.unit_label
    weight_text = format_weight(variant.weight, unit)
    return f"{product.company.name} {product.name} {weight_text}"


def annotate_purchase_count(queryset):
    """Attach favourite ``score`` and ``purchase_count`` (0 when missing)."""
    return queryset.annotate(
        score=Coalesce(F("favourite__score"), Value(0)),
        purchase_count=Coalesce(F("favourite__purchase_count"), Value(0)),
    )


def get_catalog_queryset():
    """Active products that still have a size the shop can sell."""
    return annotate_purchase_count(
        Product.objects.filter(is_active=True)
        .filter(variants__availability__in=SHOP_VISIBLE_AVAILABILITIES)
        .distinct()
        .select_related("company", "animal_type", "category")
        .prefetch_related(
            Prefetch("variants", queryset=shop_visible_variant_queryset())
        )
        .annotate(variant_count=Count("variants"))
    )


def parse_sort(raw_value):
    if not raw_value:
        return SORT_DEFAULT
    key = str(raw_value).strip().lower()
    valid = {choice[0] for choice in SORT_OPTIONS}
    return key if key in valid else SORT_DEFAULT


def _annotate_default_variant_sort_fields(queryset):
    """Sort keys from the largest package variant (same as catalog cards)."""
    default_variant = (
        ProductVariant.objects.filter(
            product=OuterRef("pk"),
            availability__in=SHOP_VISIBLE_AVAILABILITIES,
        )
        .annotate(
            unit_price_calc=ExpressionWrapper(
                F("price") / F("weight"),
                output_field=DecimalField(max_digits=12, decimal_places=4),
            )
        )
        .order_by("-weight")
    )
    return queryset.annotate(
        sort_price=Subquery(default_variant.values("price")[:1]),
        sort_stock=Subquery(default_variant.values("stock")[:1]),
        sort_unit_price=Subquery(default_variant.values("unit_price_calc")[:1]),
    )


CATALOG_MIX_SESSION_KEY = "catalog_mix_seed"


def catalog_mix_seed(request):
    """Stable per-visit seed so pagination does not reshuffle mid-browse."""
    session = getattr(request, "session", None)
    if session is None:
        return 0
    seed = session.get(CATALOG_MIX_SESSION_KEY)
    if not seed:
        seed = secrets.randbelow(1_000_000_000) + 1
        session[CATALOG_MIX_SESSION_KEY] = seed
    return int(seed)


def popularity_mix_list(products, *, seed=0, group_by_company=False):
    """
    Shuffle products so the grid mixes, while higher favourite score ranks
    earlier more often (weighted random: mix = random * (1 + score)).
    """
    scored = []
    rng = random.Random(seed)
    # Stable input order so the same seed always maps to the same scores.
    for product in sorted(products, key=lambda item: item.pk):
        weight = getattr(product, "score", None)
        if weight is None:
            weight = getattr(product, "purchase_count", 0) or 0
        score = rng.random() * (1 + (weight or 0))
        company_key = ""
        if group_by_company:
            company = getattr(product, "company", None)
            company_key = company.name.lower() if company else ""
        scored.append((company_key, -score, product.pk, product))
    scored.sort(key=lambda row: (row[0], row[1], row[2]))
    return [row[3] for row in scored]


def apply_catalog_sort(queryset, sort_key, *, browse_mode=False, mix_seed=0):
    if sort_key == SORT_DEFAULT:
        return popularity_mix_list(
            queryset,
            seed=mix_seed,
            group_by_company=browse_mode,
        )

    queryset = _annotate_default_variant_sort_fields(queryset)
    tie_breaker = ("-score", "-purchase_count", "company__name", "name")

    sort_map = {
        SORT_PRICE_ASC: ("sort_price", *tie_breaker),
        SORT_PRICE_DESC: ("-sort_price", *tie_breaker),
        SORT_STOCK_DESC: ("-sort_stock", *tie_breaker),
        SORT_UNIT_PRICE_ASC: ("sort_unit_price", *tie_breaker),
        SORT_UNIT_PRICE_DESC: ("-sort_unit_price", *tie_breaker),
    }
    return queryset.order_by(*sort_map.get(sort_key, tie_breaker))


def parse_filter_values(request, param_name):
    """Read repeated ?brand=X&brand=Y (or legacy single ?brand=) GET values."""
    values = list(request.GET.getlist(param_name))
    if not values and param_name == "brand":
        single = request.GET.get("brand", "").strip()
        if single:
            values = [single]
    result = []
    for value in values:
        for part in str(value).split(","):
            cleaned = part.strip()
            if cleaned:
                result.append(cleaned)
    return result


def _default_variant_subquery():
    return (
        ProductVariant.objects.filter(
            product=OuterRef("pk"),
            availability__in=SHOP_VISIBLE_AVAILABILITIES,
        ).order_by("-weight")
    )


def _annotate_default_variant_fields(queryset):
    default_variant = _default_variant_subquery()
    return queryset.annotate(
        default_availability=Subquery(default_variant.values("availability")[:1]),
        default_stock=Subquery(default_variant.values("stock")[:1]),
    )


def apply_catalog_filters(
    queryset,
    *,
    animal_slugs=None,
    brand_codes=None,
    category_slugs=None,
    availability_keys=None,
    price_min=None,
    price_max=None,
    price_active=False,
):
    """AND across groups, OR within the same group (any checked box)."""
    animal_slugs = animal_slugs or []
    brand_codes = brand_codes or []
    category_slugs = category_slugs or []
    availability_keys = availability_keys or []

    valid_animals = [slug for slug in animal_slugs if slug in ANIMAL_FILTER_KEYS]
    if valid_animals:
        queryset = queryset.filter(animal_type__slug__in=valid_animals)

    if brand_codes:
        valid_codes = list(
            Company.objects.filter(code__in=brand_codes).values_list("code", flat=True)
        )
        if valid_codes:
            queryset = queryset.filter(company__code__in=valid_codes)

    if category_slugs:
        valid_slugs = list(
            Category.objects.filter(slug__in=category_slugs).values_list("slug", flat=True)
        )
        if valid_slugs:
            queryset = queryset.filter(category__slug__in=valid_slugs)

    valid_availability = [key for key in availability_keys if key in AVAILABILITY_FILTER_KEYS]
    if valid_availability:
        queryset = _annotate_default_variant_fields(queryset)
        availability_q = Q()
        if AVAILABILITY_FILTER_IN_STORE in valid_availability:
            availability_q |= Q(
                default_availability=ProductVariant.AVAILABILITY_AVAILABLE_NOW,
                default_stock__gt=0,
            )
        if AVAILABILITY_FILTER_ON_ORDER in valid_availability:
            availability_q |= Q(default_availability=ProductVariant.AVAILABILITY_ON_ORDER)
        queryset = queryset.filter(availability_q)

    if price_active and price_min is not None and price_max is not None:
        queryset = _annotate_default_variant_sort_fields(queryset)
        queryset = queryset.filter(
            sort_price__gte=price_min,
            sort_price__lte=price_max,
        )

    return queryset


def parse_price_param(raw):
    if raw is None or str(raw).strip() == "":
        return None
    try:
        text = str(raw).strip().replace(",", ".")
        return Decimal(text).quantize(Decimal("0.01"))
    except (TypeError, ValueError, ArithmeticError):
        return None


def get_catalog_price_bounds(queryset):
    """Min/max default-variant price for the current catalog scope."""
    annotated = _annotate_default_variant_sort_fields(queryset)
    agg = annotated.aggregate(min_price=Min("sort_price"), max_price=Max("sort_price"))
    min_price = agg["min_price"] if agg["min_price"] is not None else Decimal("0")
    max_price = agg["max_price"] if agg["max_price"] is not None else Decimal("0")
    if max_price < min_price:
        min_price, max_price = Decimal("0"), Decimal("0")
    return {"min": min_price, "max": max_price}


def resolve_price_filter(request, bounds):
    """Selected price range from GET, clamped to catalog bounds."""
    bound_min = bounds["min"]
    bound_max = bounds["max"]
    selected_min = parse_price_param(request.GET.get("price_min"))
    selected_max = parse_price_param(request.GET.get("price_max"))

    if selected_min is None:
        selected_min = bound_min
    if selected_max is None:
        selected_max = bound_max

    if bound_max >= bound_min:
        selected_min = max(bound_min, min(selected_min, bound_max))
        selected_max = max(bound_min, min(selected_max, bound_max))
    if selected_min > selected_max:
        selected_min, selected_max = selected_max, selected_min

    active = bool(bound_max > bound_min) and (
        selected_min > bound_min or selected_max < bound_max
    )

    return {
        "bound_min": bound_min,
        "bound_max": bound_max,
        "selected_min": selected_min,
        "selected_max": selected_max,
        "active": active,
        "min_display": format_decimal_greek(selected_min),
        "max_display": format_decimal_greek(selected_max),
        "bound_min_num": float(bound_min),
        "bound_max_num": float(bound_max),
        "selected_min_num": float(selected_min),
        "selected_max_num": float(selected_max),
        "has_range": bound_max > bound_min,
    }


def resolve_animal_slugs(request):
    """Animal filter from ?animal=dog|cat."""
    slugs = parse_filter_values(request, "animal")
    return [slug for slug in slugs if slug in ANIMAL_FILTER_KEYS]


def _catalog_query_items(
    request,
    *,
    page=None,
    per_page=...,
    sort=...,
    animal_slugs=...,
    brand_codes=...,
    category_slugs=...,
    availability_keys=...,
    price_min=...,
    price_max=...,
    price_active=...,
):
    items = []

    if animal_slugs is ...:
        animal_slugs = parse_filter_values(request, "animal")
    for slug in animal_slugs:
        if slug in ANIMAL_FILTER_KEYS:
            items.append(("animal", slug))

    if brand_codes is ...:
        brand_codes = parse_filter_values(request, "brand")
    for code in brand_codes:
        items.append(("brand", code))

    if category_slugs is ...:
        category_slugs = parse_filter_values(request, "category")
    for slug in category_slugs:
        items.append(("category", slug))

    if availability_keys is ...:
        availability_keys = parse_filter_values(request, "availability")
    for key in availability_keys:
        if key in AVAILABILITY_FILTER_KEYS:
            items.append(("availability", key))

    if price_active is ...:
        price_min_raw = request.GET.get("price_min")
        price_max_raw = request.GET.get("price_max")
        if price_min_raw:
            items.append(("price_min", price_min_raw))
        if price_max_raw:
            items.append(("price_max", price_max_raw))
    elif price_active and price_min is not None and price_max is not None:
        items.append(("price_min", str(price_min)))
        items.append(("price_max", str(price_max)))

    if per_page is ...:
        resolved_per_page = parse_per_page(request.GET.get("per_page"))
    else:
        resolved_per_page = _resolve_per_page_param(per_page)

    if resolved_per_page is None:
        items.append(("per_page", PER_PAGE_ALL))
    elif resolved_per_page != DEFAULT_PER_PAGE:
        items.append(("per_page", str(resolved_per_page)))

    if sort is ...:
        resolved_sort = parse_sort(request.GET.get("sort"))
    else:
        resolved_sort = parse_sort(sort)
    if resolved_sort != SORT_DEFAULT:
        items.append(("sort", resolved_sort))

    effective_page = parse_page_number(page if page is not None else request.GET.get("page", 1))
    if effective_page > 1:
        items.append(("page", str(effective_page)))

    return items


def build_catalog_card(product, *, cart_qty=0, is_wishlisted=False):
    """Plain dict consumed by product_card.html."""
    variant = get_default_variant(product)
    if not variant:
        return None

    unit_price = variant.unit_price if shows_unit_price(product) else None
    count = product.variant_count
    if count == 1:
        sizes_label = "1 ΜΕΓΕΘΟΣ"
    else:
        sizes_label = f"{count} ΜΕΓΕΘΗ"

    stock_display = get_stock_display(variant)
    category_slug = product.category.slug if product.category_id else ""

    return {
        "product_id": product.id,
        "variant_id": variant.id,
        "sku": variant.sku or "",
        "title": get_display_title(product, variant),
        "sizes_label": sizes_label,
        "variant_count": count,
        "price": variant.selling_price,
        "price_display": format_decimal_greek(variant.selling_price),
        "unit_price_display": format_decimal_greek(unit_price) if unit_price else "",
        "unit_label": variant.unit_label,
        "availability": variant.availability,
        "stock": variant.stock,
        "stock_status": stock_display["status"],
        "availability_label": stock_display["label"],
        "availability_color_class": stock_display["color_class"],
        "can_add": stock_display["can_add"],
        "max_quantity": stock_display["max_quantity"],
        "is_on_order": stock_display["status"] == STOCK_STATUS_ON_ORDER,
        "button_label": stock_display.get("button_label", "Αγορά"),
        "image_url": product.image.url if product.image else None,
        "category_slug": category_slug,
        "image_display_scale": get_product_image_display_scale(product),
        "cart_qty": cart_qty,
        "is_wishlisted": is_wishlisted,
        "product_slug": product.slug,
        "detail_url": reverse("products:detail", kwargs={"slug": product.slug}),
    }


def get_product_detail_queryset():
    return (
        Product.objects.filter(is_active=True)
        .filter(variants__availability__in=SHOP_VISIBLE_AVAILABILITIES)
        .distinct()
        .select_related("company", "animal_type", "category")
        .prefetch_related(
            Prefetch("variants", queryset=shop_visible_variant_queryset())
        )
    )


def build_variant_option(variant, *, selected=False, cart_qty=0):
    """One package-size row for the product detail size picker."""
    stock_display = get_stock_display(variant)
    unit_price = variant.unit_price if shows_unit_price(variant.product) else None
    size_label = format_weight(variant.weight, variant.unit_label)
    return {
        "id": variant.id,
        "weight": variant.weight,
        "weight_display": size_label,
        "unit_label": variant.unit_label,
        "size_label": size_label,
        "sku": variant.sku or "",
        "price": variant.selling_price,
        "price_display": format_decimal_greek(variant.selling_price),
        "unit_price_display": format_decimal_greek(unit_price) if unit_price else "",
        "availability_label": stock_display["label"],
        "availability_color_class": stock_display["color_class"],
        "can_add": stock_display["can_add"],
        "max_quantity": stock_display["max_quantity"],
        "is_on_order": stock_display["status"] == STOCK_STATUS_ON_ORDER,
        "button_label": stock_display.get("button_label", "Αγορά"),
        "selected": selected,
        "cart_qty": cart_qty,
    }


def get_related_products_for_detail(product, *, limit=24):
    """
    Related products for the detail page (horizontal row).

    Priority (κατάβαση): same animal + category + brand, then same animal +
    category, then same animal + brand. Same animal only does not qualify.
    """
    candidates = []
    queryset = (
        get_catalog_queryset()
        .filter(animal_type_id=product.animal_type_id)
        .exclude(pk=product.pk)
    )

    for candidate in queryset:
        same_category = candidate.category_id == product.category_id
        same_company = candidate.company_id == product.company_id

        if same_category and same_company:
            tier = 0
        elif same_category:
            tier = 1
        elif same_company:
            tier = 2
        else:
            continue

        candidates.append(
            (tier, -getattr(candidate, "score", 0), candidate.company.name.lower(), candidate.name.lower(), candidate)
        )

    candidates.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    return [row[4] for row in candidates[:limit]]


def build_product_filter_links(product):
    """Pill links below the buy box — each opens catalog with one filter applied."""
    animal_slug = product.animal_type.slug
    category_slug = product.category.slug
    return [
        {
            "type": "animal",
            "label": ANIMAL_SLUG_LABELS.get(animal_slug, product.animal_type.name),
            "url": f"{reverse('products:all')}?{urlencode([('animal', animal_slug)])}",
        },
        {
            "type": "category",
            "label": CATEGORY_LABELS.get(product.category.name, product.category.name),
            "url": f"{reverse('products:all')}?{urlencode([('category', category_slug)])}",
        },
        {
            "type": "brand",
            "label": product.company.name,
            "url": f"{reverse('products:all')}?{urlencode([('brand', product.company.code)])}",
        },
    ]


def build_product_detail_context(request, product, *, selected_variant_id=None):
    """Template context for the product detail page (petcity-style)."""
    variants = [
        variant
        for variant in product.variants.all()
        if variant.availability in SHOP_VISIBLE_AVAILABILITIES
    ]
    if not variants:
        return None

    selected = None
    if selected_variant_id:
        selected = next((v for v in variants if v.id == selected_variant_id), None)
    if selected is None:
        selected = get_default_variant(product) or variants[0]

    cart_quantities = {}
    if hasattr(request, "session"):
        from cart.cart import get_cart

        cart_quantities = {
            item.product_variant.pk: item.quantity for item in get_cart(request).items
        }

    wishlisted_ids = set()
    if hasattr(request, "session"):
        from wishlist.wishlist import get_wishlist

        wishlisted_ids = get_wishlist(request).product_ids

    variant_options = [
        build_variant_option(
            v,
            selected=(v.id == selected.id),
            cart_qty=cart_quantities.get(v.id, 0),
        )
        for v in variants
    ]
    selected_option = next(o for o in variant_options if o["selected"])

    animal_label = ANIMAL_SLUG_LABELS.get(product.animal_type.slug, product.animal_type.name)
    category_label = CATEGORY_LABELS.get(product.category.name, product.category.name)

    related_products = get_related_products_for_detail(product)
    related_cards = build_catalog_cards(
        related_products,
        cart_quantities=cart_quantities,
        wishlisted_ids=wishlisted_ids,
    )

    from products.favourites import build_favourites_browse_cards

    favourite_cards = build_favourites_browse_cards(
        request,
        limit=12,
        exclude_product_ids=[product.pk],
    )

    company_url = None
    if product.company_id:
        from products.company_pages import has_brand_page

        if has_brand_page(product.company.code):
            company_url = reverse("products:company", kwargs={"company_code": product.company.code})

    return {
        "product": product,
        "page_title": get_display_title(product, selected),
        "company_name": product.company.name,
        "company_url": company_url,
        "filter_links": build_product_filter_links(product),
        "animal_label": animal_label,
        "category_label": category_label,
        "image_url": product.image.url if product.image else None,
        "image_display_scale": get_product_image_display_scale(product),
        "description": product.description.strip() if product.description else "",
        "components": product.components.strip() if product.components else "",
        "bundle_contents": product.bundle_contents.strip() if product.bundle_contents else "",
        "variant_options": variant_options,
        "selected_variant": selected_option,
        "is_wishlisted": product.id in wishlisted_ids,
        "related_cards": related_cards,
        "favourite_cards": favourite_cards,
        "user_is_authenticated": request.user.is_authenticated,
    }


def build_catalog_cards(products, cart_quantities=None, wishlisted_ids=None):
    """Build card dicts for a queryset/list of products."""
    cart_quantities = cart_quantities or {}
    wishlisted_ids = wishlisted_ids or set()
    cards = []
    for product in products:
        variant = get_default_variant(product)
        if not variant:
            continue
        card = build_catalog_card(
            product,
            cart_qty=cart_quantities.get(variant.id, 0),
            is_wishlisted=product.id in wishlisted_ids,
        )
        if card:
            cards.append(card)
    return cards


def parse_per_page(raw_value):
    """Return an int per-page size, or None for «show all»."""
    if raw_value is None:
        return DEFAULT_PER_PAGE
    text = str(raw_value).strip().lower()
    if text in ("all", "0"):
        return None
    if not text:
        return DEFAULT_PER_PAGE
    try:
        value = int(text)
    except (TypeError, ValueError):
        return DEFAULT_PER_PAGE
    if value in PER_PAGE_OPTIONS:
        return value
    return DEFAULT_PER_PAGE


def parse_page_number(raw_value):
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError):
        return 1


def _resolve_per_page_param(per_page):
    """Normalise explicit per_page argument for URL building."""
    if per_page == PER_PAGE_ALL:
        return None
    if isinstance(per_page, int):
        return per_page
    return parse_per_page(per_page)


def catalog_query_string(
    request,
    *,
    page=None,
    per_page=...,
    sort=...,
    animal_slugs=...,
    brand_codes=...,
    category_slugs=...,
    availability_keys=...,
    price_min=...,
    price_max=...,
    price_active=...,
):
    """Build query string preserving filters, sort, and pagination."""
    items = _catalog_query_items(
        request,
        page=page,
        per_page=per_page,
        sort=sort,
        animal_slugs=animal_slugs,
        brand_codes=brand_codes,
        category_slugs=category_slugs,
        availability_keys=availability_keys,
        price_min=price_min,
        price_max=price_max,
        price_active=price_active,
    )
    encoded = urlencode(items)
    return f"?{encoded}" if encoded else ""


def catalog_page_url(
    request,
    *,
    page=None,
    per_page=...,
    sort=...,
    animal_slugs=...,
    brand_codes=...,
    category_slugs=...,
    availability_keys=...,
    price_min=...,
    price_max=...,
    price_active=...,
):
    """Absolute path + query string for catalog links."""
    return request.path + catalog_query_string(
        request,
        page=page,
        per_page=per_page,
        sort=sort,
        animal_slugs=animal_slugs,
        brand_codes=brand_codes,
        category_slugs=category_slugs,
        availability_keys=availability_keys,
        price_min=price_min,
        price_max=price_max,
        price_active=price_active,
    )


def build_catalog_filter_context(
    request,
    scope_queryset,
    *,
    animal_slugs,
    brand_codes,
    category_slugs,
    availability_keys,
    price_filter,
):
    """Sidebar checkbox groups; animal filter always first."""
    company_qs = (
        Company.objects.filter(products__in=scope_queryset)
        .distinct()
        .order_by("name")
    )
    category_qs = (
        Category.objects.filter(products__in=scope_queryset)
        .distinct()
        .order_by("name")
    )

    selected_animals = set(animal_slugs)
    selected_brands = set(brand_codes)
    selected_categories = set(category_slugs)
    selected_availability = set(availability_keys)

    animal_options = [
        {
            "value": slug,
            "label": label,
            "checked": slug in selected_animals,
        }
        for slug, label in ANIMAL_FILTER_OPTIONS
    ]
    brand_options = [
        {
            "value": company.code,
            "label": company.name,
            "checked": company.code in selected_brands,
        }
        for company in company_qs
    ]
    category_options = [
        {
            "value": category.slug,
            "label": CATEGORY_LABELS.get(category.name, category.name),
            "checked": category.slug in selected_categories,
        }
        for category in category_qs
    ]
    availability_options = [
        {
            "value": key,
            "label": label,
            "checked": key in selected_availability,
        }
        for key, label in AVAILABILITY_FILTER_OPTIONS
    ]

    has_active_filters = bool(
        selected_animals
        or selected_brands
        or selected_categories
        or selected_availability
        or price_filter.get("active")
    )

    return {
        "filter_sections": [
            {"id": "animal", "title": "Σκύλος / Γάτα", "param": "animal", "options": animal_options},
            {"id": "brand", "title": "Μάρκα / Εταιρεία", "param": "brand", "options": brand_options},
            {"id": "category", "title": "Κατηγορία", "param": "category", "options": category_options},
            {
                "id": "availability",
                "title": "Διαθεσιμότητα",
                "param": "availability",
                "options": availability_options,
            },
        ],
        "price_filter": price_filter,
        "has_active_filters": has_active_filters,
        "selected_animal_slugs": animal_slugs,
        "selected_brand_codes": brand_codes,
        "selected_category_slugs": category_slugs,
        "selected_availability_keys": availability_keys,
    }


def build_animal_category_tiles(animal_slug):
    """Large category squares for dog/cat landing pages."""
    from django.urls import reverse

    tiles = []
    for slug in ANIMAL_CATEGORY_SLUGS.get(animal_slug, []):
        query = urlencode([("animal", animal_slug), ("category", slug)])
        tiles.append(
            {
                "slug": slug,
                "label": CATEGORY_SLUG_LABELS.get(slug, slug),
                "image": CATEGORY_TILE_IMAGES.get(slug),
                "url": f"{reverse('products:browse')}?{query}",
            }
        )
    return tiles


def build_animal_landing_page(animal_slug):
    """Full-bleed TROFES landing band with circular category hotspots."""
    spec = ANIMAL_LANDING[animal_slug]
    size = spec["size"]
    band_w, band_h = spec["band_px"]
    # width% is of the section width; top% is of the section height, so the
    # circle's vertical centre needs the image aspect taken into account.
    top = spec["cy"] - (size / 2) * (band_w / band_h)
    hotspots = []
    for slug, cx in zip(spec["categories"], spec["cx"]):
        query = urlencode([("animal", animal_slug), ("category", slug)])
        hotspots.append(
            {
                "slug": slug,
                "label": CATEGORY_SLUG_LABELS.get(slug, slug),
                "url": f"{reverse('products:browse')}?{query}",
                "left": round(cx - size / 2, 2),
                "top": round(top, 2),
                "size": size,
            }
        )
    return {
        "page_title": ANIMAL_SLUG_LABELS.get(animal_slug, ""),
        "animal_slug": animal_slug,
        "landing_band": spec["band"],
        "landing_band_w": spec["band_px"][0],
        "landing_band_h": spec["band_px"][1],
        "landing_hotspots": hotspots,
    }


def chunk_animal_category_rows(tiles, columns=3):
    """
    Group tiles into rows of ``columns``.

    Incomplete last rows are laid out symmetrically:
    1 tile → center column, 2 tiles → left + right columns.
    """
    rows = []
    for start in range(0, len(tiles), columns):
        row_tiles = tiles[start : start + columns]
        count = len(row_tiles)
        placed = []
        for index, tile in enumerate(row_tiles):
            if count == 1:
                col_class = "sm:col-start-2"
            elif count == 2:
                col_class = "sm:col-start-1" if index == 0 else "sm:col-start-3"
            else:
                col_class = ""
            placed.append({**tile, "col_class": col_class})
        rows.append(placed)
    return rows


# SEL_oles etairies.pdf — 2×4 ovals, PDF order.
BRAND_LIST_ORDER = ("C4P", "COR", "PRF", "OWN", "PUR", "CAR", "WLD", "EVC")
BRAND_LANDING_BAND = "images/brand-landing/brands-band.png"
BRAND_LANDING_BAND_PX = (4000, 1435)
BRAND_LANDING_HOTSPOTS = (
    ("C4P", 26.80, 38.19, 10.85, 17.28),
    ("COR", 40.15, 38.19, 10.85, 17.28),
    ("PRF", 53.50, 38.19, 10.85, 17.28),
    ("OWN", 66.88, 38.19, 10.85, 17.28),
    ("PUR", 26.80, 64.67, 10.85, 17.28),
    ("CAR", 40.15, 64.67, 10.85, 17.28),
    ("WLD", 53.50, 64.67, 10.85, 17.28),
    ("EVC", 66.88, 64.67, 10.85, 17.28),
)


def _company_catalog_url(company):
    from products.company_pages import has_brand_page

    if has_brand_page(company.code):
        return reverse("products:company", args=[company.code])
    return f"{reverse('products:all')}?{urlencode([('brand', company.code)])}"


def build_homepage_brand_list():
    """Homepage about-us brand row: logo + name pill, PDF order."""
    by_code = {company.code.upper(): company for company in Company.objects.public()}
    brands = []
    for code in BRAND_LIST_ORDER:
        company = by_code.get(code)
        if not company or not company.logo:
            continue
        brands.append(
            {
                "code": code,
                "label": company.name,
                "url": _company_catalog_url(company),
                "logo_url": company.logo.url,
            }
        )
    return brands


def build_brand_landing_page():
    """Full-bleed brands band from SEL_oles etairies, with oval hotspots."""
    by_code = {company.code.upper(): company for company in Company.objects.public()}
    hotspots = []
    for code, left, top, width, height in BRAND_LANDING_HOTSPOTS:
        company = by_code.get(code)
        if not company:
            continue
        hotspots.append(
            {
                "code": code,
                "label": company.name,
                "url": _company_catalog_url(company),
                "left": left,
                "top": top,
                "width": width,
                "height": height,
            }
        )
    return {
        "page_title": "Brands",
        "landing_band": BRAND_LANDING_BAND,
        "landing_band_w": BRAND_LANDING_BAND_PX[0],
        "landing_band_h": BRAND_LANDING_BAND_PX[1],
        "landing_hotspots": hotspots,
    }


def build_brand_tiles():
    """Large brand squares for /products/brands/ landing page."""
    tiles = []
    for company in Company.objects.public().order_by("name"):
        tile = {
            "slug": company.code.lower(),
            "label": company.name,
            "url": _company_catalog_url(company),
        }
        if company.logo:
            tile["image_url"] = company.logo.url
        else:
            tile["image"] = "images/companies/car_placeholder.png"
        tiles.append(tile)
    return tiles


def get_browse_page_title(animal_slug, category_slug):
    animal = ANIMAL_SLUG_LABELS.get(animal_slug, animal_slug)
    category = CATEGORY_SLUG_LABELS.get(category_slug, category_slug)
    return f"{animal} — {category}"


# Brand logos range from a square badge (Wild Side) to a 6.5:1 banner (Puro
# Instinto). One shared CSS height therefore renders the square ones as tiny
# circles next to the wide wordmarks, so each logo is scaled to cover the same
# artwork area instead. The target is calibrated on CLUB4PAWS and CARNIS.
BROWSE_LOGO_ARTWORK_AREA_PX = 27000
BROWSE_LOGO_FALLBACK_HEIGHT_REM = 7.5
_ROOT_FONT_SIZE_PX = 16


@lru_cache(maxsize=64)
def _browse_logo_height_rem(path, _mtime):
    """Cached per file; _mtime busts the cache when a logo is replaced."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(path) as image:
            file_height = image.height
            # Opaque bounds only: Carnis ships a third of its canvas as padding.
            artwork = image.convert("RGBA").getbbox()
    except (OSError, UnidentifiedImageError):
        return BROWSE_LOGO_FALLBACK_HEIGHT_REM
    if not artwork:
        return BROWSE_LOGO_FALLBACK_HEIGHT_REM

    area = (artwork[2] - artwork[0]) * (artwork[3] - artwork[1])
    if area <= 0:
        return BROWSE_LOGO_FALLBACK_HEIGHT_REM
    scale = math.sqrt(BROWSE_LOGO_ARTWORK_AREA_PX / area)
    return round(file_height * scale / _ROOT_FONT_SIZE_PX, 2)


def browse_logo_height_rem(company):
    """Rendered height in rem that equalises this logo against the others."""
    if not company.logo:
        return BROWSE_LOGO_FALLBACK_HEIGHT_REM
    try:
        path = company.logo.path
        mtime = os.path.getmtime(path)
    except (NotImplementedError, ValueError, OSError):
        return BROWSE_LOGO_FALLBACK_HEIGHT_REM
    return _browse_logo_height_rem(path, mtime)


def build_browse_company_sections(products, *, cart_quantities=None, wishlisted_ids=None):
    """Group browse products by company for hero-brands-style rows."""
    cart_quantities = cart_quantities or {}
    wishlisted_ids = wishlisted_ids or set()

    company_order = []
    sections_by_id = {}

    for product in products:
        company = product.company
        if company.id not in sections_by_id:
            sections_by_id[company.id] = {
                "company": {
                    "id": company.id,
                    "name": company.name,
                    "code": company.code,
                    "url": _company_catalog_url(company),
                    "logo_url": company.logo.url if company.logo else None,
                    "logo_height_rem": browse_logo_height_rem(company),
                },
                "products": [],
            }
            company_order.append(company.id)

        variant = get_default_variant(product)
        card = build_catalog_card(
            product,
            cart_qty=cart_quantities.get(variant.id, 0) if variant else 0,
            is_wishlisted=product.id in wishlisted_ids,
        )
        if card:
            sections_by_id[company.id]["products"].append(card)

    return [sections_by_id[company_id] for company_id in company_order if sections_by_id[company_id]["products"]]


def build_catalog_sort_context(request, current_sort):
    """Dropdown options for the toolbar sort control."""
    return {
        "sort": current_sort,
        "sort_choices": [
            {
                "value": key,
                "label": label,
                "url": catalog_page_url(request, page=1, sort=key),
                "active": key == current_sort,
            }
            for key, label in SORT_OPTIONS
        ],
    }


def paginate_catalog_queryset(queryset, per_page, page_number):
    """Slice queryset for the requested page; None per_page returns everything."""
    if per_page is None:
        return {
            "page_products": queryset,
            "page_obj": None,
            "is_paginated": False,
        }

    paginator = Paginator(queryset, per_page)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)

    return {
        "page_products": page_obj.object_list,
        "page_obj": page_obj,
        "is_paginated": paginator.num_pages > 1,
    }


def build_catalog_pagination_context(request, page_obj, *, per_page):
    """Template-ready pagination URLs (no custom templatetags)."""
    per_page_display = PER_PAGE_ALL if per_page is None else str(per_page)
    per_page_choices = []
    for size in PER_PAGE_OPTIONS:
        per_page_choices.append(
            {
                "label": str(size),
                "url": catalog_page_url(request, page=1, per_page=size),
                "active": per_page == size,
            }
        )
    per_page_choices.append(
        {
            "label": "Όλα",
            "url": catalog_page_url(request, page=1, per_page=PER_PAGE_ALL),
            "active": per_page is None,
        }
    )

    if page_obj is None:
        return {
            "per_page_display": per_page_display,
            "per_page_choices": per_page_choices,
            "is_paginated": False,
            "page_obj": None,
            "page_links": [],
            "prev_url": None,
            "next_url": None,
        }

    page_links = [
        {
            "num": num,
            "url": catalog_page_url(request, page=num, per_page=per_page),
            "active": num == page_obj.number,
        }
        for num in page_obj.paginator.page_range
    ]

    return {
        "per_page_display": per_page_display,
        "per_page_choices": per_page_choices,
        "is_paginated": page_obj.paginator.num_pages > 1,
        "page_obj": page_obj,
        "page_links": page_links,
        "prev_url": (
            catalog_page_url(request, page=page_obj.previous_page_number(), per_page=per_page)
            if page_obj.has_previous()
            else None
        ),
        "next_url": (
            catalog_page_url(request, page=page_obj.next_page_number(), per_page=per_page)
            if page_obj.has_next()
            else None
        ),
    }
