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
