from django.core.management.base import BaseCommand, CommandError

from products.shelf_stock import apply_warehouse_stock


class Command(BaseCommand):
    help = (
        "Apply the handwritten warehouse stock. All other variants become "
        "on-order with shop quantity 0."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        report = apply_warehouse_stock(dry_run=dry_run)

        if report["missing"]:
            for item in report["missing"]:
                self.stderr.write(self.style.ERROR(f"Missing: {item}"))
            raise CommandError(
                "Aborting: one or more handwritten stock rows were not found."
            )

        prefix = "[DRY RUN] " if dry_run else ""
        for name, old_weight, new_weight, _pk in report["weight_updates"]:
            self.stdout.write(
                f"{prefix}Carnis weight {name}: {old_weight} kg → {new_weight} kg"
            )
        self.stdout.write(
            f"{prefix}On-order with shop stock 0: {report['on_order']} variant(s)."
        )
        for _pk, name, weight, quantity in report["shelf"]:
            self.stdout.write(
                f"{prefix}Shelf {quantity} × {name} ({weight} kg)"
            )
        for warning in report["warnings"]:
            self.stdout.write(self.style.WARNING(f"{prefix}{warning}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Applied {len(report['shelf'])} in-store SKUs."
            )
        )
