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


def _cart_item(*, weight, length=6, width=20, height=30, quantity=1):
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
    BOXNOW_MAX_WEIGHT_KG="20.0",
)
class BoxNowPricingTests(SimpleTestCase):
    def test_small_compartment_for_small_dims(self):
        items = [_cart_item(weight=1, length=6, width=20, height=30)]
        self.assertEqual(determine_compartment_size(items), COMPARTMENT_SMALL)

    def test_medium_compartment_when_height_exceeds_small(self):
        items = [_cart_item(weight=3, length=12, width=30, height=40)]
        self.assertEqual(determine_compartment_size(items), COMPARTMENT_MEDIUM)

    def test_large_compartment_for_tall_pack(self):
        items = [_cart_item(weight=8, length=20, width=40, height=50)]
        self.assertEqual(determine_compartment_size(items), COMPARTMENT_LARGE)

    def test_free_shipping_over_minimum(self):
        items = [_cart_item(weight=1)]
        fee = calculate_boxnow_shipping_cost(
            items,
            Decimal("60.00"),
            REGION_ATTICA,
        )
        self.assertEqual(fee, Decimal("0.00"))

    def test_charges_medium_fee_outside_free_threshold(self):
        items = [_cart_item(weight=3, length=12, width=30, height=40)]
        fee = calculate_boxnow_shipping_cost(
            items,
            Decimal("15.00"),
            REGION_ATTICA,
        )
        self.assertEqual(fee, Decimal("2.50"))

    def test_exceeds_weight_limit_above_20kg(self):
        items = [_cart_item(weight=21)]
        self.assertTrue(exceeds_boxnow_weight_limit(items))

    def test_exceeds_when_larger_than_large_locker(self):
        items = [_cart_item(weight=5, length=40, width=50, height=70)]
        self.assertTrue(exceeds_boxnow_weight_limit(items))


@override_settings(
    BOXNOW_FEE_SMALL=Decimal("1.80"),
    BOXNOW_FEE_MEDIUM=Decimal("2.50"),
    BOXNOW_FEE_LARGE=Decimal("3.50"),
    BOXNOW_MAX_WEIGHT_KG="20.0",
    COURIER_FLAT_FEE=Decimal("3.20"),
    FREE_SHIPPING_ORDER_MINIMUM=Decimal("60.00"),
)
class BoxNowDeliveryOptionsTests(SimpleTestCase):
    def test_build_delivery_options_includes_box_now_without_partner_id(self):
        options, _within = build_delivery_options(
            cart_total=Decimal("15.00"),
            postal_code="10563",
            cart=[_cart_item(weight=1)],
        )
        values = [option["value"] for option in options]
        self.assertIn(Order.DELIVERY_METHOD_BOX_NOW, values)
        box_now = next(
            option for option in options
            if option["value"] == Order.DELIVERY_METHOD_BOX_NOW
        )
        self.assertTrue(box_now["requires_locker"])
        self.assertEqual(box_now["fee"], Decimal("1.80"))
        self.assertIn("8×45×60", box_now["description"])
        self.assertIn("20", box_now["description"])

    def test_calculate_courier_fee_for_box_now(self):
        fee = calculate_courier_fee(
            "10563",
            Order.DELIVERY_METHOD_BOX_NOW,
            cart=[_cart_item(weight=1)],
            cart_total=Decimal("15.00"),
        )
        self.assertEqual(fee, Decimal("1.80"))

    def test_box_now_disabled_when_cart_too_heavy(self):
        options, _within = build_delivery_options(
            cart_total=Decimal("15.00"),
            postal_code="10563",
            cart=[_cart_item(weight=21)],
        )
        box_now = next(
            option for option in options
            if option["value"] == Order.DELIVERY_METHOD_BOX_NOW
        )
        self.assertTrue(box_now["disabled"])
        self.assertFalse(box_now["requires_locker"])
        self.assertIn("courier", box_now["unavailable_message"])
        self.assertIn("20", box_now["unavailable_message"])
        self.assertNotIn("ELTA", box_now["unavailable_message"])
        courier = next(
            option for option in options
            if option["value"] == Order.DELIVERY_METHOD_COURIER
        )
        self.assertFalse(courier["disabled"])
        self.assertEqual(courier["fee"], Decimal("3.20"))


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
            weight=Decimal("1.00"),
            length=Decimal("6.00"),
            width=Decimal("20.00"),
            height=Decimal("30.00"),
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


class BoxNowWebhookTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        cls.user = User.objects.create_user(
            email="hook@example.com",
            password="testpass123",
            phone_number="+306900000000",
            city="Αθήνα",
            street="Ερμού",
            street_number="1",
            postal_code="10563",
            latitude=Decimal("37.9755"),
            longitude=Decimal("23.7348"),
        )
        cls.order = Order.objects.create(
            user=cls.user,
            payment_method=Order.PAYMENT_METHOD_CARD,
            status=Order.STATUS_PAID,
            cart_cost=Decimal("10.00"),
            courier_fee=Decimal("1.80"),
            total_cost=Decimal("11.80"),
            delivery_method=Order.DELIVERY_METHOD_BOX_NOW,
            delivery_phone_number="+306900000000",
            delivery_city="Αθήνα",
            delivery_address="Ερμού 1",
            delivery_postal_code="10563",
            delivery_latitude=Decimal("37.9755"),
            delivery_longitude=Decimal("23.7348"),
            boxnow_locker_id="8",
        )

    def test_webhook_updates_event_and_delivered_status(self):
        payload = {
            "specversion": "1.0",
            "type": "gr.boxnow.parcel_event_change",
            "source": "https://boxnow.gr/api/v1/webhooks/1",
            "subject": "111",
            "id": "msg-1",
            "time": "2026-09-01T11:00:00.000Z",
            "datacontenttype": "application/json",
            "datasignature": "",
            "data": {
                "parcelId": "111",
                "parcelState": "delivered",
                "parcelReferenceNumber": "",
                "parcelName": "order",
                "orderNumber": self.order.order_code,
                "event": "delivered",
                "time": "2026-09-01T11:00:00.000Z",
            },
        }
        response = self.client.post(
            "/checkout/boxnow/webhook/",
            data=__import__("json").dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.boxnow_last_event, "delivered")
        self.assertEqual(self.order.status, Order.STATUS_DELIVERED)
        self.assertEqual(self.order.boxnow_parcel_id, "111")
