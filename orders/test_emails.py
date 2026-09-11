from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from newsletter.models import NewsletterSubscriber
from newsletter.services import subscribe_newsletter
from orders.emails import send_order_status_email
from orders.models import Order

User = get_user_model()


class NewsletterSignupTests(TestCase):
    def test_subscribe_newsletter_creates_subscriber(self):
        user = User.objects.create_user(email="news@example.com", password="x")
        created = subscribe_newsletter(email=user.email, user=user)
        self.assertTrue(created)
        self.assertTrue(
            NewsletterSubscriber.objects.filter(email=user.email, is_active=True).exists()
        )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_BASE_URL="http://testserver",
)
class OrderEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="order-mail@example.com",
            password="testpass123",
        )

    def _make_order(self, **kwargs):
        defaults = {
            "user": self.user,
            "payment_method": Order.PAYMENT_METHOD_COD,
            "status": Order.STATUS_NEW,
            "cart_cost": Decimal("10.00"),
            "courier_fee": Decimal("2.00"),
            "total_cost": Decimal("12.00"),
            "delivery_method": Order.DELIVERY_METHOD_COURIER,
            "delivery_phone_number": "+306900000000",
            "delivery_city": "Αθήνα",
            "delivery_address": "Ερμού 1",
            "delivery_postal_code": "10563",
            "delivery_latitude": Decimal("37.9755"),
            "delivery_longitude": Decimal("23.7348"),
        }
        defaults.update(kwargs)
        return Order.objects.create(**defaults)

    def test_new_order_create_does_not_email_until_checkout_sends(self):
        with patch("orders.signals.send_order_status_email") as mock_send:
            self._make_order()
        mock_send.assert_not_called()

    def test_status_change_sends_update_email(self):
        order = self._make_order(status=Order.STATUS_NEW)
        mail.outbox.clear()
        order.status = Order.STATUS_DELIVERED
        order.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(order.public_code_display, mail.outbox[0].subject)

    def test_send_order_status_email_contains_details(self):
        order = self._make_order()
        mail.outbox.clear()
        send_order_status_email(order, is_new=True)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("ΠΑΡΑΔΟΣΗ", body)
        self.assertIn("Σύνολο πληρωμής", body)
        self.assertIn("Παρακάτω θα βρείτε όλα τα στοιχεία", body)
        self.assertIn("Σας ευχαριστούμε θερμά που προτιμήσατε", body)
        self.assertIn("210 6038727", body)
        self.assertIn("697 7927008", body)
        self.assertIn("ακύρωση ή μετατροπή", body)

    def test_new_cod_email_status_is_registered_not_paid(self):
        order = self._make_order()
        mail.outbox.clear()
        send_order_status_email(order, is_new=True)
        body = mail.outbox[0].body
        self.assertIn("Καταχωρήθηκε", body)
        self.assertNotIn("Πληρωμένη", body)
        self.assertIn("αντικαταβολή", body)

    def test_new_cod_email_states_payment_is_due_on_delivery(self):
        order = self._make_order()
        mail.outbox.clear()
        send_order_status_email(order, is_new=True)
        body = mail.outbox[0].body
        self.assertIn("Τρόπος πληρωμής: Αντικαταβολή", body)
        self.assertIn("Κατάσταση πληρωμής: Αναμένεται πληρωμή κατά την παράδοση", body)

    def test_new_card_email_states_the_order_is_already_paid(self):
        order = self._make_order(
            payment_method=Order.PAYMENT_METHOD_CARD,
            stripe_payment_intent_id="pi_test_email",
        )
        mail.outbox.clear()
        send_order_status_email(order, is_new=True)
        body = mail.outbox[0].body
        self.assertIn("Τρόπος πληρωμής: Κάρτα", body)
        self.assertIn("Κατάσταση πληρωμής: Εξοφλήθηκε με κάρτα", body)
        self.assertNotIn("Αναμένεται πληρωμή", body)

    def test_delivered_cod_email_reports_the_money_as_collected(self):
        order = self._make_order()
        mail.outbox.clear()
        order.status = Order.STATUS_DELIVERED
        order.collected_payment_method = Order.PAYMENT_METHOD_CARD
        order.save()
        body = mail.outbox[0].body
        # Collected by card at the door, still recorded as αντικαταβολή.
        self.assertIn("Τρόπος πληρωμής: Αντικαταβολή", body)
        self.assertIn("Κατάσταση πληρωμής: Εξοφλήθηκε", body)

    def test_cancellation_request_email_keeps_the_payment_visible(self):
        order = self._make_order(
            payment_method=Order.PAYMENT_METHOD_CARD,
            stripe_payment_intent_id="pi_test_cancel",
        )
        mail.outbox.clear()
        order.status = Order.STATUS_CANCELLATION_REQUESTED
        order.save()
        body = mail.outbox[0].body
        self.assertIn("Αίτημα ακύρωσης", body)
        self.assertIn("Κατάσταση πληρωμής: Εξοφλήθηκε με κάρτα", body)

    def test_in_progress_alias_does_not_email(self):
        order = self._make_order(status=Order.STATUS_NEW)
        mail.outbox.clear()
        order.status = Order.STATUS_PAID
        order.save()
        self.assertEqual(len(mail.outbox), 0)

    def test_delivered_email_uses_delivered_subject_and_items(self):
        from orders.models import OrderItem
        from products.models import AnimalType, Category, Company, Product, ProductVariant

        company = Company.objects.create(name="BRAND", code="BRD")
        animal = AnimalType.objects.create(name="Dog", slug="dog-mail")
        category = Category.objects.create(name="Dry Food", slug="dry-mail")
        product = Product.objects.create(
            name="Adult Mix",
            company=company,
            animal_type=animal,
            category=category,
            is_active=True,
        )
        variant = ProductVariant.objects.create(
            product=product,
            weight=Decimal("2.00"),
            price=Decimal("10.00"),
        )
        order = self._make_order()
        OrderItem.objects.create(
            order=order,
            product_variant=variant,
            quantity=2,
            price_at_purchase=Decimal("10.00"),
        )
        mail.outbox.clear()
        order.status = Order.STATUS_DELIVERED
        order.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("παραδόθηκε", mail.outbox[0].subject)
        self.assertIn("BRAND Adult Mix", mail.outbox[0].body)
        self.assertIn("2×", mail.outbox[0].body)
