from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from cart.cart import CartError, DBCart
from checkout.helpers import SESSION_KEY
from checkout.views import _create_order_from_checkout
from orders.models import Order
from orders.stock import reserve_stock_for_cart
from products.models import (
    AnimalType,
    Category,
    Company,
    Offer,
    OfferItem,
    Product,
    ProductVariant,
)

User = get_user_model()


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


class OfferCartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="Brand", code="BRD")
        cls.animal = AnimalType.objects.create(name="Dog", slug="dog")
        cls.category = Category.objects.create(name="Dry Food", slug="dry-food")
        cls.product_a = Product.objects.create(
            name="Offer A",
            company=cls.company,
            animal_type=cls.animal,
            category=cls.category,
            is_active=True,
        )
        cls.product_b = Product.objects.create(
            name="Offer B",
            company=cls.company,
            animal_type=cls.animal,
            category=cls.category,
            is_active=True,
        )
        cls.variant_a = ProductVariant.objects.create(
            product=cls.product_a,
            weight=Decimal("2.00"),
            price=Decimal("10.00"),
            stock=5,
        )
        cls.variant_b = ProductVariant.objects.create(
            product=cls.product_b,
            weight=Decimal("3.00"),
            price=Decimal("20.00"),
            stock=4,
        )
        cls.offer = Offer.objects.create(
            title="Πακέτο Α+Β",
            price=Decimal("25.00"),
            is_active=True,
        )
        OfferItem.objects.create(offer=cls.offer, variant=cls.variant_a, quantity=1)
        OfferItem.objects.create(offer=cls.offer, variant=cls.variant_b, quantity=1)
        cls.offer.refresh_discount()

    def test_add_offer_via_api(self):
        response = self.client.post(
            reverse("cart:add"),
            {"offer_id": self.offer.pk},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["offer_id"], self.offer.pk)
        self.assertEqual(data["quantity"], 1)
        self.assertEqual(data["offer_quantities"][str(self.offer.pk)], 1)
        self.assertEqual(data["total_items"], 1)

    def test_offer_appears_on_cart_page(self):
        self.client.post(reverse("cart:add"), {"offer_id": self.offer.pk})
        page = self.client.get(reverse("accounts:cart"))
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertIn(f'data-offer-id="{self.offer.pk}"', html)
        self.assertContains(page, "Πακέτο Α+Β")

    def test_offer_stock_blocks_when_component_short(self):
        self.variant_a.stock = 0
        self.variant_a.save(update_fields=["stock"])
        response = self.client.post(
            reverse("cart:add"),
            {"offer_id": self.offer.pk},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_reserve_stock_expands_offer_components(self):
        user = User.objects.create_user(
            email="offer-stock@example.com",
            password="testpass123",
        )
        cart = DBCart(user)
        cart.add_offer(self.offer, quantity=2)
        reserve_stock_for_cart(cart)
        self.variant_a.refresh_from_db()
        self.variant_b.refresh_from_db()
        self.assertEqual(self.variant_a.stock, 3)
        self.assertEqual(self.variant_b.stock, 2)

    def test_checkout_creates_proportional_order_items(self):
        user = User.objects.create_user(
            email="offer-order@example.com",
            password="testpass123",
        )
        cart = DBCart(user)
        cart.add_offer(self.offer, quantity=1)
        factory = RequestFactory()
        request = factory.post("/checkout/payment/")
        request.user = user
        from django.contrib.sessions.middleware import SessionMiddleware

        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        checkout_data = {
            "delivery_method": Order.DELIVERY_METHOD_COURIER,
            "phone_number": "+306900000000",
            "city": "Αθήνα",
            "address": "Ερμού 1",
            "postal_code": "10563",
            "floor": "",
            "latitude": "37.9755",
            "longitude": "23.7348",
            "delivery_notes": "",
        }
        request.session[SESSION_KEY] = checkout_data
        order = _create_order_from_checkout(
            request,
            cart=cart,
            checkout_data=checkout_data,
            payment_method=Order.PAYMENT_METHOD_COD,
            courier_fee=Decimal("2.00"),
            cart_total=Decimal("25.00"),
            total_cost=Decimal("27.00"),
            order_status=Order.STATUS_NEW,
        )
        items = list(order.items.select_related("product_variant").order_by("pk"))
        self.assertEqual(len(items), 2)
        total = sum(item.price_at_purchase * item.quantity for item in items)
        self.assertEqual(total, Decimal("25.00"))
        self.variant_a.refresh_from_db()
        self.variant_b.refresh_from_db()
        self.assertEqual(self.variant_a.stock, 4)
        self.assertEqual(self.variant_b.stock, 3)

    def test_cannot_overbook_offer_packages(self):
        user = User.objects.create_user(
            email="offer-limit@example.com",
            password="testpass123",
        )
        cart = DBCart(user)
        cart.add_offer(self.offer, quantity=4)
        with self.assertRaises(CartError):
            cart.add_offer(self.offer, quantity=1)
