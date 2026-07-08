from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from cart.cart import get_cart
from products.catalog import (
    apply_catalog_filters,
    apply_catalog_sort,
    build_animal_category_tiles,
    build_browse_company_sections,
    build_catalog_cards,
    build_catalog_filter_context,
    build_catalog_pagination_context,
    build_catalog_sort_context,
    get_browse_page_title,
    get_catalog_price_bounds,
    get_catalog_queryset,
    paginate_catalog_queryset,
    parse_filter_values,
    parse_page_number,
    parse_per_page,
    parse_sort,
    resolve_animal_slugs,
    resolve_price_filter,
    ANIMAL_SLUG_LABELS,
    PER_PAGE_ALL,
    DEFAULT_PER_PAGE,
    SORT_DEFAULT,
)
from products.company_pages import build_company_page_context, has_brand_page
from products.models import Company, Product
from wishlist.models import WishlistItem

# How many matches the search dropdown shows at once - kept small since this
# is a live-as-you-type suggestion list, not a full search results page.
SEARCH_SUGGESTION_LIMIT = 8


def _catalog_filter_hidden_fields(sort, per_page):
    hidden = []
    if sort != SORT_DEFAULT:
        hidden.append({"name": "sort", "value": sort})
    if per_page is None:
        hidden.append({"name": "per_page", "value": PER_PAGE_ALL})
    elif per_page != DEFAULT_PER_PAGE:
        hidden.append({"name": "per_page", "value": str(per_page)})
    return hidden


def home(request):
    """
    Homepage: full-bleed hero/about/brands/animals sections.
    The brand carousel lists every Company that has a logo uploaded.
    """
    companies = (
        Company.objects.exclude(logo="")
        .exclude(logo__isnull=True)
        .order_by("name")
    )

    return render(
        request,
        "home.html",
        {
            "companies": companies,
        },
    )


def _cart_quantities(request):
    cart = get_cart(request)
    return {item.product_variant.pk: item.quantity for item in cart.items}


def _wishlisted_ids(request):
    if not request.user.is_authenticated:
        return set()
    return set(
        WishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)
    )


def _catalog_page(request, page_title):
    base_queryset = get_catalog_queryset()
    animal_slugs = resolve_animal_slugs(request)

    scope_queryset = base_queryset
    if animal_slugs:
        scope_queryset = scope_queryset.filter(animal_type__slug__in=animal_slugs)

    brand_codes = parse_filter_values(request, "brand")
    category_slugs = parse_filter_values(request, "category")
    availability_keys = parse_filter_values(request, "availability")
    price_bounds = get_catalog_price_bounds(scope_queryset)
    price_filter = resolve_price_filter(request, price_bounds)

    products = apply_catalog_filters(
        base_queryset,
        animal_slugs=animal_slugs,
        brand_codes=brand_codes,
        category_slugs=category_slugs,
        availability_keys=availability_keys,
        price_min=price_filter["selected_min"],
        price_max=price_filter["selected_max"],
        price_active=price_filter["active"],
    )

    sort = parse_sort(request.GET.get("sort"))
    products = apply_catalog_sort(products, sort)

    total_count = products.count()
    per_page = parse_per_page(request.GET.get("per_page"))
    page_number = parse_page_number(request.GET.get("page"))
    pagination = paginate_catalog_queryset(products, per_page, page_number)

    cards = build_catalog_cards(
        pagination["page_products"],
        cart_quantities=_cart_quantities(request),
        wishlisted_ids=_wishlisted_ids(request),
    )

    filter_context = build_catalog_filter_context(
        request,
        scope_queryset,
        animal_slugs=animal_slugs,
        brand_codes=brand_codes,
        category_slugs=category_slugs,
        availability_keys=availability_keys,
        price_filter=price_filter,
    )

    return {
        "page_title": page_title,
        "product_cards": cards,
        "product_count": total_count,
        "user_is_authenticated": request.user.is_authenticated,
        "filter_hidden_fields": _catalog_filter_hidden_fields(sort, per_page),
        **filter_context,
        **build_catalog_sort_context(request, sort),
        **build_catalog_pagination_context(
            request,
            pagination["page_obj"],
            per_page=per_page,
        ),
    }


def _catalog_browse_page(request, animal_slug, category_slug):
    """Products grouped by company — hero-brands-style rows, no sidebar."""
    base_queryset = get_catalog_queryset()
    products = apply_catalog_filters(
        base_queryset,
        animal_slugs=[animal_slug],
        category_slugs=[category_slug],
    )

    sort = parse_sort(request.GET.get("sort"))
    products = apply_catalog_sort(products, sort)

    total_count = products.count()
    company_sections = build_browse_company_sections(
        products,
        cart_quantities=_cart_quantities(request),
        wishlisted_ids=_wishlisted_ids(request),
    )

    animal_landing_url = reverse(
        "products:dogs" if animal_slug == "dog" else "products:cats"
    )

    return {
        "page_title": get_browse_page_title(animal_slug, category_slug),
        "company_sections": company_sections,
        "product_count": total_count,
        "user_is_authenticated": request.user.is_authenticated,
        "browse_mode": True,
        "animal_slug": animal_slug,
        "category_slug": category_slug,
        "back_url": animal_landing_url,
        "back_label": ANIMAL_SLUG_LABELS.get(animal_slug, ""),
        **build_catalog_sort_context(request, sort),
    }


def _animal_categories_page(animal_slug):
    return {
        "page_title": ANIMAL_SLUG_LABELS.get(animal_slug, ""),
        "animal_slug": animal_slug,
        "category_tiles": build_animal_category_tiles(animal_slug),
    }


@ensure_csrf_cookie
def catalog_dogs(request):
    return render(
        request,
        "products/animal_categories.html",
        _animal_categories_page("dog"),
    )


@ensure_csrf_cookie
def catalog_cats(request):
    return render(
        request,
        "products/animal_categories.html",
        _animal_categories_page("cat"),
    )


@ensure_csrf_cookie
def catalog_browse(request):
    animal_slugs = resolve_animal_slugs(request)
    category_slugs = parse_filter_values(request, "category")
    if len(animal_slugs) != 1 or len(category_slugs) != 1:
        return redirect(reverse("products:all"))
    return render(
        request,
        "products/catalog_browse.html",
        _catalog_browse_page(request, animal_slugs[0], category_slugs[0]),
    )


@ensure_csrf_cookie
def catalog_all(request):
    brand_codes = parse_filter_values(request, "brand")
    animal_slugs = resolve_animal_slugs(request)
    page_title = "Όλα τα προϊόντα"
    if len(brand_codes) == 1:
        company = Company.objects.filter(code__iexact=brand_codes[0]).first()
        if company:
            page_title = company.name
    elif animal_slugs == ["dog"]:
        page_title = "Σκύλος"
    elif animal_slugs == ["cat"]:
        page_title = "Γάτα"
    return render(
        request,
        "products/catalog.html",
        _catalog_page(request, page_title),
    )


def _build_brand_page_product_cards(request, queryset):
    return build_catalog_cards(
        queryset,
        cart_quantities=_cart_quantities(request),
        wishlisted_ids=_wishlisted_ids(request),
    )


@ensure_csrf_cookie
def company_page(request, company_code):
    company = get_object_or_404(Company, code__iexact=company_code)
    context = build_company_page_context(company)
    if context is None:
        return redirect(reverse("products:all"))

    page_sections = context.get("page_sections")
    if page_sections:
        base_products = get_catalog_queryset().filter(company=company)
        sections = []
        for section in page_sections:
            section = dict(section)
            if section.get("type") == "products":
                products = base_products
                if section.get("animal_type"):
                    products = products.filter(animal_type__name=section["animal_type"])
                if section.get("category"):
                    products = products.filter(category__name=section["category"])
                section["product_cards"] = _build_brand_page_product_cards(
                    request,
                    products.order_by("name"),
                )
            sections.append(section)
        context["page_sections"] = sections
        context["user_is_authenticated"] = request.user.is_authenticated
    elif context.get("show_products_row"):
        products = get_catalog_queryset().filter(company=company).order_by("name")
        context["product_cards"] = _build_brand_page_product_cards(request, products)
        context["user_is_authenticated"] = request.user.is_authenticated

    return render(
        request,
        "products/company/brand_page.html",
        context,
    )


def catalog_brands(request):
    companies = Company.objects.order_by("name")
    return render(
        request,
        "products/brands.html",
        {
            "page_title": "Brands",
            "companies": companies,
        },
    )


def search_suggestions(request):
    """
    JSON endpoint backing the nav's live search dropdown.

    Matches on product name / company name / category name, case-insensitive.
    """
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})

    products = (
        Product.objects.filter(is_active=True)
        .filter(
            Q(name__icontains=query)
            | Q(company__name__icontains=query)
            | Q(category__name__icontains=query)
        )
        .select_related("company")
        .order_by("name")[:SEARCH_SUGGESTION_LIMIT]
    )

    results = [
        {
            "name": product.name,
            "company": product.company.name,
            "image_url": product.image.url if product.image else None,
        }
        for product in products
    ]
    return JsonResponse({"results": results})
