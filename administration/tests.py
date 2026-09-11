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

    def test_inventory_uses_full_product_name_and_image_slot(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:inventory"))
        self.assertContains(response, "Alpha Co Adult Mix 2 kg")
        self.assertContains(response, "inventory-row__photo")

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
            {"stock": "10"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 10)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"stock": "7"},
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
            {"stock": "0"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 0)
        self.assertEqual(variant.availability, ProductVariant.AVAILABILITY_OUT_OF_STOCK)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"stock": "6"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 6)
        self.assertEqual(variant.availability, ProductVariant.AVAILABILITY_AVAILABLE_NOW)

    def test_status_buttons_set_on_order_and_unavailable(self):
        variant = ProductVariant.objects.get(product__name="Adult Mix", weight=2)
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"stock": str(variant.stock), "availability": "on_order"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.availability, ProductVariant.AVAILABILITY_ON_ORDER)
        self.assertEqual(variant.stock, 0)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"stock": "4", "availability": "out_of_stock"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 4)
        self.assertEqual(variant.availability, ProductVariant.AVAILABILITY_OUT_OF_STOCK)

        self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"stock": "4", "availability": "available_now"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.availability, ProductVariant.AVAILABILITY_AVAILABLE_NOW)

    def test_inventory_page_has_status_controls(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:inventory"))
        self.assertContains(response, "Άμεσα διαθέσιμο")
        self.assertContains(response, "Κατόπιν παραγγελίας")
        self.assertContains(response, "Προσωρινά μη διαθέσιμο")
        self.assertContains(response, "Τεμάχια καταστήματος")
        self.assertContains(response, "απόθεμα προμηθευτή")
        self.assertContains(response, 'name="stock"')

    def test_product_pause_hides_from_storefront(self):
        from products.catalog import get_catalog_queryset

        product = Product.objects.get(name="Adult Mix")
        adult_variant = ProductVariant.objects.get(product=product, weight=2)
        kitten_variant = ProductVariant.objects.get(product__name="Kitten Mix")
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("administration:toggle_product_pause", args=[product.pk]),
            {"pause": "1"},
        )
        product.refresh_from_db()
        self.assertFalse(product.is_active)
        self.assertFalse(get_catalog_queryset().filter(pk=product.pk).exists())

        inventory = self.client.get(reverse("administration:inventory"))
        self.assertContains(inventory, "Adult Mix")
        self.assertContains(inventory, "Κρυφά από το e-shop")
        self.assertContains(inventory, "Εμφάνιση ξανά στο e-shop")
        html = inventory.content.decode()
        self.assertLess(
            html.find(f'id="variant-{kitten_variant.pk}"'),
            html.find("Κρυφά από το e-shop"),
        )
        self.assertLess(
            html.find("Κρυφά από το e-shop"),
            html.find(f'id="variant-{adult_variant.pk}"'),
        )

        self.client.post(
            reverse("administration:toggle_product_pause", args=[product.pk]),
            {"pause": "0"},
        )
        product.refresh_from_db()
        self.assertTrue(product.is_active)
        self.assertTrue(get_catalog_queryset().filter(pk=product.pk).exists())
        restored = self.client.get(reverse("administration:inventory"))
        self.assertNotContains(restored, "Κρυφά από το e-shop")
        self.assertContains(restored, "Απόκρυψη από το e-shop")

    def test_non_admin_cannot_adjust_stock(self):
        User = get_user_model()
        other = User.objects.create_user(email="other@example.com", password="x")
        variant = ProductVariant.objects.first()
        self.client.force_login(other)
        response = self.client.post(
            reverse("administration:adjust_stock", args=[variant.pk]),
            {"stock": "10"},
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
            delivery_method=Order.DELIVERY_METHOD_COMPANY,
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
        self.assertEqual(response.context["delivery_filter"], "company")

    def test_orders_default_hides_courier_orders(self):
        Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=8,
            total_cost=8,
            delivery_method=Order.DELIVERY_METHOD_COURIER,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Courier Street 9",
            delivery_postal_code="11111",
        )
        self.client.force_login(self.admin_user)
        default_view = self.client.get(reverse("administration:orders"))
        self.assertNotContains(default_view, "Courier Street 9")
        all_view = self.client.get(
            reverse("administration:orders"),
            {"delivery": "all"},
        )
        self.assertContains(all_view, "Courier Street 9")

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

    def test_orders_page_has_admin_actions(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:orders"))
        self.assertContains(response, "Καταχώρηση είσπραξης")
        self.assertContains(response, "Ακύρωση παραγγελίας")
        self.assertContains(response, "Λόγος ακύρωσης")
        self.assertContains(response, "Καταχώρηση")

    def test_admin_cancel_requires_reason(self):
        order = Order.objects.filter(user=self.customer).first()
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("administration:update_order", args=[order.pk]),
            {"action": "cancel", "cancellation_reason": "  "},
        )
        self.assertRedirects(response, reverse("administration:orders"))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLATION_REQUESTED)
        self.assertEqual(order.cancellation_reason, "")

    def test_admin_cancel_saves_reason_emails_and_shows_on_history(self):
        from django.core import mail
        from django.test import override_settings

        order = Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=10,
            total_cost=10,
            delivery_method=Order.DELIVERY_METHOD_COMPANY,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Σταδίου 8",
            delivery_postal_code="10564",
        )
        reason = "Το προϊόν δεν είναι διαθέσιμο στο απόθεμα."
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mail.outbox.clear()
            self.client.force_login(self.admin_user)
            self.client.post(
                reverse("administration:update_order", args=[order.pk]),
                {"action": "cancel", "cancellation_reason": reason},
            )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)
        self.assertEqual(order.cancellation_reason, reason)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("ακυρώθηκε", mail.outbox[0].subject)
        self.assertIn(reason, mail.outbox[0].body)

        self.client.force_login(self.customer)
        history = self.client.get(reverse("accounts:orders"))
        self.assertContains(history, reason)
        detail = self.client.get(reverse("orders:detail", args=[order.pk]))
        self.assertContains(detail, reason)

    def test_admin_cancel_returns_items_to_stock(self):
        company = Company.objects.create(name="Stock Co", code="STK")
        animal = AnimalType.objects.create(name="Dog", slug="dog-cancel-stock")
        category = Category.objects.create(name="Dry", slug="dry-cancel-stock")
        product = Product.objects.create(
            name="Stock Food",
            company=company,
            animal_type=animal,
            category=category,
            is_active=True,
        )
        variant = ProductVariant.objects.create(
            product=product,
            weight=2,
            price=10,
            stock=3,
            availability=ProductVariant.AVAILABILITY_AVAILABLE_NOW,
        )
        order = Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=20,
            total_cost=20,
            delivery_method=Order.DELIVERY_METHOD_COMPANY,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Πατησίων 20",
            delivery_postal_code="10432",
        )
        from orders.models import OrderItem

        OrderItem.objects.create(
            order=order,
            product_variant=variant,
            quantity=2,
            price_at_purchase=10,
        )
        self.client.force_login(self.admin_user)
        self.client.post(
            reverse("administration:update_order", args=[order.pk]),
            {"action": "cancel", "cancellation_reason": "Έλλειψη αποθέματος προμηθευτή."},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 5)

    def test_admin_can_mark_paid_and_change_status(self):
        order = Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_COD,
            status=Order.STATUS_NEW,
            cart_cost=10,
            total_cost=10,
            delivery_method=Order.DELIVERY_METHOD_COMPANY,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Ακαδημίας 5",
            delivery_postal_code="10671",
        )
        self.client.force_login(self.admin_user)
        self.client.post(
            reverse("administration:update_order", args=[order.pk]),
            {"action": "mark_paid", "payment_method": "card"},
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)
        # Collected by card at the door, but still an αντικαταβολή order.
        self.assertEqual(order.payment_method, Order.PAYMENT_METHOD_COD)
        self.assertEqual(order.collected_payment_method, Order.PAYMENT_METHOD_CARD)

        self.client.post(
            reverse("administration:update_order", args=[order.pk]),
            {"action": "set_status", "status": "delivered"},
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_DELIVERED)

    def test_stripe_paid_order_cannot_be_re_declared_as_unpaid(self):
        order = Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_CARD,
            status=Order.STATUS_NEW,
            cart_cost=10,
            total_cost=10,
            delivery_method=Order.DELIVERY_METHOD_COURIER,
            delivery_phone_number="6912345678",
            delivery_city="Αθήνα",
            delivery_address="Ακαδημίας 5",
            delivery_postal_code="10671",
            stripe_payment_intent_id="pi_locked",
            collected_payment_method=Order.PAYMENT_METHOD_CARD,
        )
        self.client.force_login(self.admin_user)
        self.client.post(
            reverse("administration:update_order", args=[order.pk]),
            {"action": "mark_paid", "payment_method": "cash_on_delivery"},
        )
        order.refresh_from_db()
        self.assertEqual(order.payment_method, Order.PAYMENT_METHOD_CARD)
        self.assertEqual(order.collected_payment_method, Order.PAYMENT_METHOD_CARD)


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

    def test_pending_queue_defaults_to_company_delivery(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:deliveries"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["delivery_filter"], "company")
        groups = response.context["delivery_groups"]
        self.assertEqual([group["key"] for group in groups], ["company"])
        self.assertContains(response, "Σταδίου 10")
        self.assertNotContains(response, "Ερμού 1")
        self.assertContains(response, "Από υπάλληλο")

    def test_pending_queue_groups_company_first(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("administration:deliveries"),
            {"delivery": "all"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Μετρητά")
        self.assertContains(response, "Κάρτα")
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

    def test_delivered_orders_are_quiet_gray(self):
        self.old_order.status = Order.STATUS_DELIVERED
        self.old_order.save(update_fields=["status"])
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("administration:deliveries"),
            {"show": "delivered", "delivery": "all"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "delivery-row--delivered")
        self.assertContains(response, "Αλλαγή κατάστασης")
        self.assertContains(response, "bg-slate-600")
        self.assertNotContains(response, "bg-red-700")
        self.assertNotContains(response, "bg-red-50")

    def test_mark_delivered_and_undo(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("administration:mark_delivery", args=[self.old_order.pk]),
            {"action": "deliver", "show": "pending", "collected_payment": "cash_on_delivery"},
        )
        self.assertRedirects(
            response,
            reverse("administration:deliveries") + "?show=pending",
        )
        self.old_order.refresh_from_db()
        self.assertEqual(self.old_order.status, Order.STATUS_DELIVERED)

        blocked = self.client.post(
            reverse("administration:mark_delivery", args=[self.old_order.pk]),
            {"action": "undeliver", "show": "delivered"},
        )
        self.assertRedirects(
            blocked,
            reverse("administration:deliveries") + "?show=delivered",
        )
        self.old_order.refresh_from_db()
        self.assertEqual(self.old_order.status, Order.STATUS_DELIVERED)

        self.client.post(
            reverse("administration:mark_delivery", args=[self.old_order.pk]),
            {
                "action": "undeliver",
                "show": "delivered",
                "reason": "Πάτησα λάθος το κουμπί παράδοσης.",
            },
        )
        self.old_order.refresh_from_db()
        self.assertEqual(self.old_order.status, Order.STATUS_NEW)
        self.assertIn("Πάτησα λάθος", self.old_order.special_notes)

    def test_courier_can_cancel_a_delivered_order_with_reason(self):
        self.old_order.status = Order.STATUS_DELIVERED
        self.old_order.collected_payment_method = Order.PAYMENT_METHOD_COD
        self.old_order.save(update_fields=["status", "collected_payment_method"])
        self.client.force_login(self.courier_user)
        response = self.client.post(
            reverse("administration:mark_delivery", args=[self.old_order.pk]),
            {
                "action": "cancel",
                "show": "delivered",
                "reason": "Ο πελάτης αρνήθηκε την παραλαβή.",
            },
        )
        self.assertRedirects(
            response,
            reverse("administration:deliveries") + "?show=delivered",
        )
        self.old_order.refresh_from_db()
        self.assertEqual(self.old_order.status, Order.STATUS_CANCELLED)
        self.assertEqual(
            self.old_order.cancellation_reason,
            "Ο πελάτης αρνήθηκε την παραλαβή.",
        )

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

    def test_pending_rows_stay_compact_until_hover(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("administration:deliveries"))
        self.assertContains(response, "data-delivery-row")
        self.assertContains(response, "delivery-detail")
        self.assertContains(response, 'name="collected_payment"')
        self.assertContains(response, "Πράσινες")
        self.assertContains(response, "Πορτοκαλί")
        self.assertContains(response, "Κόκκινες")

    def test_cod_delivery_requires_cash_or_card(self):
        self.client.force_login(self.admin_user)
        self.client.post(
            reverse("administration:mark_delivery", args=[self.old_order.pk]),
            {"delivered": "1", "show": "pending"},
        )
        self.old_order.refresh_from_db()
        self.assertEqual(self.old_order.status, Order.STATUS_NEW)
        self.assertEqual(self.old_order.collected_payment_method, "")

    def test_boxnow_delivery_is_card_only(self):
        boxnow = Order.objects.create(
            user=self.customer,
            payment_method=Order.PAYMENT_METHOD_CARD,
            status=Order.STATUS_NEW,
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

        # Undoing the delivery must not erase a payment Stripe already took.
        self.client.post(
            reverse("administration:mark_delivery", args=[boxnow.pk]),
            {
                "action": "undeliver",
                "show": "delivered",
                "reason": "Ο πελάτης δεν ήταν στο locker.",
            },
        )
        boxnow.refresh_from_db()
        self.assertEqual(boxnow.status, Order.STATUS_NEW)
        self.assertEqual(boxnow.payment_method, Order.PAYMENT_METHOD_CARD)
        self.assertEqual(boxnow.collected_payment_method, Order.PAYMENT_METHOD_CARD)

    def test_company_orders_use_age_colors_and_filters(self):
        from datetime import date, datetime
        from unittest.mock import patch

        from orders.presentation import company_delivery_priority

        today = date(2026, 9, 4)  # Friday
        Order.objects.filter(pk=self.new_order.pk).update(
            order_date=timezone.make_aware(datetime(2026, 8, 28, 10, 0))
        )
        self.new_order.refresh_from_db()
        with patch("orders.presentation.timezone.localdate", return_value=today):
            self.assertEqual(company_delivery_priority(self.new_order), "red")
            self.assertEqual(company_delivery_priority(self.old_order), "")
            self.client.force_login(self.admin_user)
            response = self.client.get(reverse("administration:deliveries"))
        self.assertContains(response, "delivery-row--priority-red")
        self.assertContains(response, 'data-priority="red"')
        self.assertNotContains(response, 'data-priority="green"')

        with patch("orders.presentation.timezone.localdate", return_value=today):
            filtered = self.client.get(
                reverse("administration:deliveries"),
                {"priority": "red", "delivery": "all"},
            )
        company_rows = filtered.context["delivery_groups"][0]["orders"]
        courier_rows = filtered.context["delivery_groups"][1]["orders"]
        self.assertTrue(all(row.get("priority") == "red" for row in company_rows))
        self.assertTrue(any("Σταδίου 10" in row["delivery_address_display"] for row in company_rows))
        self.assertTrue(any("Ερμού 1" in row["delivery_address_display"] for row in courier_rows))
        self.assertTrue(all(not row.get("priority") for row in courier_rows))


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
            status=Order.STATUS_NEW,
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
