from django.core.management.base import BaseCommand

from products.models import ProductVariant


class Command(BaseCommand):
    help = "Set the same stock level on every product variant (default: 20)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stock",
            type=int,
            default=20,
            help="Stock quantity to apply to all variants (default: 20).",
        )

    def handle(self, *args, **options):
        stock = options["stock"]
        if stock < 0:
            self.stderr.write(self.style.ERROR("Stock must be zero or greater."))
            return

        updated = ProductVariant.objects.update(stock=stock)
        self.stdout.write(
            self.style.SUCCESS(f"Set stock={stock} on {updated} variant(s).")
        )
