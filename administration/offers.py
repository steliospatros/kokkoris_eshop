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


def save_offer(*, title, price, is_active, lines, offer=None):
    with transaction.atomic():
        if offer is None:
            offer = Offer(title=title, price=price, is_active=is_active)
            offer.save()
        else:
            offer.title = title
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
        "items__variant__product"
    ).order_by("-updated_at"):
        regular = offer_regular_total(offer)
        rows.append(
            {
                "offer": offer,
                "item_count": offer.items.count(),
                "regular_display": format_decimal_greek(regular),
                "price_display": format_decimal_greek(offer.selling_price),
                "components": [
                    {
                        "title": get_display_title(item.variant.product, item.variant),
                        "quantity": item.quantity,
                    }
                    for item in offer.items.all()
                ],
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
        options.append(
            {
                "id": variant.pk,
                "label": (
                    f"{variant.product.company.name} — "
                    f"{get_display_title(variant.product, variant)} "
                    f"({format_decimal_greek(variant.selling_price)} €)"
                ),
                "price": str(variant.selling_price),
            }
        )
    return options
