from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from products.models import AnimalType, Category, Company, Product, ProductVariant
from products.shelf_stock import apply_warehouse_stock


class ApplyWarehouseStockTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Alpha Co", code="ALP")
        self.category = Category.objects.create(name="Dry Food")
        self.dog = AnimalType.objects.create(name="Dog", slug="dog")
        self.on_shelf = Product.objects.create(
            name="Shelf Mix",
            company=self.company,
            category=self.category,
            animal_type=self.dog,
        )
        self.on_order = Product.objects.create(
            name="Order Mix",
            company=self.company,
            category=self.category,
            animal_type=self.dog,
        )
        self.shelf_variant = ProductVariant.objects.create(
            product=self.on_shelf,
            weight=Decimal("12.00"),
            price=Decimal("20.00"),
            stock=20,
            availability=ProductVariant.AVAILABILITY_AVAILABLE_NOW,
        )
        self.other_variant = ProductVariant.objects.create(
            product=self.on_order,
            weight=Decimal("3.00"),
            price=Decimal("10.00"),
            stock=20,
            availability=ProductVariant.AVAILABILITY_AVAILABLE_NOW,
        )

    def test_unlisted_variants_become_on_order_with_zero_shop_stock(self):
        items = (
            (
                "Alpha Co",
                "Shelf Mix",
                Decimal("12.00"),
                7,
                "",
            ),
        )
        with patch("products.shelf_stock.SHELF_ITEMS", items):
            with patch("products.shelf_stock.CARNIS_CAT_WEIGHT_UPDATES", ()):
                report = apply_warehouse_stock()

        self.shelf_variant.refresh_from_db()
        self.other_variant.refresh_from_db()
        self.assertEqual(report["on_order"], 2)
        self.assertEqual(self.shelf_variant.stock, 7)
        self.assertEqual(
            self.shelf_variant.availability,
            ProductVariant.AVAILABILITY_AVAILABLE_NOW,
        )
        self.assertEqual(self.other_variant.stock, 0)
        self.assertEqual(
            self.other_variant.availability,
            ProductVariant.AVAILABILITY_ON_ORDER,
        )
