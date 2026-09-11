from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from products.models import AnimalType, Category, Company, Product, ProductVariant


class ProductDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="TESTBRAND", code="TST")
        cls.animal = AnimalType.objects.create(name="Dog", slug="dog")
        cls.category = Category.objects.create(name="Dry Food", slug="dry-food")
        cls.product = Product.objects.create(
            name="Test Adult Chicken",
            company=cls.company,
            animal_type=cls.animal,
            category=cls.category,
            description="Πλήρης τροφή για ενήλικους σκύλους.",
            components="Κοτόπουλο 30%, ρύζι.",
            is_active=True,
        )
        cls.variant_small = ProductVariant.objects.create(
            product=cls.product,
            weight=Decimal("2.00"),
            sku="TST-2KG",
            price=Decimal("11.50"),
        )
        cls.variant_large = ProductVariant.objects.create(
            product=cls.product,
            weight=Decimal("10.00"),
            sku="TST-10KG",
            price=Decimal("45.00"),
        )

    def test_product_detail_page_renders(self):
        url = reverse("products:detail", kwargs={"slug": self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Adult Chicken")
        self.assertContains(response, "Πλήρης τροφή")
        self.assertContains(response, "Κοτόπουλο 30%")
        self.assertContains(response, "TST-10KG")

    def test_product_detail_unknown_slug_404(self):
        response = self.client.get(reverse("products:detail", kwargs={"slug": "missing-product"}))
        self.assertEqual(response.status_code, 404)

    def test_related_products_priority(self):
        from products.catalog import get_related_products_for_detail

        other_company = Company.objects.create(name="OTHER", code="OTH")
        same_cat_other_brand = Product.objects.create(
            name="Same Cat Other Brand",
            company=other_company,
            animal_type=self.animal,
            category=self.category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=same_cat_other_brand,
            weight=Decimal("1.00"),
            price=Decimal("5.00"),
        )

        other_category = Category.objects.create(name="Sachets", slug="sachets")
        same_brand_other_cat = Product.objects.create(
            name="Same Brand Other Cat",
            company=self.company,
            animal_type=self.animal,
            category=other_category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=same_brand_other_cat,
            weight=Decimal("1.00"),
            price=Decimal("5.00"),
        )

        other_animal = AnimalType.objects.create(name="Cat", slug="cat")
        wrong_animal = Product.objects.create(
            name="Wrong Animal",
            company=self.company,
            animal_type=other_animal,
            category=self.category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=wrong_animal,
            weight=Decimal("1.00"),
            price=Decimal("5.00"),
        )

        unrelated = Product.objects.create(
            name="Unrelated Dog",
            company=other_company,
            animal_type=self.animal,
            category=other_category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=unrelated,
            weight=Decimal("1.00"),
            price=Decimal("5.00"),
        )

        twin = Product.objects.create(
            name="Twin Product",
            company=self.company,
            animal_type=self.animal,
            category=self.category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=twin,
            weight=Decimal("3.00"),
            price=Decimal("15.00"),
        )

        related = get_related_products_for_detail(self.product)
        names = [p.name for p in related]
        self.assertIn("Twin Product", names)
        self.assertIn("Same Cat Other Brand", names)
        self.assertIn("Same Brand Other Cat", names)
        self.assertNotIn("Wrong Animal", names)
        self.assertNotIn("Unrelated Dog", names)
        self.assertEqual(names[0], "Twin Product")
        self.assertEqual(names[1], "Same Cat Other Brand")
        self.assertEqual(names[2], "Same Brand Other Cat")

    def test_product_detail_filter_links(self):
        url = reverse("products:detail", kwargs={"slug": self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"?animal={self.animal.slug}")
        self.assertContains(response, f"?category={self.category.slug}")
        self.assertContains(response, f"?brand={self.company.code}")

    def test_catalog_card_includes_detail_url(self):
        from products.catalog import build_catalog_card, get_catalog_queryset

        product = get_catalog_queryset().get(pk=self.product.pk)
        card = build_catalog_card(product)
        self.assertIn("detail_url", card)
        self.assertIn(self.product.slug, card["detail_url"])

    def test_on_order_uses_same_buy_button_and_a_note(self):
        from products.catalog import build_catalog_card, get_catalog_queryset, get_stock_display

        display = get_stock_display(self.variant_small)
        self.assertEqual(display.get("button_label", "Αγορά"), "Αγορά")
        self.assertEqual(display["label"], "")

        self.variant_small.availability = ProductVariant.AVAILABILITY_ON_ORDER
        self.variant_small.save(update_fields=["availability"])
        on_order = get_stock_display(self.variant_small)
        self.assertEqual(on_order["button_label"], "Αγορά")
        self.assertEqual(on_order["label"], "Κατόπιν παραγγελίας")
        self.assertTrue(on_order["can_add"])

        self.product.variants.update(
            availability=ProductVariant.AVAILABILITY_ON_ORDER
        )
        card = build_catalog_card(get_catalog_queryset().get(pk=self.product.pk))
        self.assertEqual(card["button_label"], "Αγορά")
        self.assertEqual(card["availability_label"], "Κατόπιν παραγγελίας")
        listing = self.client.get(reverse("products:all"))
        self.assertContains(listing, "Αγορά")
        self.assertContains(listing, "Κατόπιν παραγγελίας")
        self.assertNotContains(listing, "bg-kokkoris-blue")

    def test_hidden_and_unavailable_products_leave_the_shop(self):
        from products.catalog import get_catalog_queryset, get_product_detail_queryset

        self.product.is_active = False
        self.product.save(update_fields=["is_active"])
        self.assertFalse(get_catalog_queryset().filter(pk=self.product.pk).exists())
        self.assertFalse(get_product_detail_queryset().filter(pk=self.product.pk).exists())
        listing = self.client.get(reverse("products:all"))
        self.assertNotContains(listing, self.product.name)
        detail = self.client.get(
            reverse("products:detail", kwargs={"slug": self.product.slug})
        )
        self.assertEqual(detail.status_code, 404)

        self.product.is_active = True
        self.product.save(update_fields=["is_active"])
        self.product.variants.update(
            availability=ProductVariant.AVAILABILITY_OUT_OF_STOCK
        )
        self.assertFalse(get_catalog_queryset().filter(pk=self.product.pk).exists())
        response = self.client.get(
            reverse("products:detail", kwargs={"slug": self.product.slug})
        )
        self.assertEqual(response.status_code, 404)

    def test_unit_price_shown_only_for_dry_food(self):
        from products.catalog import build_catalog_card, build_variant_option, get_catalog_queryset

        dry = get_catalog_queryset().get(pk=self.product.pk)
        dry_card = build_catalog_card(dry)
        self.assertTrue(dry_card["unit_price_display"])

        sachets = Category.objects.create(name="Sachets", slug="sachets")
        wet = Product.objects.create(
            name="Wet Chicken Pouch",
            company=self.company,
            animal_type=self.animal,
            category=sachets,
            is_active=True,
        )
        wet_variant = ProductVariant.objects.create(
            product=wet,
            weight=Decimal("0.10"),
            price=Decimal("1.20"),
        )
        wet = get_catalog_queryset().get(pk=wet.pk)
        wet_card = build_catalog_card(wet)
        self.assertEqual(wet_card["unit_price_display"], "")
        self.assertEqual(build_variant_option(wet_variant)["unit_price_display"], "")

    def test_default_sort_mixes_but_keeps_popular_ahead(self):
        from products.catalog import apply_catalog_sort, get_catalog_queryset, popularity_mix_list
        from products.models import Favourite

        popular = Product.objects.create(
            name="Popular Mix Food",
            company=self.company,
            animal_type=self.animal,
            category=self.category,
            is_active=True,
        )
        ProductVariant.objects.create(product=popular, weight=Decimal("2.00"), price=Decimal("10.00"))
        Favourite.objects.filter(product=popular).update(purchase_count=80, score=400)

        other = Product.objects.create(
            name="Quiet Mix Food",
            company=self.company,
            animal_type=self.animal,
            category=self.category,
            is_active=True,
        )
        ProductVariant.objects.create(product=other, weight=Decimal("2.00"), price=Decimal("10.00"))

        queryset = get_catalog_queryset().filter(pk__in=[popular.pk, other.pk, self.product.pk])
        first = apply_catalog_sort(queryset, "default", mix_seed=7)
        second = apply_catalog_sort(queryset, "default", mix_seed=7)
        shuffled_input = list(reversed(list(queryset)))
        third = popularity_mix_list(shuffled_input, seed=7)
        self.assertEqual([p.pk for p in first], [p.pk for p in second])
        self.assertEqual([p.pk for p in first], [p.pk for p in third])
        self.assertEqual(first[0].pk, popular.pk)

        mixed_seeds = [
            popularity_mix_list(queryset, seed=seed)[0].pk
            for seed in range(1, 21)
        ]
        self.assertGreaterEqual(mixed_seeds.count(popular.pk), 15)


class FrozenEmptyCompanyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empty = Company.objects.create(name="Empty Brand", code="EMP")
        cls.visible = Company.objects.create(name="Visible Brand", code="VIS")
        animal = AnimalType.objects.create(name="Dog", slug="dog")
        category = Category.objects.create(name="Dry Food", slug="dry-food")
        visible_product = Product.objects.create(
            name="Visible Food",
            company=cls.visible,
            animal_type=animal,
            category=category,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=visible_product, weight=2, price=10, stock=5
        )

    def test_empty_company_hidden_from_brand_tiles(self):
        from products.catalog import build_brand_landing_page, build_brand_tiles

        labels = [tile["label"] for tile in build_brand_tiles()]
        self.assertIn("Visible Brand", labels)
        self.assertNotIn("Empty Brand", labels)

        landing_labels = [spot["label"] for spot in build_brand_landing_page()["landing_hotspots"]]
        self.assertNotIn("Empty Brand", landing_labels)

        from products.catalog import build_homepage_brand_list

        home_labels = [brand["label"] for brand in build_homepage_brand_list()]
        self.assertNotIn("Empty Brand", home_labels)
        self.assertTrue(
            all("logo_url" in brand for brand in build_homepage_brand_list())
        )

    def test_browse_company_logo_links_to_brand_page(self):
        company = Company.objects.create(name="Core", code="COR")
        animal = AnimalType.objects.get(slug="dog")
        category = Category.objects.get(slug="dry-food")
        product = Product.objects.create(
            name="Core Adult",
            company=company,
            animal_type=animal,
            category=category,
            is_active=True,
        )
        ProductVariant.objects.create(product=product, weight=2, price=10, stock=5)

        response = self.client.get(
            reverse("products:browse"),
            {"animal": "dog", "category": "dry-food"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("products:company", args=["COR"]))
        self.assertContains(response, "browse-company-header__link")

    def test_empty_company_page_redirects(self):
        response = self.client.get(
            reverse("products:company", kwargs={"company_code": "EMP"})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("products:brands"))

    def test_hidden_only_company_leaves_the_shop(self):
        from products.catalog import build_brand_tiles

        animal = AnimalType.objects.get(slug="dog")
        category = Category.objects.get(slug="dry-food")
        hidden_brand = Company.objects.create(name="Hidden Brand", code="HID")
        product = Product.objects.create(
            name="Secret Food",
            company=hidden_brand,
            animal_type=animal,
            category=category,
            is_active=False,
        )
        ProductVariant.objects.create(product=product, weight=2, price=10, stock=5)

        labels = [tile["label"] for tile in build_brand_tiles()]
        self.assertNotIn("Hidden Brand", labels)
        response = self.client.get(
            reverse("products:company", kwargs={"company_code": "HID"})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("products:brands"))
