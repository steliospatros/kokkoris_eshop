"""Build offer cards and catalog merge rules for promotions."""
from decimal import Decimal

from django.db.models import Count, Prefetch
from django.urls import reverse

from products.catalog import format_decimal_greek, get_display_title, get_stock_display
from products.models import Offer, OfferItem, ProductVariant
from products.pricing import ceil_to_tenth


def active_offers_queryset():
    return (
        Offer.objects.filter(is_active=True)
        .annotate(item_count=Count("items"))
        .filter(item_count__gt=0)
        .prefetch_related(
            Prefetch(
                "items",
                queryset=OfferItem.objects.select_related(
                    "variant__product__company",
                    "variant__product__category",
                    "variant__product__animal_type",
                ).order_by("pk"),
            )
        )
        .order_by("-updated_at", "-pk")
    )


def offer_regular_total(offer):
    total = Decimal("0.00")
    for line in offer.component_lines():
        total += line.variant.selling_price * line.quantity
    return ceil_to_tenth(total)


def allocate_offer_unit_prices(offer):
    """
    Split package price across component lines proportionally.
    Returns list of (variant, qty_per_package, unit_price).
    """
    lines = offer.component_lines()
    if not lines:
        return []
    regular_parts = [
        (line, line.variant.selling_price * line.quantity) for line in lines
    ]
    regular_total = sum(part for _, part in regular_parts) or Decimal("0.00")
    package = offer.selling_price
    allocated = []
    remaining = package
    for index, (line, part) in enumerate(regular_parts):
        if index == len(regular_parts) - 1:
            line_total = remaining
        elif regular_total > 0:
            line_total = ceil_to_tenth(package * (part / regular_total))
            remaining -= line_total
        else:
            line_total = Decimal("0.00")
        unit = ceil_to_tenth(line_total / line.quantity) if line.quantity else line_total
        allocated.append((line.variant, line.quantity, unit))
    return allocated


def single_item_replaced_product_ids(offers=None):
    """Product PKs whose catalog card is replaced by a single-variant offer."""
    offers = offers if offers is not None else active_offers_queryset()
    replaced = set()
    for offer in offers:
        lines = offer.component_lines()
        if len(lines) == 1:
            replaced.add(lines[0].variant.product_id)
    return replaced


def build_offer_card(offer, *, cart_qty=0):
    lines = offer.component_lines()
    if not lines:
        return None
    regular = offer_regular_total(offer)
    images = []
    for line in lines:
        product = line.variant.product
        if product.image:
            images.append(product.image.url)
        else:
            images.append("")
    # Collage uses unique product images in offer order (keep duplicates if qty>1? use once per line)
    title_bits = []
    for line in lines:
        bit = get_display_title(line.variant.product, line.variant)
        if line.quantity > 1:
            bit = f"{line.quantity}× {bit}"
        title_bits.append(bit)
    # Single-item: always show the product name (ignore custom package title).
    if len(lines) == 1:
        title = title_bits[0]
        product = lines[0].variant.product
        product_id = product.pk
        sizes_label = "Προσφορά"
        detail_url = reverse("products:detail", kwargs={"slug": product.slug}) if product.slug else ""
        sku = product.sku or ""
    else:
        title = offer.title or " + ".join(title_bits)
        product_id = None
        sizes_label = f"{len(lines)} προϊόντα"
        detail_url = ""
        sku = ""

    # Stock: limited by scarcest available_now component
    can_add = True
    max_packages = None
    for line in lines:
        stock = get_stock_display(line.variant)
        if not stock["can_add"]:
            can_add = False
            max_packages = 0
            break
        if stock["max_quantity"] is not None:
            packs = stock["max_quantity"] // line.quantity
            max_packages = packs if max_packages is None else min(max_packages, packs)

    return {
        "kind": "offer",
        "offer_id": offer.pk,
        "product_id": product_id,
        "variant_id": None,
        "title": title,
        "detail_url": detail_url,
        # Collage only for multi-product packages; single-item uses a normal photo.
        "image_urls": images if len(lines) > 1 else [],
        "image_url": images[0] if images else None,
        "sizes_label": sizes_label,
        "sku": sku,
        "availability_label": "Άμεσα" if can_add else "Μη διαθέσιμο",
        "availability_color_class": "text-emerald-700" if can_add else "text-slate-500",
        "price_display": format_decimal_greek(offer.selling_price),
        "regular_price_display": format_decimal_greek(regular) if regular > offer.selling_price else "",
        "discount_percent": offer.discount_percent,
        "unit_price_display": "",
        "unit_label": "",
        "cart_qty": cart_qty,
        "can_add": can_add and (max_packages is None or max_packages > 0),
        "max_quantity": max_packages,
        "is_on_order": False,
        "button_label": "Αγορά",
        "is_wishlisted": False,
        "component_count": len(lines),
    }


def build_offer_cards(offers=None, cart_offer_quantities=None):
    cart_offer_quantities = cart_offer_quantities or {}
    offers = offers if offers is not None else list(active_offers_queryset())
    cards = []
    for offer in offers:
        card = build_offer_card(
            offer,
            cart_qty=cart_offer_quantities.get(offer.pk, 0),
        )
        if card:
            cards.append(card)
    return cards


def merge_catalog_with_offers(product_cards, *, offer_cards=None, replaced_product_ids=None):
    """Offers first; drop product cards replaced by single-item offers."""
    offer_cards = offer_cards if offer_cards is not None else build_offer_cards()
    replaced_product_ids = (
        replaced_product_ids
        if replaced_product_ids is not None
        else single_item_replaced_product_ids()
    )
    filtered = [
        card
        for card in product_cards
        if card.get("product_id") not in replaced_product_ids
    ]
    return list(offer_cards) + filtered
