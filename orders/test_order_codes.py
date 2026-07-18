"""Tests for public order codes."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from orders.codes import generate_order_code
from orders.models import Order

User = get_user_model()


class OrderCodeTests(TestCase):
    def test_generate_order_code_has_prefix(self):
        code = generate_order_code()
        self.assertTrue(code.startswith("KPK"))
        self.assertEqual(len(code), 11)

    def test_new_order_gets_unique_public_code(self):
        user = User.objects.create_user(email="code@example.com", password="x")
        order = Order.objects.create(
            user=user,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=Decimal("10.00"),
            courier_fee=Decimal("0.00"),
            total_cost=Decimal("10.00"),
            delivery_method=Order.DELIVERY_METHOD_COURIER,
            delivery_phone_number="+306900000000",
            delivery_city="Αθήνα",
            delivery_address="Ερμού 1",
            delivery_postal_code="10563",
            delivery_latitude=Decimal("37.9755"),
            delivery_longitude=Decimal("23.7348"),
        )
        self.assertTrue(order.order_code.startswith("KPK"))
        self.assertEqual(order.public_code_display, f"#{order.order_code}")

    def test_two_orders_never_share_code(self):
        user = User.objects.create_user(email="code2@example.com", password="x")
        common = {
            "user": user,
            "payment_method": Order.PAYMENT_METHOD_COD,
            "status": Order.STATUS_NEW,
            "cart_cost": Decimal("10.00"),
            "courier_fee": Decimal("0.00"),
            "total_cost": Decimal("10.00"),
            "delivery_method": Order.DELIVERY_METHOD_COURIER,
            "delivery_phone_number": "+306900000000",
            "delivery_city": "Αθήνα",
            "delivery_address": "Ερμού 1",
            "delivery_postal_code": "10563",
            "delivery_latitude": Decimal("37.9755"),
            "delivery_longitude": Decimal("23.7348"),
        }
        first = Order.objects.create(**common)
        second = Order.objects.create(**common)
        self.assertNotEqual(first.order_code, second.order_code)
