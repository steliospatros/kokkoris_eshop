from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from cart.cart import get_cart
from products.catalog import build_catalog_cards, get_catalog_queryset
from products.models import Company, Product
from wishlist.models import WishlistItem

# How many matches the search dropdown shows at once - kept small since this
# is a live-as-you-type suggestion list, not a full search results page.
SEARCH_SUGGESTION_LIMIT = 8

# Placeholder catalog UI data — wired to real filters in a later pass.
DOG_CATALOG_TABS = [
    {"label": "Τροφές Σκύλου", "active": True},
    {"label": "Λιχουδιές", "active": False},
    {"label": "Φροντίδα & Καλλωπισμός", "active": False},
    {"label": "Υγιεινή", "active": False},
    {"label": "Αξεσουάρ", "active": False},
]
CAT_CATALOG_TABS = [
    {"label": "Τροφές Γάτας", "active": True},
    {"label": "Λιχουδιές", "active": False},
    {"label": "Άμμος", "active": False},
    {"label": "Φροντίδα", "active": False},
    {"label": "Αξεσουάρ", "active": False},
]
ALL_CATALOG_TABS = [
    {"label": "Όλα", "active": True},
    {"label": "Σκύλος", "active": False},
    {"label": "Γάτα", "active": False},
    {"label": "Brands", "active": False},
]
DEFAULT_FILTER_SECTIONS = [
    {"title": "Μάρκα", "items": ["CLUB4PAWS", "OWNAT", "PROFINE", "Wild Side"]},
    {"title": "Κατηγορία", "items": ["Ξηρά τροφή", "Κονσέρβες", "Φακελάκια", "Άμμος"]},
    {"title": "Διαθεσιμότητα", "items": ["Άμεσα διαθέσιμο", "Κατόπιν παραγγελίας"]},
]


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


def _catalog_page(request, page_title, *, animal_slug=None, company_code=None):
    products = get_catalog_queryset()
    if animal_slug:
        products = products.filter(animal_type__slug=animal_slug)
    if company_code:
        products = products.filter(company__code__iexact=company_code)

    cards = build_catalog_cards(
        products,
        cart_quantities=_cart_quantities(request),
        wishlisted_ids=_wishlisted_ids(request),
    )

    if animal_slug == "dog":
        catalog_tabs = DOG_CATALOG_TABS
    elif animal_slug == "cat":
        catalog_tabs = CAT_CATALOG_TABS
    else:
        catalog_tabs = ALL_CATALOG_TABS

    return {
        "page_title": page_title,
        "product_cards": cards,
        "product_count": len(cards),
        "user_is_authenticated": request.user.is_authenticated,
        "catalog_tabs": catalog_tabs,
        "filter_sections": DEFAULT_FILTER_SECTIONS,
    }


@ensure_csrf_cookie
def catalog_dogs(request):
    return render(
        request,
        "products/catalog.html",
        _catalog_page(request, "Σκύλος", animal_slug="dog"),
    )


@ensure_csrf_cookie
def catalog_cats(request):
    return render(
        request,
        "products/catalog.html",
        _catalog_page(request, "Γάτα", animal_slug="cat"),
    )


@ensure_csrf_cookie
def catalog_all(request):
    company_code = request.GET.get("brand", "").strip()
    page_title = "Όλα τα προϊόντα"
    if company_code:
        company = Company.objects.filter(code__iexact=company_code).first()
        if company:
            page_title = company.name
    return render(
        request,
        "products/catalog.html",
        _catalog_page(request, page_title, company_code=company_code or None),
    )


def catalog_brands(request):
    companies = (
        Company.objects.filter(products__is_active=True)
        .distinct()
        .order_by("name")
    )
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
