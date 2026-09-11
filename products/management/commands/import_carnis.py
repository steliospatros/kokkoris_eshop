"""
Import the Carnis dry-food range from the client transfer folder.

Photos are the pack shots in CARNIS_PHOTO&KEIMENA. Pack prices follow the
brand-page cards in PAGE_BRAND.pdf (small bag 18 €, large bag 71 € for dogs).

Usage:
    python manage.py import_carnis \\
        --photos-dir "/mnt/c/Users/steli/Downloads/transfer-01a06c84/CARNIS_PHOTO&KEIMENA"
"""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image

from products.description_copy import generate_product_description
from products.models import AnimalType, Category, Company, Product, ProductVariant

TRANSFER_DEFAULT = Path(
    "/mnt/c/Users/steli/Downloads/transfer-01a06c84/CARNIS_PHOTO&KEIMENA"
)

DOG_PRICES = (
    (Decimal("2.00"), Decimal("18.00")),
    (Decimal("4.00"), Decimal("29.00")),
    (Decimal("12.50"), Decimal("71.00")),
)
ADULT_CAT_PRICES = (
    (Decimal("3.00"), Decimal("18.00")),
    (Decimal("7.00"), Decimal("32.00")),
)
KITTEN_PRICES = (
    (Decimal("2.00"), Decimal("18.00")),
    (Decimal("4.00"), Decimal("32.00")),
)

PRODUCTS = (
    {
        "name": "Κοτόπουλο μικρή κροκέτα ξηρά τροφή - για σκύλους όλων των ηλικιών",
        "animal": "Dog",
        "photo": "s946835458127304065_p1_i1_w600.webp",
        "seed": (
            "Συμπιεσμένες κροκέτες μικρού μεγέθους με κοτόπουλο, ολλανδικής παραγωγής, "
            "χωρίς γλουτένη σίτου."
        ),
        "components": (
            "Πλήρης συμπιεσμένη ξηρά τροφή με κοτόπουλο, φυσικά συστατικά, "
            "βιταμίνες και μέταλλα. Χωρίς τεχνητά χρώματα, αρώματα και γεύσεις."
        ),
        "variants": DOG_PRICES,
    },
    {
        "name": "Σολομός μικρή κροκέτα ξηρά τροφή - για σκύλους όλων των ηλικιών",
        "animal": "Dog",
        "photo": "s946835458127304065_p3_i1_w600.webp",
        "seed": (
            "Συμπιεσμένες κροκέτες μικρού μεγέθους με σολομό, με χονδροϊτίνη και γλυκοζαμίνη, "
            "χωρίς γλουτένη σίτου."
        ),
        "components": (
            "Πλήρης συμπιεσμένη ξηρά τροφή με σολομό, φυσικά συστατικά, "
            "χονδροϊτίνη και γλυκοζαμίνη. Χωρίς τεχνητά χρώματα, αρώματα και γεύσεις."
        ),
        "variants": DOG_PRICES,
    },
    {
        "name": "Κουνέλι μικρή κροκέτα ξηρά τροφή - για σκύλους όλων των ηλικιών",
        "animal": "Dog",
        "photo": "s946835458127304065_p6_i1_w600.webp",
        "seed": (
            "Συμπιεσμένες κροκέτες μικρού μεγέθους με κουνέλι, κατάλληλες για ευαίσθητους "
            "σκύλους, χωρίς γλουτένη σίτου."
        ),
        "components": (
            "Πλήρης συμπιεσμένη ξηρά τροφή με κουνέλι και φυσικά συστατικά. "
            "Χωρίς τεχνητά χρώματα, αρώματα και γεύσεις."
        ),
        "variants": DOG_PRICES,
    },
    {
        "name": "Αρνί μικρή κροκέτα ξηρά τροφή - για σκύλους όλων των ηλικιών",
        "animal": "Dog",
        "photo": "s946835458127304065_p7_i2_w600.webp",
        "seed": (
            "Συμπιεσμένες κροκέτες μικρού μεγέθους πλούσιες σε αρνί, με MOS, χωρίς γλουτένη."
        ),
        "components": (
            "Πλήρης συμπιεσμένη ξηρά τροφή πλούσια σε αρνί, με φυσική πηγή MOS. "
            "Χωρίς τεχνητά χρώματα, αρώματα και γεύσεις."
        ),
        "variants": DOG_PRICES,
    },
    {
        "name": "Σολομός ξηρά τροφή - για ενήλικες γάτες",
        "animal": "Cat",
        "photo": "s946835458127304065_p9_i2_w1500.webp",
        "seed": (
            "Συνταγή χωρίς δημητριακά με σολομό, ταυρίνη, χονδροϊτίνη και "
            "γλυκοζαμίνη, για έλεγχο τριχόμπαλων."
        ),
        "components": (
            "Πλήρης ξηρά τροφή για ενήλικες γάτες με σολομό. Χωρίς δημητριακά, "
            "με ταυρίνη, χονδροϊτίνη, γλυκοζαμίνη και φυτικές ίνες."
        ),
        "variants": ADULT_CAT_PRICES,
    },
    {
        "name": "Classic ξηρά τροφή - για ενήλικες γάτες",
        "animal": "Cat",
        "photo": "s946835458127304065_p10_i3_w1500.webp",
        "seed": (
            "Κλασική συνταγή χωρίς γλουτένη σίτου, με ινουλίνη, χονδροϊτίνη "
            "και γλυκοζαμίνη."
        ),
        "components": (
            "Πλήρης ξηρά τροφή Classic για ενήλικες γάτες. Χωρίς γλουτένη σίτου, "
            "με ινουλίνη, χονδροϊτίνη και γλυκοζαμίνη."
        ),
        "variants": ADULT_CAT_PRICES,
    },
    {
        "name": "Kitten γαλοπούλα ξηρά τροφή - για γατάκια",
        "animal": "Cat",
        "photo": "s946835458127304065_p11_i4_w1500.webp",
        "seed": (
            "Συνταγή χωρίς δημητριακά, πλούσια σε γαλοπούλα, με ωμέγα 3 και 6 "
            "και ινουλίνη."
        ),
        "components": (
            "Πλήρης ξηρά τροφή για γατάκια, πλούσια σε γαλοπούλα. Χωρίς δημητριακά, "
            "με ωμέγα 3 και 6, ινουλίνη και ταυρίνη."
        ),
        "variants": KITTEN_PRICES,
    },
    {
        "name": "Adult XL γαλοπούλα ξηρά τροφή - για μεγαλόσωμες γάτες",
        "animal": "Cat",
        "photo": "s946835458127304065_p12_i4_w1500.webp",
        "seed": (
            "Συνταγή χωρίς δημητριακά με γαλοπούλα για μεγαλόσωμες ενήλικες γάτες, "
            "με χονδροϊτίνη και γλυκοζαμίνη."
        ),
        "components": (
            "Πλήρης ξηρά τροφή Adult XL με γαλοπούλα για μεγαλόσωμες γάτες. "
            "Χωρίς δημητριακά, με χονδροϊτίνη, γλυκοζαμίνη και φυτικές ίνες."
        ),
        "variants": ADULT_CAT_PRICES,
    },
)


def _save_image(product: Product, source: Path, dest_name: str) -> None:
    image = Image.open(source)
    if image.mode not in ("RGB", "L"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "RGBA":
            background.paste(image, mask=image.split()[-1])
        else:
            background.paste(image.convert("RGB"))
        image = background
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    product.image.save(dest_name, ContentFile(buffer.read()), save=True)


class Command(BaseCommand):
    help = "Import Carnis pack shots, Greek copy, and brand-page pack prices."

    def add_arguments(self, parser):
        parser.add_argument("--photos-dir", default=str(TRANSFER_DEFAULT))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        photos_dir = Path(options["photos_dir"])
        dry_run = options["dry_run"]
        if not photos_dir.is_dir():
            raise CommandError(f"Photos directory not found: {photos_dir}")

        try:
            company = Company.objects.get(name="Carnis")
        except Company.DoesNotExist as exc:
            raise CommandError("Company 'Carnis' not found. Run seed_data first.") from exc

        animals = {animal.name: animal for animal in AnimalType.objects.all()}
        category = Category.objects.get(name="Dry Food")
        created = updated = variants = photos = 0

        for spec in PRODUCTS:
            photo_path = photos_dir / spec["photo"]
            description = generate_product_description(
                name=spec["name"],
                company=company.name,
                animal=spec["animal"],
                category=category.name,
                seed_description=spec["seed"],
            )
            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] {spec['name']} | {spec['animal']} | "
                    f"photo={'yes' if photo_path.is_file() else 'MISSING'}"
                )
                continue

            with transaction.atomic():
                product, was_created = Product.objects.get_or_create(
                    name=spec["name"],
                    company=company,
                    defaults={
                        "animal_type": animals[spec["animal"]],
                        "category": category,
                        "description": description,
                        "components": spec["components"],
                        "is_active": True,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                    if not product.is_active:
                        product.is_active = True
                        product.save(update_fields=["is_active", "updated_at"])

                if photo_path.is_file() and (was_created or not product.image):
                    dest = f"carnis-{product.slug}.jpg"
                    _save_image(product, photo_path, dest)
                    photos += 1
                elif not photo_path.is_file():
                    self.stdout.write(self.style.WARNING(f"  ! Missing photo {photo_path.name}"))

                for weight, price in spec["variants"]:
                    variant, v_created = ProductVariant.objects.get_or_create(
                        product=product,
                        weight=weight,
                        defaults={
                            "price": price,
                            "stock": 20,
                            "availability": ProductVariant.AVAILABILITY_AVAILABLE_NOW,
                        },
                    )
                    if v_created:
                        variants += 1
                    else:
                        changed = []
                        if variant.price == Decimal("0.00"):
                            variant.price = price
                            changed.append("price")
                        if variant.availability != ProductVariant.AVAILABILITY_AVAILABLE_NOW:
                            variant.availability = ProductVariant.AVAILABILITY_AVAILABLE_NOW
                            changed.append("availability")
                        if variant.stock == 0:
                            variant.stock = 20
                            changed.append("stock")
                        if changed:
                            variant.save(update_fields=changed)

        logo_path = photos_dir / "LOGO_CARNIS.PNG"
        if not dry_run and logo_path.is_file() and not company.logo:
            with logo_path.open("rb") as handle:
                company.logo.save("car_LOGO_CARNIS.png", ContentFile(handle.read()), save=True)
            self.stdout.write(self.style.SUCCESS("  + Imported Carnis logo"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Carnis: {created} new products, {updated} existing, "
                f"{variants} variants, {photos} photos. Activated for sale."
            )
        )
