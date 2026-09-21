from django.test import TestCase
from django.urls import reverse

from products.models import AnimalType, Category, Company, Product, ProductVariant


class HiddenProductCartTests(TestCase):
    def test_cannot_add_paused_product(self):
        company = Company.objects.create(name="Brand", code="BRD")
        animal = AnimalType.objects.create(name="Dog", slug="dog")
        category = Category.objects.create(name="Dry Food", slug="dry-food")
        product = Product.objects.create(
            name="Hidden Mix",
            company=company,
            animal_type=animal,
            category=category,
            is_active=False,
        )
        variant = ProductVariant.objects.create(
            product=product, weight=2, price=10, stock=5
        )

        response = self.client.post(reverse("cart:add"), {"variant_id": variant.pk})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])


class CartPageMarkupTests(TestCase):
    def test_cart_line_keeps_variant_id_on_the_stepper(self):
        company = Company.objects.create(name="Brand", code="BRD")
        animal = AnimalType.objects.create(name="Dog", slug="dog")
        category = Category.objects.create(name="Dry Food", slug="dry-food")
        product = Product.objects.create(
            name="Adult Mix",
            company=company,
            animal_type=animal,
            category=category,
            is_active=True,
        )
        variant = ProductVariant.objects.create(
            product=product, weight=2, price=10, stock=5
        )

        add = self.client.post(reverse("cart:add"), {"variant_id": variant.pk})
        self.assertEqual(add.status_code, 200)

        page = self.client.get(reverse("accounts:cart"))
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertNotRegex(html, r">\s*data-variant-id=")
        self.assertIn(f'data-variant-id="{variant.pk}"', html)
        self.assertContains(page, "Adult Mix")
