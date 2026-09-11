from collections import defaultdict

from products.catalog import AVAILABILITY_LABELS, format_weight, get_display_title
from products.models import ProductVariant


ADMIN_AVAILABILITY_CHOICES = (
    (ProductVariant.AVAILABILITY_AVAILABLE_NOW, "Άμεσα διαθέσιμο"),
    (ProductVariant.AVAILABILITY_ON_ORDER, "Κατόπιν παραγγελίας"),
    (ProductVariant.AVAILABILITY_OUT_OF_STOCK, "Προσωρινά μη διαθέσιμο"),
)

HIDDEN_SECTION_TITLE = "Κρυφά από το e-shop"
HIDDEN_SECTION_ANCHOR = "inventory-hidden"


def _inventory_anchor(prefix, index):
    return f"inventory-{prefix}-{index}"


def _variant_row(variant):
    product = variant.product
    company_name = product.company.name
    size_label = format_weight(variant.weight, variant.unit_label)
    display_title = get_display_title(product, variant)
    image_url = product.image.url if product.image else ""
    return {
        "variant_id": variant.pk,
        "product_id": product.pk,
        "product_name": product.name,
        "display_title": display_title,
        "size_label": size_label,
        "image_url": image_url,
        "stock": variant.stock,
        "availability": variant.availability,
        "availability_label": AVAILABILITY_LABELS.get(
            variant.availability,
            variant.availability,
        ),
        "sku": variant.sku or "",
        "is_paused": not product.is_active,
        "search_text": " ".join(
            part
            for part in (
                display_title,
                product.name,
                size_label,
                variant.sku or "",
                company_name,
            )
            if part
        ).lower(),
    }


def _group_variants(variants, *, prefix):
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    company_order = []
    category_order = defaultdict(list)
    animal_order = defaultdict(lambda: defaultdict(list))

    for variant in variants:
        product = variant.product
        company_name = product.company.name
        category_name = product.category.name
        animal_name = product.animal_type.name

        if company_name not in grouped:
            company_order.append(company_name)
        if category_name not in category_order[company_name]:
            category_order[company_name].append(category_name)
        if animal_name not in animal_order[company_name][category_name]:
            animal_order[company_name][category_name].append(animal_name)

        grouped[company_name][category_name][animal_name].append(_variant_row(variant))

    sections = []
    nav_entries = []
    for company_index, company_name in enumerate(company_order, start=1):
        company_anchor = _inventory_anchor(f"{prefix}-company", company_index)
        categories = []
        category_nav = []
        for category_index, category_name in enumerate(
            category_order[company_name], start=1
        ):
            category_anchor = _inventory_anchor(
                f"{prefix}-company-{company_index}-cat",
                category_index,
            )
            animals = []
            for animal_name in animal_order[company_name][category_name]:
                animals.append(
                    {
                        "name": animal_name,
                        "variants": grouped[company_name][category_name][animal_name],
                    }
                )
            categories.append(
                {
                    "name": category_name,
                    "anchor_id": category_anchor,
                    "animals": animals,
                }
            )
            category_nav.append(
                {
                    "name": category_name,
                    "anchor_id": category_anchor,
                }
            )
        sections.append(
            {
                "name": company_name,
                "anchor_id": company_anchor,
                "letter": company_name[0].upper() if company_name else "?",
                "categories": categories,
            }
        )
        nav_entries.append(
            {
                "name": company_name,
                "letter": company_name[0].upper() if company_name else "?",
                "anchor_id": company_anchor,
                "categories": category_nav,
            }
        )

    return sections, nav_entries


def build_inventory_sections():
    """
    Group all product variants for the administration inventory view.

    Visible storefront products come first (company → category → animal).
    Products hidden from the e-shop follow in a separate block at the end.
    """
    variants = list(
        ProductVariant.objects.select_related(
            "product__company",
            "product__category",
            "product__animal_type",
        ).order_by(
            "product__company__name",
            "product__category__name",
            "product__animal_type__name",
            "product__name",
            "weight",
        )
    )
    visible_variants = [variant for variant in variants if variant.product.is_active]
    hidden_variants = [variant for variant in variants if not variant.product.is_active]

    visible_sections, nav_entries = _group_variants(visible_variants, prefix="visible")
    hidden_sections, hidden_nav = _group_variants(hidden_variants, prefix="hidden")

    blocks = [
        {
            "title": None,
            "is_hidden": False,
            "anchor_id": None,
            "sections": visible_sections,
        }
    ]
    if hidden_sections:
        blocks.append(
            {
                "title": HIDDEN_SECTION_TITLE,
                "is_hidden": True,
                "anchor_id": HIDDEN_SECTION_ANCHOR,
                "sections": hidden_sections,
            }
        )
        nav_entries.append(
            {
                "name": HIDDEN_SECTION_TITLE,
                "letter": "Κ",
                "anchor_id": HIDDEN_SECTION_ANCHOR,
                "categories": [
                    {
                        "name": entry["name"],
                        "anchor_id": entry["anchor_id"],
                    }
                    for entry in hidden_nav
                ],
            }
        )

    return blocks, nav_entries
