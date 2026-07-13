from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory, TestCase
from django.urls import resolve, reverse

from core.breadcrumbs import HOME_LABEL, build_breadcrumbs


class BreadcrumbLogicTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, path, query=None):
        if "?" in path:
            path_only, query_string = path.split("?", 1)
            query = query or query_string
        else:
            path_only = path

        request = self.factory.get(path_only, query or {})
        request.session = {}
        request.user = AnonymousUser()
        request.resolver_match = resolve(path_only)
        return request

    def test_homepage_has_no_breadcrumbs(self):
        self.assertEqual(build_breadcrumbs(self._request("/")), [])

    def test_dogs_page_starts_with_homepage(self):
        trail = build_breadcrumbs(self._request("/products/dogs/"))
        self.assertEqual(len(trail), 2)
        self.assertEqual(trail[0]["label"], HOME_LABEL)
        self.assertEqual(trail[0]["url"], reverse("home"))
        self.assertEqual(trail[1]["label"], "Σκύλος")

    def test_browse_splits_animal_and_category(self):
        trail = build_breadcrumbs(
            self._request(
                "/products/browse/",
                query={"animal": "dog", "category": "dry-food"},
            )
        )
        self.assertEqual(len(trail), 3)
        self.assertEqual(trail[0]["label"], HOME_LABEL)
        self.assertEqual(trail[1]["label"], "Σκύλος")
        self.assertEqual(trail[1]["url"], reverse("products:dogs"))
        self.assertEqual(trail[2]["label"], "Ξηρά τροφή")

    def test_accounts_details_includes_hub(self):
        trail = build_breadcrumbs(self._request("/accounts/details/"))
        self.assertEqual(len(trail), 3)
        self.assertEqual(trail[0]["label"], HOME_LABEL)
        self.assertEqual(trail[1]["label"], "Ο λογαριασμός μου")
        self.assertEqual(trail[2]["label"], "Τα στοιχεία μου")

    def test_checkout_trail_includes_cart_before_step(self):
        trail = build_breadcrumbs(self._request("/checkout/delivery/"))
        self.assertEqual(len(trail), 4)
        self.assertEqual(trail[0]["label"], HOME_LABEL)
        self.assertEqual(trail[1]["label"], "Το καλάθι μου")
        self.assertEqual(trail[1]["url"], reverse("accounts:cart"))
        self.assertEqual(trail[2]["label"], "Διεύθυνση παράδοσης")
        self.assertEqual(trail[3]["label"], "Τρόπος παράδοσης")

    def test_accounts_cart_without_items_has_plain_label(self):
        trail = build_breadcrumbs(self._request("/accounts/cart/"))
        self.assertEqual(trail[-1]["label"], "Το καλάθι μου")


class BreadcrumbTrailTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_homepage_does_not_render_breadcrumbs(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["breadcrumbs"], [])
        self.assertNotContains(response, "site-breadcrumbs")

    def test_browse_renders_hierarchical_path(self):
        response = self.client.get(
            reverse("products:browse") + "?animal=dog&category=dry-food"
        )
        self.assertEqual(response.status_code, 200)
        breadcrumbs = response.context["breadcrumbs"]
        self.assertEqual(len(breadcrumbs), 3)
        self.assertEqual(breadcrumbs[0]["label"], HOME_LABEL)
        self.assertEqual(breadcrumbs[1]["label"], "Σκύλος")
        self.assertEqual(breadcrumbs[2]["label"], "Ξηρά τροφή")
        self.assertContains(response, "site-breadcrumbs")
        self.assertContains(response, HOME_LABEL)
        self.assertContains(response, "Ξηρά τροφή")

    def test_account_flow_shows_breadcrumbs(self):
        user = get_user_model().objects.create_user(
            email="user@example.com",
            password="pass12345",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:details"))
        breadcrumbs = response.context["breadcrumbs"]
        self.assertEqual(len(breadcrumbs), 3)
        self.assertEqual(breadcrumbs[0]["label"], HOME_LABEL)
        self.assertEqual(breadcrumbs[1]["label"], "Ο λογαριασμός μου")
        self.assertEqual(breadcrumbs[2]["label"], "Τα στοιχεία μου")

    def test_info_page_starts_with_homepage(self):
        response = self.client.get(reverse("pages:contact"))
        breadcrumbs = response.context["breadcrumbs"]
        self.assertEqual(len(breadcrumbs), 2)
        self.assertEqual(breadcrumbs[0]["label"], HOME_LABEL)
        self.assertEqual(breadcrumbs[1]["label"], "Επικοινωνία")
