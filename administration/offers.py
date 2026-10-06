"""Administration CRUD helpers for product offers."""
from decimal import Decimal, InvalidOperation

from django.db import transaction

from products.catalog import format_decimal_greek, get_display_title
from products.models import Offer, OfferItem, ProductVariant
from products.offers import offer_regular_total
from products.pricing import ceil_to_tenth


def parse_money(raw):
    text = (raw or "").strip().replace("€", "").replace(" ", "").replace(",", ".")
    if not text:
        raise ValueError("empty")
    try:
        amount = Decimal(text)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("invalid") from exc
    if amount <= 0:
        raise ValueError("non_positive")
    return ceil_to_tenth(amount)


def parse_offer_lines_from_post(post):
    """
    Expect parallel lists: variant_id[], quantity[].
    Returns list of (ProductVariant, qty).
    """
    variant_ids = post.getlist("variant_id")
    quantities = post.getlist("quantity")
    if not variant_ids:
        raise ValueError("no_items")
    lines = []
    seen = set()
    for index, raw_id in enumerate(variant_ids):
        try:
            variant_id = int(raw_id)
            qty = int(quantities[index]) if index < len(quantities) else 1
        except (TypeError, ValueError, IndexError) as exc:
            raise ValueError("bad_line") from exc
        if qty < 1:
            raise ValueError("bad_qty")
        if variant_id in seen:
            continue
        seen.add(variant_id)
        try:
            variant = ProductVariant.objects.select_related("product").get(pk=variant_id)
        except ProductVariant.DoesNotExist as exc:
            raise ValueError("missing_variant") from exc
        lines.append((variant, qty))
    if not lines:
        raise ValueError("no_items")
    return lines


def resolve_offer_title(*, title, lines):
    """
    Single-item offers never need a custom title — use the product name.
    Multi-item packages require an explicit package title.
    """
    if len(lines) == 1:
        variant, qty = lines[0]
        bit = get_display_title(variant.product, variant)
        return f"{qty}× {bit}" if qty > 1 else bit
    cleaned = (title or "").strip()
    if not cleaned:
        raise ValueError("title_required")
    return cleaned


def save_offer(*, title, price, is_active, lines, offer=None):
    resolved_title = resolve_offer_title(title=title, lines=lines)
    with transaction.atomic():
        if offer is None:
            offer = Offer(title=resolved_title, price=price, is_active=is_active)
            offer.save()
        else:
            offer.title = resolved_title
            offer.price = price
            offer.is_active = is_active
            offer.save()
        offer.items.all().delete()
        OfferItem.objects.bulk_create(
            [
                OfferItem(offer=offer, variant=variant, quantity=qty)
                for variant, qty in lines
            ]
        )
        offer.refresh_discount(save=True)
        return offer


def build_offer_admin_rows():
    rows = []
    for offer in Offer.objects.prefetch_related(
        "items__variant__product__company"
    ).order_by("-updated_at"):
        items = list(offer.items.all())
        regular = offer_regular_total(offer)
        images = []
        components = []
        for item in items:
            product = item.variant.product
            if product.image:
                images.append(product.image.url)
            components.append(
                {
                    "title": get_display_title(product, item.variant),
                    "quantity": item.quantity,
                    "image_url": product.image.url if product.image else None,
                    "regular_price_display": format_decimal_greek(
                        item.variant.selling_price
                    ),
                }
            )
        is_single = len(items) == 1
        rows.append(
            {
                "offer": offer,
                "is_single": is_single,
                "kind_label": "Έκπτωση προϊόντος" if is_single else "Πακέτο",
                "item_count": len(items),
                "regular_display": format_decimal_greek(regular),
                "price_display": format_decimal_greek(offer.selling_price),
                "images": images[:4],
                "components": components,
                "search_text": " ".join(
                    [
                        offer.title or "",
                        *[c["title"] for c in components],
                    ]
                ).lower(),
            }
        )
    return rows


def variant_picker_options():
    options = []
    qs = (
        ProductVariant.objects.select_related(
            "product__company",
            "product__animal_type",
            "product__category",
        )
        .filter(product__is_active=True)
        .order_by("product__company__name", "product__name", "weight")
    )
    for variant in qs:
        product = variant.product
        options.append(
            {
                "id": variant.pk,
                "label": (
                    f"{product.company.name} — "
                    f"{get_display_title(product, variant)} "
                    f"({format_decimal_greek(variant.selling_price)} €)"
                ),
                "name": get_display_title(product, variant),
                "company": product.company.name,
                "price": str(variant.selling_price),
                "price_display": format_decimal_greek(variant.selling_price),
                "image_url": product.image.url if product.image else "",
            }
        )
    return options
