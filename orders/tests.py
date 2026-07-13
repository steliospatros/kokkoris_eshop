from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from cart.cart import DBCart
from checkout.helpers import SESSION_KEY
from checkout.views import _create_order_from_checkout
from orders.models import Order
from orders.presentation import add_business_days, build_delivery_eta_message
from orders.stock import release_stock_for_order, reserve_stock_for_cart
from products.models import AnimalType, Category, Company, Product, ProductVariant

User = get_user_model()


class OrderStockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="stock@example.com",
            password="testpass123",
        )
        company = Company.objects.create(name="BRAND", code="BRD")
        animal = AnimalType.objects.create(name="Dog", slug="dog")
        category = Category.objects.create(name="Dry Food", slug="dry-food")
        product = Product.objects.create(
            name="Stock Product",
            company=company,
            animal_type=animal,
            category=category,
            is_active=True,
        )
        cls.variant = ProductVariant.objects.create(
            product=product,
            weight=Decimal("2.00"),
            price=Decimal("10.00"),
            stock=5,
        )

    def test_reserve_stock_decrements_variant(self):
        cart = DBCart(self.user)
        cart.add_item(self.variant, quantity=2)
        reserve_stock_for_cart(cart)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)

    def test_release_stock_restores_variant_on_cancel(self):
        cart = DBCart(self.user)
        cart.add_item(self.variant, quantity=2)
        factory = RequestFactory()
        request = factory.post("/checkout/payment/")
        request.user = self.user
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
            cart_total=Decimal("20.00"),
            total_cost=Decimal("22.00"),
            order_status=Order.STATUS_NEW,
        )
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)
        release_stock_for_order(order)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 5)


class OrderPresentationTests(TestCase):
    def test_add_business_days_skips_weekend(self):
        self.assertEqual(
            add_business_days(date(2026, 7, 13), 3),
            date(2026, 7, 16),
        )

    def test_eta_message_mentions_registration_time(self):
        user = User.objects.create_user(email="eta@example.com", password="x")
        order = Order.objects.create(
            user=user,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=Decimal("10.00"),
            courier_fee=Decimal("0.00"),
            total_cost=Decimal("10.00"),
            delivery_method=Order.DELIVERY_METHOD_COMPANY,
            delivery_phone_number="+306900000000",
            delivery_city="Αθήνα",
            delivery_address="Ερμού 1",
            delivery_postal_code="10563",
            delivery_latitude=Decimal("37.9755"),
            delivery_longitude=Decimal("23.7348"),
        )
        message = build_delivery_eta_message(order)
        self.assertIn("καταχώρησης", message)
        self.assertIn("3–4 εργάσιμες", message)


class OrderDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="detail@example.com",
            password="testpass123",
        )
        cls.order = Order.objects.create(
            user=cls.user,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=Decimal("10.00"),
            courier_fee=Decimal("2.00"),
            total_cost=Decimal("12.00"),
            delivery_method=Order.DELIVERY_METHOD_COURIER,
            delivery_phone_number="+306900000000",
            delivery_city="Αθήνα",
            delivery_address="Ερμού 1",
            delivery_postal_code="10563",
            delivery_latitude=Decimal("37.9755"),
            delivery_longitude=Decimal("23.7348"),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_order_detail_page_renders(self):
        response = self.client.get(
            reverse("orders:detail", kwargs={"order_id": self.order.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Λεπτομέρειες παραγγελίας")
        self.assertContains(response, "Ενημέρωση παράδοσης")
        self.assertContains(response, "Διεύθυνση παράδοσης")

    def test_confirmation_page_uses_detail_sections(self):
        response = self.client.get(
            reverse("checkout:confirmation", kwargs={"order_id": self.order.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Κόστος παραγγελίας")
