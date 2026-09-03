from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from administration.models import AdministrationUser
from administration.permissions import user_is_administration_user
from orders.models import Order
from products.models import AnimalType, Category, Company, Product, ProductVariant


class AdministrationAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="steliospatros@gmail.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="test-pass-123",
        )
        AdministrationUser.objects.get_or_create(
            email="steliospatros@gmail.com",
            defaults={"is_active": True},
        )

    def test_allow_list_grants_access(self):
        self.assertTrue(user_is_administration_user(self.admin_user))
        self.assertFalse(user_is_administration_user(self.other_user))

    def test_inactive_administration_user_is_denied(self):
        AdministrationUser.objects.filter(email="steliospatros@gmail.com").update(is_active=False)
        self.assertFalse(user_is_administration_user(self.admin_user))

    def test_administration_hub_requires_allow_list(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("administration:hub"))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:hub"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Προϊόντα")

    def test_account_hub_shows_management_link_only_for_admins(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("accounts:hub"))
        self.assertNotContains(response, "Διαχείριση")

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("accounts:hub"))
        self.assertContains(response, "Διαχείριση")


class AdministrationInventoryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="steliospatros@gmail.com",
            password="test-pass-123",
        )
        AdministrationUser.objects.get_or_create(
            email="steliospatros@gmail.com",
            defaults={"is_active": True},
        )

        self.company = Company.objects.create(name="Alpha Co", code="ALP")
        self.category = Category.objects.create(name="Dry Food")
        self.dog = AnimalType.objects.create(name="Dog", slug="dog")
        self.cat = AnimalType.objects.create(name="Cat", slug="cat")

        product_dog = Product.objects.create(
            name="Adult Mix",
            company=self.company,
            category=self.category,
            animal_type=self.dog,
        )
        product_cat = Product.objects.create(
            name="Kitten Mix",
            company=self.company,
            category=self.category,
            animal_type=self.cat,
        )
        ProductVariant.objects.create(product=product_dog, weight=2, price=10, stock=5)
        ProductVariant.objects.create(product=product_dog, weight=10, price=40, stock=12)
        ProductVariant.objects.create(product=product_cat, weight=1, price=8, stock=3)

    def test_inventory_lists_variants_separately_and_grouped(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:inventory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha Co")
        self.assertContains(response, "Dry Food")
        self.assertContains(response, "Dog")
        self.assertContains(response, "Cat")
        self.assertContains(response, "Adult Mix")
        self.assertContains(response, "Kitten Mix")
        self.assertContains(response, "Απόθεμα")
        self.assertContains(response, "12")
        self.assertContains(response, "3")

    def test_favourites_page_lists_products_by_score(self):
        product = Product.objects.get(name="Adult Mix")
        from products.models import Favourite

        Favourite.objects.filter(product=product).update(
            score=47,
            purchase_count=5,
            wishlist_count=4,
            view_count=12,
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:favourites"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Adult Mix")
        self.assertContains(response, "47")
        self.assertContains(response, "Favourites")

    def test_adjust_stock_add_and_remove(self):
        variant = ProductVariant.objects.get(product__name="Adult Mix", weight=2)
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"delta": "5"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 10)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"delta": "-3"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 7)

    def test_stock_zero_sets_out_of_stock_for_available_now(self):
        variant = ProductVariant.objects.get(product__name="Adult Mix", weight=2)
        variant.availability = ProductVariant.AVAILABILITY_AVAILABLE_NOW
        variant.stock = 2
        variant.save()
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"delta": "-2"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 0)
        self.assertEqual(variant.availability, ProductVariant.AVAILABILITY_OUT_OF_STOCK)

    def test_product_pause_hides_from_storefront(self):
        product = Product.objects.get(name="Adult Mix")
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("administration:toggle_product_pause", args=[product.pk]),
            {"pause": "1"},
        )
        product.refresh_from_db()
        self.assertFalse(product.is_active)

        self.client.post(
            reverse("administration:toggle_product_pause", args=[product.pk]),
            {"pause": "0"},
        )
        product.refresh_from_db()
        self.assertTrue(product.is_active)

    def test_non_admin_cannot_adjust_stock(self):
        User = get_user_model()
        other = User.objects.create_user(email="other@example.com", password="x")
        variant = ProductVariant.objects.first()
        self.client.force_login(other)
        response = self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"delta": "10"},
        )
        self.assertEqual(response.status_code, 403)


class AdministrationOrdersPanelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="steliospatros@gmail.com",
            password="test-pass-123",
        )
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="test-pass-123",
        )
        AdministrationUser.objects.get_or_create(
            email="steliospatros@gmail.com",
            defaults={"is_active": True},
        )
        Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_CARD,
            status=Order.STATUS_CANCELLATION_REQUESTED,
            cart_cost=10,
            total_cost=10,
            delivery_method=Order.DELIVERY_METHOD_COURIER,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Οδός 1",
            delivery_postal_code="11111",
            delivery_latitude=37.98,
            delivery_longitude=23.72,
            stripe_payment_intent_id="pi_test_123",
            cancellation_requested_at=timezone.now(),
        )

    def test_orders_page_lists_cancellation_requests(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:orders"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Αιτήματα ακύρωσης")
        self.assertContains(response, "customer@example.com")

    def test_payments_page_loads(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:payments"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Παραλήφθηκαν")
        self.assertContains(response, "Αναμένονται")
        self.assertContains(response, "Μετρητά")
        self.assertContains(response, "Κάρτα")

    def test_orders_filter_by_user(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("administration:orders"),
            {"user": "customer@example.com", "period": "month"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "customer@example.com")


class AdministrationDeliveriesPanelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="steliospatros@gmail.com",
            password="test-pass-123",
            first_name="Admin",
            last_name="User",
        )
        self.courier_user = User.objects.create_user(
            email="courier@example.com",
            password="test-pass-123",
        )
        self.customer = User.objects.create_user(
            email="delivery-customer@example.com",
            password="test-pass-123",
            first_name="Maria",
            last_name="Papadopoulos",
        )
        AdministrationUser.objects.get_or_create(
            email="steliospatros@gmail.com",
            defaults={"is_active": True, "role": AdministrationUser.ROLE_ADMIN},
        )
        AdministrationUser.objects.create(
            email="courier@example.com",
            is_active=True,
            role=AdministrationUser.ROLE_COURIER,
        )
        self.old_order = Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=10,
            total_cost=12,
            courier_fee=2,
            delivery_method=Order.DELIVERY_METHOD_COURIER,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Ερμού 1",
            delivery_postal_code="10563",
            delivery_latitude=37.98,
            delivery_longitude=23.72,
        )
        self.new_order = Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=20,
            total_cost=22,
            courier_fee=2,
            delivery_method=Order.DELIVERY_METHOD_COMPANY,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Σταδίου 10",
            delivery_postal_code="10564",
            delivery_latitude=37.98,
            delivery_longitude=23.72,
        )
        Order.objects.filter(pk=self.old_order.pk).update(
            order_date=timezone.now() - timedelta(days=2)
        )
        self.old_order.refresh_from_db()

    def test_hub_lists_deliveries_link(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:hub"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Παραδόσεις")

    def test_pending_queue_groups_company_first(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:deliveries"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Παραδόθηκε")
        self.assertContains(response, "Παράδοση από την εταιρία (εντός Αθηνών)")
        self.assertContains(response, "BOX NOW")
        groups = response.context["delivery_groups"]
        self.assertEqual([group["key"] for group in groups], ["company", "courier", "boxnow"])
        company_addresses = [
            row["delivery_address_display"] for row in groups[0]["orders"]
        ]
        courier_addresses = [
            row["delivery_address_display"] for row in groups[1]["orders"]
        ]
        self.assertTrue(any("Σταδίου 10" in address for address in company_addresses))
        self.assertTrue(any("Ερμού 1" in address for address in courier_addresses))

    def test_delivered_orders_use_red_button(self):
        self.old_order.status = Order.STATUS_DELIVERED
        self.old_order.save(update_fields=["status"])
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("administration:deliveries"),
            {"show": "delivered"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bg-red-700")
        self.assertContains(response, "Δεν παραδόθηκε")
        self.assertContains(response, "bg-red-50")

    def test_mark_delivered_and_undo(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("administration:mark_delivery", args=[self.old_order.pk]),
            {"delivered": "1", "show": "pending", "collected_payment": "cash_on_delivery"},
        )
        self.assertRedirects(
            response,
            reverse("administration:deliveries") + "?show=pending",
        )
        self.old_order.refresh_from_db()
        self.assertEqual(self.old_order.status, Order.STATUS_DELIVERED)

        self.client.post(
            reverse("administration:mark_delivery", args=[self.old_order.pk]),
            {"delivered": "0", "show": "delivered"},
        )
        self.old_order.refresh_from_db()
        self.assertEqual(self.old_order.status, Order.STATUS_NEW)

    def test_courier_can_open_deliveries_but_not_orders(self):
        self.client.force_login(self.courier_user)
        response = self.client.get(reverse("administration:deliveries"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Προς παράδοση")

        response = self.client.get(reverse("administration:orders"))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("administration:hub"))
        self.assertRedirects(response, reverse("administration:deliveries"))

    def test_courier_sees_deliveries_on_account_hub(self):
        self.client.force_login(self.courier_user)
        response = self.client.get(reverse("accounts:hub"))
        self.assertContains(response, "Παραδόσεις")
        self.assertNotContains(response, "Διαχείριση")

    def test_mark_delivered_sends_email(self):
        from django.core import mail
        from django.test import override_settings

        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mail.outbox.clear()
            self.client.force_login(self.admin_user)
            self.client.post(
                reverse("administration:mark_delivery", args=[self.old_order.pk]),
                {"delivered": "1", "collected_payment": "card"},
            )
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn("παραδόθηκε", mail.outbox[0].subject)

    @override_settings(GOOGLE_MAPS_API_KEY="test-maps-key")
    def test_delivery_row_includes_map_thumbnail(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:deliveries"))
        self.assertContains(response, "maps.googleapis.com/maps/api/staticmap")
        self.assertContains(response, "markers=color:0x42746c")
        self.assertContains(response, "popovertarget")
        self.assertContains(response, "google.com/maps?q=")

    def test_cod_delivery_requires_cash_or_card(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("administration:mark_delivery", args=[self.old_order.pk]),
            {"delivered": "1", "show": "pending"},
        )
        self.assertRedirects(
            response,
            reverse("administration:deliveries") + "?show=pending",
        )
        self.old_order.refresh_from_db()
        self.assertEqual(self.old_order.status, Order.STATUS_NEW)
        self.assertEqual(self.old_order.collected_payment_method, "")

    def test_boxnow_delivery_is_card_only(self):
        boxnow = Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_CARD,
            status=Order.STATUS_PAID,
            cart_cost=15,
            total_cost=15,
            courier_fee=0,
            delivery_method=Order.DELIVERY_METHOD_BOX_NOW,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Locker",
            delivery_postal_code="10563",
            stripe_payment_intent_id="pi_boxnow",
        )
        self.assertFalse(boxnow.needs_collection_declaration())
        self.client.force_login(self.admin_user)
        self.client.post(
            reverse("administration:mark_delivery", args=[boxnow.pk]),
            {"delivered": "1", "show": "pending"},
        )
        boxnow.refresh_from_db()
        self.assertEqual(boxnow.status, Order.STATUS_DELIVERED)
        self.assertEqual(boxnow.collected_payment_method, Order.PAYMENT_METHOD_CARD)


class PaymentsDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="steliospatros@gmail.com",
            password="test-pass-123",
        )
        AdministrationUser.objects.get_or_create(
            email="steliospatros@gmail.com",
            defaults={"is_active": True, "role": AdministrationUser.ROLE_ADMIN},
        )
        self.customer = User.objects.create_user(
            email="pay@example.com",
            password="x",
        )
        defaults = dict(
            user=self.customer,
            delivery_method=Order.DELIVERY_METHOD_COMPANY,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Ερμού 1",
            delivery_postal_code="10563",
            delivery_latitude=37.98,
            delivery_longitude=23.72,
        )
        Order.objects.create(
            **defaults,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=10,
            courier_fee=0,
            total_cost=10,
        )
        collected = Order.objects.create(
            **defaults,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_DELIVERED,
            cart_cost=20,
            courier_fee=0,
            total_cost=20,
            collected_payment_method=Order.PAYMENT_METHOD_COD,
            delivered_at=timezone.now(),
        )
        Order.objects.create(
            **defaults,
            payment_method=Order.PAYMENT_METHOD_CARD,
            status=Order.STATUS_PAID,
            cart_cost=30,
            courier_fee=0,
            total_cost=30,
            stripe_payment_intent_id="pi_dash_1",
        )
        self.collected = collected

    def test_dashboard_splits_received_and_expected(self):
        from decimal import Decimal

        from administration.money import build_payments_dashboard_context
        from administration.order_queries import PERIOD_DAY

        context = build_payments_dashboard_context(
            period=PERIOD_DAY,
            anchor_date=timezone.localdate(),
        )
        self.assertEqual(context["received"]["cash"], Decimal("20.00"))
        self.assertEqual(context["received"]["card"], Decimal("30.00"))
        self.assertEqual(context["expected"]["cash"], Decimal("10.00"))
        self.assertEqual(context["expected"]["card"], Decimal("0.00"))

    def test_payments_page_shows_totals(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("administration:payments"),
            {"period": "day", "date": timezone.localdate().isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "20,00")
        self.assertContains(response, "30,00")
        self.assertContains(response, "10,00")
