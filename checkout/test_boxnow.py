from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from checkout.boxnow_pricing import (
    COMPARTMENT_LARGE,
    COMPARTMENT_MEDIUM,
    COMPARTMENT_SMALL,
    calculate_boxnow_shipping_cost,
    determine_compartment_size,
    exceeds_boxnow_weight_limit,
)
from checkout.delivery import build_delivery_options, calculate_courier_fee
from orders.models import Order
from products.utils import REGION_ATTICA


def _cart_item(*, weight, length=10, width=10, height=10, quantity=1):
    product = SimpleNamespace(
        weight=Decimal(str(weight)),
        length=Decimal(str(length)),
        width=Decimal(str(width)),
        height=Decimal(str(height)),
    )
    return SimpleNamespace(product=product, quantity=quantity)


@override_settings(
    BOXNOW_FEE_SMALL=Decimal("1.80"),
    BOXNOW_FEE_MEDIUM=Decimal("2.50"),
    BOXNOW_FEE_LARGE=Decimal("3.50"),
    BOXNOW_SMALL_MAX_KG="4.0",
    BOXNOW_MEDIUM_MAX_KG="10.0",
)
class BoxNowPricingTests(SimpleTestCase):
    def test_small_compartment_for_light_cart(self):
        items = [_cart_item(weight=2)]
        self.assertEqual(determine_compartment_size(items), COMPARTMENT_SMALL)

    def test_medium_compartment_for_mid_weight_cart(self):
        items = [_cart_item(weight=6)]
        self.assertEqual(determine_compartment_size(items), COMPARTMENT_MEDIUM)

    def test_large_compartment_for_heavy_cart(self):
        items = [_cart_item(weight=12)]
        self.assertEqual(determine_compartment_size(items), COMPARTMENT_LARGE)

    def test_free_shipping_over_minimum(self):
        items = [_cart_item(weight=2)]
        fee = calculate_boxnow_shipping_cost(
            items,
            Decimal("60.00"),
            REGION_ATTICA,
        )
        self.assertEqual(fee, Decimal("0.00"))

    def test_charges_medium_fee_outside_free_threshold(self):
        items = [_cart_item(weight=6)]
        fee = calculate_boxnow_shipping_cost(
            items,
            Decimal("15.00"),
            REGION_ATTICA,
        )
        self.assertEqual(fee, Decimal("2.50"))

    def test_exceeds_weight_limit_above_max_kg(self):
        items = [_cart_item(weight=12)]
        self.assertTrue(exceeds_boxnow_weight_limit(items))


@override_settings(
    BOXNOW_PARTNER_ID="123",
    BOXNOW_FEE_SMALL=Decimal("1.80"),
    BOXNOW_FEE_MEDIUM=Decimal("2.50"),
    BOXNOW_FEE_LARGE=Decimal("3.50"),
    BOXNOW_SMALL_MAX_KG="4.0",
    BOXNOW_MEDIUM_MAX_KG="10.0",
    BOXNOW_WIDGET_ENABLED=True,
    COURIER_FLAT_FEE=Decimal("5.00"),
    FREE_SHIPPING_ORDER_MINIMUM=Decimal("60.00"),
)
class BoxNowDeliveryOptionsTests(SimpleTestCase):
    def test_build_delivery_options_includes_box_now(self):
        options, _within = build_delivery_options(
            cart_total=Decimal("15.00"),
            postal_code="10563",
            cart=[_cart_item(weight=2)],
        )
        values = [option["value"] for option in options]
        self.assertIn(Order.DELIVERY_METHOD_BOX_NOW, values)
        box_now = next(
            option for option in options
            if option["value"] == Order.DELIVERY_METHOD_BOX_NOW
        )
        self.assertTrue(box_now["requires_locker"])
        self.assertEqual(box_now["fee"], Decimal("1.80"))

    def test_calculate_courier_fee_for_box_now(self):
        fee = calculate_courier_fee(
            "10563",
            Order.DELIVERY_METHOD_BOX_NOW,
            cart=[_cart_item(weight=2)],
            cart_total=Decimal("15.00"),
        )
        self.assertEqual(fee, Decimal("1.80"))

    def test_box_now_disabled_when_cart_too_heavy(self):
        options, _within = build_delivery_options(
            cart_total=Decimal("15.00"),
            postal_code="10563",
            cart=[_cart_item(weight=12)],
        )
        box_now = next(
            option for option in options
            if option["value"] == Order.DELIVERY_METHOD_BOX_NOW
        )
        self.assertTrue(box_now["disabled"])
        self.assertFalse(box_now["requires_locker"])
        self.assertIn("courier", box_now["unavailable_message"])
        self.assertNotIn("ELTA", box_now["unavailable_message"])
        courier = next(
            option for option in options
            if option["value"] == Order.DELIVERY_METHOD_COURIER
        )
        self.assertFalse(courier["disabled"])
        self.assertEqual(courier["fee"], Decimal("5.00"))


@override_settings(BOXNOW_PARTNER_ID="123", BOXNOW_WIDGET_ENABLED=True)
class BoxNowCheckoutDeliveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        from products.models import AnimalType, Category, Company, Product, ProductVariant

        User = get_user_model()
        cls.user = User.objects.create_user(
            email="boxnow@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            phone_number="+306900000000",
            city="Αθήνα",
            street="Ερμού",
            street_number="1",
            postal_code="10563",
            latitude=Decimal("37.9755"),
            longitude=Decimal("23.7348"),
        )
        company = Company.objects.create(name="BRAND", code="BRD")
        animal = AnimalType.objects.create(name="Cat", slug="cat")
        category = Category.objects.create(name="Dry Food", slug="dry-food")
        product = Product.objects.create(
            name="Test Product",
            company=company,
            animal_type=animal,
            category=category,
            is_active=True,
        )
        cls.variant = ProductVariant.objects.create(
            product=product,
            weight=Decimal("2.00"),
            price=Decimal("10.00"),
        )

    def setUp(self):
        from checkout.helpers import SESSION_KEY

        self.session_key = SESSION_KEY
        self.client.force_login(self.user)
        session = self.client.session
        session[self.session_key] = {
            "phone_number": self.user.phone_number,
            "city": self.user.city,
            "address": "Ερμού 1",
            "postal_code": "10563",
            "floor": "",
            "latitude": str(self.user.latitude),
            "longitude": str(self.user.longitude),
            "delivery_notes": "",
        }
        session.save()
        self.client.post(
            "/cart/add/",
            {"variant_id": self.variant.pk, "quantity": 1},
        )

    def test_box_now_requires_locker_selection(self):
        response = self.client.post(
            "/checkout/delivery/",
            {"delivery_method": Order.DELIVERY_METHOD_BOX_NOW},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Επίλεξε σημείο παραλαβής BOX NOW")

    @patch("checkout.views.schedule_boxnow_delivery")
    def test_box_now_post_with_locker_advances_to_payment(self, mock_schedule):
        response = self.client.post(
            "/checkout/delivery/",
            {
                "delivery_method": Order.DELIVERY_METHOD_BOX_NOW,
                "boxnow_locker_id": "42",
                "boxnow_locker_name": "Locker Test",
                "boxnow_locker_address": "Ερμού 10",
                "boxnow_locker_postal_code": "10563",
            },
        )
        self.assertRedirects(response, "/checkout/payment/")
        data = self.client.session[self.session_key]
        self.assertEqual(data["delivery_method"], Order.DELIVERY_METHOD_BOX_NOW)
        self.assertEqual(data["boxnow_locker_id"], "42")
