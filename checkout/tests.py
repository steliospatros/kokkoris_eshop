from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from checkout.delivery import build_delivery_options
from checkout.helpers import (
    CHECKOUT_STEP_ADDRESS,
    CHECKOUT_STEP_DELIVERY,
    CHECKOUT_STEP_PAYMENT,
    SESSION_KEY,
    build_checkout_steps,
)
from checkout.stripe_service import (
    StripePaymentError,
    decimal_to_stripe_cents,
    find_order_for_payment_intent,
    verify_card_payment_intent,
)
from orders.models import Order
from products.models import AnimalType, Category, Company, Product, ProductVariant

User = get_user_model()


class CheckoutStepsTests(TestCase):
    def test_address_step_active_on_first_visit(self):
        steps = build_checkout_steps(CHECKOUT_STEP_ADDRESS)
        self.assertEqual(steps[0]["state"], "active")
        self.assertEqual(steps[1]["state"], "locked")
        self.assertEqual(steps[2]["state"], "locked")

    def test_delivery_step_after_address_saved(self):
        checkout_data = {
            "address": "Ερμού 1",
            "city": "Αθήνα",
            "postal_code": "10563",
        }
        steps = build_checkout_steps(CHECKOUT_STEP_DELIVERY, checkout_data)
        self.assertEqual(steps[0]["state"], "completed")
        self.assertEqual(steps[1]["state"], "active")
        self.assertEqual(steps[2]["state"], "locked")
        self.assertIn("Ερμού 1", steps[0]["summary"])

    def test_payment_step_after_delivery_saved(self):
        checkout_data = {
            "address": "Ερμού 1",
            "city": "Αθήνα",
            "postal_code": "10563",
            "delivery_method": Order.DELIVERY_METHOD_COMPANY,
        }
        steps = build_checkout_steps(CHECKOUT_STEP_PAYMENT, checkout_data)
        self.assertEqual(steps[0]["state"], "completed")
        self.assertEqual(steps[1]["state"], "completed")
        self.assertEqual(steps[2]["state"], "active")


class CheckoutDeliveryViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="checkout@example.com",
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
        self.client.force_login(self.user)
        session = self.client.session
        session[SESSION_KEY] = {
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
            reverse("cart:add"),
            {"variant_id": self.variant.pk, "quantity": 1},
        )

    def test_delivery_page_renders_step_list(self):
        response = self.client.get(reverse("checkout:delivery"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Διεύθυνση παράδοσης")
        self.assertContains(response, "Τρόπος αποστολής")
        self.assertContains(response, "Τρόπος πληρωμής")
        self.assertContains(response, "Παράδοση από υπάλληλο")

    def test_delivery_post_advances_to_payment(self):
        response = self.client.post(
            reverse("checkout:delivery"),
            {"delivery_method": Order.DELIVERY_METHOD_COMPANY},
        )
        self.assertRedirects(response, reverse("checkout:payment"))
        data = self.client.session[SESSION_KEY]
        self.assertEqual(data["delivery_method"], Order.DELIVERY_METHOD_COMPANY)

    def test_payment_page_renders_payment_options(self):
        session = self.client.session
        session[SESSION_KEY]["delivery_method"] = Order.DELIVERY_METHOD_COURIER
        session[SESSION_KEY]["courier_fee"] = "2.00"
        session.save()
        response = self.client.get(reverse("checkout:payment"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Επιλογή τρόπου πληρωμής")
        self.assertContains(response, "Αντικαταβολή")
        self.assertContains(response, "Πληρωμή μέσω κάρτας")
        self.assertContains(response, "stripe-card-element")


class DeliveryOptionsTests(TestCase):
    def test_urban_area_includes_company_delivery(self):
        options, within = build_delivery_options(
            cart_total=Decimal("25.00"),
            postal_code="10563",
            cart=[],
        )
        self.assertTrue(within)
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0]["value"], Order.DELIVERY_METHOD_COMPANY)
        self.assertFalse(options[0]["disabled"])

    def test_outlying_area_company_disabled_courier_only_selectable(self):
        options, within = build_delivery_options(
            cart_total=Decimal("25.00"),
            postal_code="19009",
            cart=[],
        )
        self.assertFalse(within)
        self.assertEqual(len(options), 2)
        self.assertTrue(options[0]["disabled"])
        self.assertIn("υπάλληλο", options[0]["unavailable_message"])
        self.assertFalse(options[1]["disabled"])
        self.assertEqual(options[1]["value"], Order.DELIVERY_METHOD_COURIER)
        self.assertEqual(options[1]["label"], "Αποστολή μέσω ELTA")


class StripeServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="stripe@example.com",
            password="testpass123",
        )

    @patch("checkout.stripe_service.retrieve_payment_intent")
    def test_verify_rejects_amount_mismatch(self, mock_retrieve):
        mock_retrieve.return_value = MagicMock(
            status="succeeded",
            amount=999,
            metadata={
                "user_id": str(self.user.pk),
                "checkout_session_key": "sess-1",
            },
        )
        with self.assertRaises(StripePaymentError) as ctx:
            verify_card_payment_intent(
                "pi_test",
                user=self.user,
                checkout_session_key="sess-1",
                expected_total=Decimal("12.00"),
            )
        self.assertIn("ποσό", str(ctx.exception).lower())

    def test_find_order_for_payment_intent(self):
        order = Order.objects.create(
            user=self.user,
            payment_method=Order.PAYMENT_METHOD_CARD,
            status=Order.STATUS_PAID,
            cart_cost=Decimal("10.00"),
            courier_fee=Decimal("2.00"),
            total_cost=Decimal("12.00"),
            stripe_payment_intent_id="pi_existing",
            delivery_method=Order.DELIVERY_METHOD_COURIER,
            delivery_phone_number="+306900000000",
            delivery_city="Αθήνα",
            delivery_address="Ερμού 1",
            delivery_postal_code="10563",
            delivery_latitude=Decimal("37.9755"),
            delivery_longitude=Decimal("23.7348"),
        )
        found = find_order_for_payment_intent("pi_existing", user=self.user)
        self.assertEqual(found, order)

    def test_decimal_to_stripe_cents(self):
        self.assertEqual(decimal_to_stripe_cents(Decimal("12.34")), 1234)


class CardCheckoutViewTests(CheckoutDeliveryViewTests):
    """Reuse cart + session setup from delivery view tests."""

    def setUp(self):
        super().setUp()
        session = self.client.session
        session[SESSION_KEY]["delivery_method"] = Order.DELIVERY_METHOD_COURIER
        session[SESSION_KEY]["courier_fee"] = "2.00"
        session.save()

    @patch("checkout.views.stripe_payments_enabled", return_value=True)
    @patch("checkout.views._finalize_card_checkout")
    def test_card_post_redirects_to_confirmation(self, mock_finalize, _mock_enabled):
        mock_order = MagicMock(id=42)
        mock_finalize.return_value = mock_order
        response = self.client.post(
            reverse("checkout:payment"),
            {
                "payment_method": Order.PAYMENT_METHOD_CARD,
                "stripe_payment_intent_id": "pi_test_123",
            },
        )
        self.assertRedirects(
            response,
            reverse("checkout:confirmation", kwargs={"order_id": 42}),
            fetch_redirect_response=False,
        )
        mock_finalize.assert_called_once()

    @override_settings(STRIPE_PUBLISHABLE_KEY="pk_test", STRIPE_SECRET_KEY="sk_test")
    @patch("checkout.views.stripe_payments_enabled", return_value=True)
    @patch("checkout.views._finalize_card_checkout")
    def test_3ds_return_creates_order(self, mock_finalize, _mock_enabled):
        mock_order = MagicMock(id=99)
        mock_finalize.return_value = mock_order
        response = self.client.get(
            reverse("checkout:payment"),
            {
                "redirect_status": "succeeded",
                "payment_intent": "pi_3ds_return",
            },
        )
        self.assertRedirects(
            response,
            reverse("checkout:confirmation", kwargs={"order_id": 99}),
            fetch_redirect_response=False,
        )
        mock_finalize.assert_called_once()
