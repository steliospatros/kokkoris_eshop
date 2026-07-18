from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from orders.models import Order
from orders.refunds import order_requires_stripe_refund
from orders.stock import release_stock_for_order

User = get_user_model()


class CancellationRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="cancel@example.com",
            password="testpass123",
        )
        cls.paid_card_order = Order.objects.create(
            user=cls.user,
            payment_method=Order.PAYMENT_METHOD_CARD,
            status=Order.STATUS_PAID,
            cart_cost=Decimal("10.00"),
            courier_fee=Decimal("2.00"),
            total_cost=Decimal("12.00"),
            stripe_payment_intent_id="pi_test_paid",
            delivery_method=Order.DELIVERY_METHOD_COURIER,
            delivery_phone_number="+306900000000",
            delivery_city="Αθήνα",
            delivery_address="Ερμού 1",
            delivery_postal_code="10563",
            delivery_latitude=Decimal("37.9755"),
            delivery_longitude=Decimal("23.7348"),
        )
        cls.cod_order = Order.objects.create(
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

    def test_paid_card_order_can_request_cancellation(self):
        self.assertTrue(self.paid_card_order.can_request_cancellation())
        self.assertTrue(self.paid_card_order.can_customer_initiate_cancel())

    def test_paid_card_cancel_submits_request_not_immediate_cancel(self):
        response = self.client.post(
            reverse("orders:cancel_order", kwargs={"order_id": self.paid_card_order.id})
        )
        self.assertRedirects(
            response,
            reverse("orders:detail", kwargs={"order_id": self.paid_card_order.id}),
        )
        self.paid_card_order.refresh_from_db()
        self.assertEqual(
            self.paid_card_order.status,
            Order.STATUS_CANCELLATION_REQUESTED,
        )
        self.assertIsNotNone(self.paid_card_order.cancellation_requested_at)

    def test_cod_order_cancels_immediately(self):
        with patch("orders.views.release_stock_for_order") as mock_release:
            response = self.client.post(
                reverse("orders:cancel_order", kwargs={"order_id": self.cod_order.id})
            )
            self.assertRedirects(
                response,
                reverse("orders:detail", kwargs={"order_id": self.cod_order.id}),
            )
            self.cod_order.refresh_from_db()
            self.assertEqual(self.cod_order.status, Order.STATUS_CANCELLED)
            mock_release.assert_called_once()

    def test_order_requires_stripe_refund(self):
        self.assertTrue(order_requires_stripe_refund(self.paid_card_order))

    @patch("orders.admin.create_stripe_refund_for_order")
    @patch("orders.admin.release_stock_for_order")
    def test_admin_refund_action_cancels_order(self, mock_release, mock_refund):
        from orders.admin import process_stripe_refund_and_cancel

        mock_refund.return_value = MagicMock(id="re_test_refund")
        self.paid_card_order.status = Order.STATUS_CANCELLATION_REQUESTED
        self.paid_card_order.cancellation_requested_at = timezone.now()
        self.paid_card_order.save()

        class FakeRequest:
            pass

        request = FakeRequest()
        with patch("orders.admin.messages") as mock_messages:
            process_stripe_refund_and_cancel(None, request, [self.paid_card_order])

        self.paid_card_order.refresh_from_db()
        self.assertEqual(self.paid_card_order.status, Order.STATUS_CANCELLED)
        self.assertEqual(self.paid_card_order.stripe_refund_id, "re_test_refund")
        mock_release.assert_called_once()
        mock_messages.success.assert_called_once()
