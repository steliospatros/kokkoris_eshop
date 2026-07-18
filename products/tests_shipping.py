"""Tests for ELTA Courier shipping cost calculation."""
from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase

from products.utils import (
    REGION_ATTICA,
    COD_FEE,
    calculate_shipping_cost,
    postal_code_to_region,
)


def _line(weight, length, width, height, quantity=1):
    """Build a minimal cart line stub for shipping tests."""
    product = SimpleNamespace(
        weight=Decimal(str(weight)),
        length=Decimal(str(length)),
        width=Decimal(str(width)),
        height=Decimal(str(height)),
    )
    return SimpleNamespace(product_variant=SimpleNamespace(product=product), quantity=quantity)


class PostalCodeRegionTests(TestCase):
    def test_athens_postal_code_is_attica(self):
        self.assertEqual(postal_code_to_region("10563"), REGION_ATTICA)

    def test_crete_postal_code_is_not_attica(self):
        self.assertEqual(postal_code_to_region("71201"), "Other")


class ShippingCostTests(TestCase):
    def test_base_fee_for_light_shipment(self):
        items = [_line(1.5, 20, 15, 10)]
        cost = calculate_shipping_cost(items, Decimal("15.00"), REGION_ATTICA)
        self.assertEqual(cost, Decimal("2.00"))

    def test_extra_weight_surcharge_rounds_up(self):
        # 3.1 kg chargeable → 2 kg over limit → ceil(1.1) = 2 extra kg
        items = [_line(3.1, 10, 10, 10)]
        cost = calculate_shipping_cost(items, Decimal("15.00"), REGION_ATTICA)
        self.assertEqual(cost, Decimal("2.00") + Decimal("2") * Decimal("0.80"))

    def test_volumetric_weight_used_when_higher_than_real_weight(self):
        # Real: 0.5 kg; volumetric: (50*40*30)/5000 = 12 kg
        items = [_line(0.5, 50, 40, 30)]
        cost = calculate_shipping_cost(items, Decimal("15.00"), REGION_ATTICA)
        extra_kg = 12 - 2  # chargeable 12 kg, base limit 2
        expected = Decimal("2.00") + Decimal(extra_kg) * Decimal("0.80")
        self.assertEqual(cost, expected)

    def test_free_shipping_in_attica_for_orders_over_20(self):
        items = [_line(5, 30, 20, 15)]
        cost = calculate_shipping_cost(items, Decimal("20.00"), REGION_ATTICA)
        self.assertEqual(cost, Decimal("0.00"))

    def test_attica_under_20_charges_courier_fee(self):
        items = [_line(1.5, 20, 15, 10)]
        cost = calculate_shipping_cost(items, Decimal("19.99"), REGION_ATTICA)
        self.assertEqual(cost, Decimal("2.00"))

    def test_free_shipping_outside_attica_for_large_cart(self):
        items = [_line(5, 30, 20, 15)]
        cost = calculate_shipping_cost(items, Decimal("50.00"), "Other")
        self.assertEqual(cost, Decimal("0.00"))

    def test_cod_fee_applies_even_when_attica_shipping_is_free(self):
        items = [_line(5, 30, 20, 15)]
        cost = calculate_shipping_cost(
            items,
            Decimal("25.00"),
            REGION_ATTICA,
            is_cash_on_delivery=True,
        )
        self.assertEqual(cost, COD_FEE)

    def test_cod_fee_applies_even_when_shipping_is_free(self):
        items = [_line(5, 30, 20, 15)]
        cost = calculate_shipping_cost(
            items,
            Decimal("60.00"),
            "Other",
            is_cash_on_delivery=True,
        )
        self.assertEqual(cost, COD_FEE)

    def test_cod_fee_added_to_paid_shipping(self):
        items = [_line(1.0, 10, 10, 10)]
        cost = calculate_shipping_cost(
            items,
            Decimal("15.00"),
            REGION_ATTICA,
            is_cash_on_delivery=True,
        )
        self.assertEqual(cost, Decimal("2.00") + COD_FEE)
