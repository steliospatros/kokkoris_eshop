"""Hierarchical breadcrumbs for inner pages (always start with Homepage)."""

from __future__ import annotations

from django.http import HttpRequest
from django.urls import reverse

from pages.content import INFO_PAGES

HOME_LABEL = "Αρχική σελίδα"

SKIP_URL_NAMES = frozenset(
    {
        "search_suggestions",
        "api_login",
        "api_signup",
        "api_password_reset",
        "toggle",
        "status",
        "subscribe",
        "profile",
        "home",
    }
)

ACCOUNT_LABELS = {
    "hub": "Ο λογαριασμός μου",
    "details": "Τα στοιχεία μου",
    "orders": "Ιστορικό παραγγελιών",
    "cart": "Το καλάθι μου",
}

CHECKOUT_LABELS = {
    "address": "Διεύθυνση παράδοσης",
    "delivery": "Τρόπος παράδοσης",
    "payment": "Τρόπος πληρωμής",
    "confirmation": "Επιβεβαίωση παραγγελίας",
}

PRODUCT_LABELS = {
    "dogs": "Σκύλος",
    "cats": "Γάτα",
    "all": "Όλα τα προϊόντα",
    "brands": "Μάρκες",
}

ADMINISTRATION_LABELS = {
    "hub": "Διαχείριση",
    "inventory": "Απόθεμα προϊόντων",
    "orders": "Διαχείριση παραγγελιών",
    "payments": "Ιστορικό πληρωμών",
}


def _crumb(label: str, url: str) -> dict[str, str]:
    return {"label": label, "url": url}


def _home_crumb() -> dict[str, str]:
    return _crumb(HOME_LABEL, reverse("home"))


def _page_label(url_name: str) -> str | None:
    slug_by_name = {
        "store": "store",
        "contact": "contact",
        "shipping": "shipping",
        "shipping_cost": "shipping-cost",
        "returns": "returns",
        "payment": "payment",
        "privacy": "privacy",
    }
    slug = slug_by_name.get(url_name)
    if not slug:
        return None
    return str(INFO_PAGES[slug]["title"])


def _checkout_trail(
    url_name: str,
    request: HttpRequest | None = None,
    **kwargs,
) -> list[dict[str, str]]:
    crumbs = [_home_crumb()]

    cart_label = ACCOUNT_LABELS["cart"]
    if request is not None:
        from cart.cart import get_cart

        count = get_cart(request).total_items
        if count > 0:
            cart_label = f"Το καλάθι μου ({count})"
    crumbs.append(_crumb(cart_label, reverse("accounts:cart")))

    steps = (
        ("address", CHECKOUT_LABELS["address"]),
        ("delivery", CHECKOUT_LABELS["delivery"]),
        ("payment", CHECKOUT_LABELS["payment"]),
        ("confirmation", CHECKOUT_LABELS["confirmation"]),
    )
    for step_name, step_label in steps:
        if step_name == "confirmation":
            order_id = kwargs.get("order_id")
            if order_id is None:
                continue
            url = reverse("checkout:confirmation", kwargs={"order_id": order_id})
        else:
            url = reverse(f"checkout:{step_name}")
        crumbs.append(_crumb(step_label, url))
        if step_name == url_name:
            break
    return crumbs


def _accounts_trail(url_name: str, request: HttpRequest | None = None) -> list[dict[str, str]]:
    if url_name == "cart":
        label = ACCOUNT_LABELS["cart"]
        if request is not None:
            from cart.cart import get_cart

            count = get_cart(request).total_items
            if count > 0:
                label = f"Το καλάθι μου ({count})"
        return [_home_crumb(), _crumb(label, reverse("accounts:cart"))]

    crumbs = [_home_crumb()]
    hub_label = ACCOUNT_LABELS["hub"]
    if url_name == "hub":
        crumbs.append(_crumb(hub_label, reverse("accounts:hub")))
        return crumbs

    crumbs.append(_crumb(hub_label, reverse("accounts:hub")))
    if url_name in ACCOUNT_LABELS:
        crumbs.append(_crumb(ACCOUNT_LABELS[url_name], reverse(f"accounts:{url_name}")))
    return crumbs


def _administration_trail(url_name: str) -> list[dict[str, str]]:
    crumbs = [
        _home_crumb(),
        _crumb(ACCOUNT_LABELS["hub"], reverse("accounts:hub")),
        _crumb(ADMINISTRATION_LABELS["hub"], reverse("administration:hub")),
    ]
    if url_name != "hub" and url_name in ADMINISTRATION_LABELS:
        crumbs.append(
            _crumb(ADMINISTRATION_LABELS[url_name], reverse(f"administration:{url_name}"))
        )
    return crumbs


def _products_trail(request: HttpRequest) -> list[dict[str, str]] | None:
    match = request.resolver_match
    if match is None:
        return None

    url_name = match.url_name
    crumbs = [_home_crumb()]

    if url_name in {"dogs", "cats", "brands", "all"}:
        crumbs.append(_crumb(PRODUCT_LABELS[url_name], reverse(f"products:{url_name}")))
        return crumbs

    if url_name == "browse":
        from products.catalog import (
            ANIMAL_SLUG_LABELS,
            CATEGORY_SLUG_LABELS,
            parse_filter_values,
            resolve_animal_slugs,
        )

        animal_slugs = resolve_animal_slugs(request)
        category_slugs = parse_filter_values(request, "category")
        if len(animal_slugs) != 1 or len(category_slugs) != 1:
            return None

        animal_slug = animal_slugs[0]
        category_slug = category_slugs[0]
        animal_label = ANIMAL_SLUG_LABELS.get(animal_slug, animal_slug)
        category_label = CATEGORY_SLUG_LABELS.get(category_slug, category_slug)
        animal_url_name = "dogs" if animal_slug == "dog" else "cats"

        crumbs.append(_crumb(animal_label, reverse(f"products:{animal_url_name}")))
        crumbs.append(_crumb(category_label, request.get_full_path()))
        return crumbs

    if url_name == "company":
        from products.models import Company

        company_code = match.kwargs.get("company_code")
        company = (
            Company.objects.filter(code__iexact=company_code).only("name").first()
            if company_code
            else None
        )
        label = company.name if company else "Μάρκα"
        crumbs.append(_crumb(label, request.get_full_path()))
        return crumbs

    if url_name == "detail":
        from products.catalog import get_product_detail_queryset

        slug = match.kwargs.get("slug")
        product = get_product_detail_queryset().filter(slug=slug).first()
        if not product:
            return crumbs

        animal_slug = product.animal_type.slug
        from products.catalog import ANIMAL_SLUG_LABELS, CATEGORY_SLUG_LABELS

        animal_label = ANIMAL_SLUG_LABELS.get(animal_slug, product.animal_type.name)
        category_label = CATEGORY_SLUG_LABELS.get(
            product.category.slug,
            product.category.name,
        )
        animal_url = reverse("products:dogs" if animal_slug == "dog" else "products:cats")
        browse_query = f"?animal={animal_slug}&category={product.category.slug}"

        crumbs.append(_crumb(animal_label, animal_url))
        crumbs.append(_crumb(category_label, reverse("products:browse") + browse_query))
        crumbs.append(_crumb(product.name, request.get_full_path()))
        return crumbs

    return None


def build_breadcrumbs(request: HttpRequest) -> list[dict[str, str]]:
    match = request.resolver_match
    if match is None or request.method != "GET":
        return []

    if match.url_name in SKIP_URL_NAMES:
        return []

    if request.path.startswith("/admin/") or "/api/" in request.path:
        return []

    app_name = match.app_name
    url_name = match.url_name

    if app_name == "administration" and url_name in ADMINISTRATION_LABELS:
        return _administration_trail(url_name)

    if app_name == "products":
        return _products_trail(request) or []

    if app_name == "accounts" and url_name in ACCOUNT_LABELS:
        return _accounts_trail(url_name, request)

    if app_name == "checkout" and url_name in CHECKOUT_LABELS:
        return _checkout_trail(url_name, request, **match.kwargs)

    if app_name == "wishlist" and url_name == "list":
        return [_home_crumb(), _crumb("Αγαπημένα", reverse("wishlist:list"))]

    if app_name == "pages":
        label = _page_label(url_name)
        if label:
            return [_home_crumb(), _crumb(label, request.get_full_path())]

    return []


def update_breadcrumb_trail(request: HttpRequest) -> list[dict[str, str]]:
    """Kept for middleware compatibility."""
    return build_breadcrumbs(request)
