from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from products.models import AnimalType, Category, Company, Product, ProductVariant


class ProductDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="TESTBRAND", code="TST")
        cls.animal = AnimalType.objects.create(name="Dog", slug="dog")
        cls.category = Category.objects.create(name="Dry Food", slug="dry-food")
        cls.product = Product.objects.create(
            name="Test Adult Chicken",
            company=cls.company,
            animal_type=cls.animal,
            category=cls.category,
            description="Πλήρης τροφή για ενήλικους σκύλους.",
            components="Κοτόπουλο 30%, ρύζι.",
            is_active=True,
        )
        cls.variant_small = ProductVariant.objects.create(
            product=cls.product,
            weight=Decimal("2.00"),
            sku="TST-2KG",
            price=Decimal("11.50"),
        )
        cls.variant_large = ProductVariant.objects.create(
            product=cls.product,
            weight=Decimal("10.00"),
            sku="TST-10KG",
            price=Decimal("45.00"),
        )

    def test_product_detail_page_renders(self):
        url = reverse("products:detail", kwargs={"slug": self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Adult Chicken")
        self.assertContains(response, "Πλήρης τροφή")
        self.assertContains(response, "Κοτόπουλο 30%")
        self.assertContains(response, "TST-10KG")

    def test_product_detail_unknown_slug_404(self):
        response = self.client.get(reverse("products:detail", kwargs={"slug": "missing-product"}))
        self.assertEqual(response.status_code, 404)

    def test_related_products_priority(self):
        from products.catalog import get_related_products_for_detail

        other_company = Company.objects.create(name="OTHER", code="OTH")
        same_cat_other_brand = Product.objects.create(
            name="Same Cat Other Brand",
            company=other_company,
            animal_type=self.animal,
            category=self.category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=same_cat_other_brand,
            weight=Decimal("1.00"),
            price=Decimal("5.00"),
        )

        other_category = Category.objects.create(name="Sachets", slug="sachets")
        same_brand_other_cat = Product.objects.create(
            name="Same Brand Other Cat",
            company=self.company,
            animal_type=self.animal,
            category=other_category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=same_brand_other_cat,
            weight=Decimal("1.00"),
            price=Decimal("5.00"),
        )

        other_animal = AnimalType.objects.create(name="Cat", slug="cat")
        wrong_animal = Product.objects.create(
            name="Wrong Animal",
            company=self.company,
            animal_type=other_animal,
            category=self.category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=wrong_animal,
            weight=Decimal("1.00"),
            price=Decimal("5.00"),
        )

        unrelated = Product.objects.create(
            name="Unrelated Dog",
            company=other_company,
            animal_type=self.animal,
            category=other_category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=unrelated,
            weight=Decimal("1.00"),
            price=Decimal("5.00"),
        )

        twin = Product.objects.create(
            name="Twin Product",
            company=self.company,
            animal_type=self.animal,
            category=self.category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=twin,
            weight=Decimal("3.00"),
            price=Decimal("15.00"),
        )

        related = get_related_products_for_detail(self.product)
        names = [p.name for p in related]
        self.assertIn("Twin Product", names)
        self.assertIn("Same Cat Other Brand", names)
        self.assertIn("Same Brand Other Cat", names)
        self.assertNotIn("Wrong Animal", names)
        self.assertNotIn("Unrelated Dog", names)
        self.assertEqual(names[0], "Twin Product")
        self.assertEqual(names[1], "Same Cat Other Brand")
        self.assertEqual(names[2], "Same Brand Other Cat")

    def test_product_detail_filter_links(self):
        url = reverse("products:detail", kwargs={"slug": self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"?animal={self.animal.slug}")
        self.assertContains(response, f"?category={self.category.slug}")
        self.assertContains(response, f"?brand={self.company.code}")

    def test_catalog_card_includes_detail_url(self):
        from products.catalog import build_catalog_card, get_catalog_queryset

        product = get_catalog_queryset().get(pk=self.product.pk)
        card = build_catalog_card(product)
        self.assertIn("detail_url", card)
        self.assertIn(self.product.slug, card["detail_url"])
