from collections import defaultdict

from products.catalog import AVAILABILITY_LABELS, format_weight
from products.models import ProductVariant


def _inventory_anchor(prefix, index):
    return f"inventory-{prefix}-{index}"


def build_inventory_sections():
    """
    Group all product variants for the administration inventory view.

    Hierarchy: company → category → animal type → variant rows.
    Each variant is listed separately (different package sizes = separate rows).
    """
    variants = (
        ProductVariant.objects.select_related(
            "product__company",
            "product__category",
            "product__animal_type",
        )
        .order_by(
            "product__company__name",
            "product__category__name",
            "product__animal_type__name",
            "product__name",
            "weight",
        )
    )

    grouped = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
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

        grouped[company_name][category_name][animal_name].append(
            {
                "variant_id": variant.pk,
                "product_id": product.pk,
                "product_name": product.name,
                "size_label": f"{format_weight(variant.weight)} {variant.unit_label}",
                "stock": variant.stock,
                "availability_label": AVAILABILITY_LABELS.get(
                    variant.availability,
                    variant.availability,
                ),
                "sku": variant.sku or "",
                "is_paused": not product.is_active,
            }
        )

    sections = []
    nav_entries = []
    for company_index, company_name in enumerate(company_order, start=1):
        company_anchor = _inventory_anchor("company", company_index)
        categories = []
        category_nav = []
        for category_index, category_name in enumerate(category_order[company_name], start=1):
            category_anchor = _inventory_anchor(
                f"company-{company_index}-cat",
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
