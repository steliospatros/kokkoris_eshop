"""
Import the Puro Instinto dry-food range from the client transfer folder.

Pack sizes follow the manufacturer bags (3 kg / 15 kg for dogs, 3 kg for cat).
Retail prices come from PURO INSTINTO.docx. Products are listed as immediately
available, matching the «Αγορά» buttons on PAGE_BRAND.pdf.

Usage:
    python manage.py import_puro_instinto \\
        --photos-dir "/mnt/c/Users/steli/Downloads/transfer-01a06c84/PURO INSTINTO_PHOTO&KEIMENA"
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
    "/mnt/c/Users/steli/Downloads/transfer-01a06c84/PURO INSTINTO_PHOTO&KEIMENA"
)

PRODUCTS = (
    {
        "name": "4 Meats ξηρά τροφή - για ενήλικους σκύλους",
        "animal": "Dog",
        "photo": "s946835458127304065_p14_i10_w2362.webp",
        "seed": (
            "Χαμηλά δημητριακά, με 64% ζωική πρωτεΐνη από τέσσερα κρέατα, "
            "πρεβιοτικά FOS και MOS."
        ),
        "components": (
            "Υδρόλυση κρεάτων (κουνέλι, πουλερικά, βοδινό και ίππος), καστανό ρύζι, "
            "ολόκληρο ρύζι, λίπος πουλερικών, όσπρια, φυσικό άρωμα συκωτιού πουλερικών, "
            "ίνα ρυζιού, μαγιά μπύρας, λάδι ψαριού πλούσιο σε Ω3, λιγνοκυτταρίνη, "
            "αφυδατωμένο αυγό, γλυκοζαμίνη, L-λυσίνη, MOS, FOS, μεθειονίνη, "
            "φυσικά αντιοξειδωτικά, βιταμίνες και μέταλλα, χηλικός ψευδάργυρος, "
            "προβιοτικά, εκχύλισμα yucca shidigera, L-καρνιτίνη."
        ),
        "variants": (
            (Decimal("3.00"), Decimal("16.00")),
            (Decimal("15.00"), Decimal("62.00")),
        ),
    },
    {
        "name": "Fish ξηρά τροφή - για ενήλικους σκύλους",
        "animal": "Dog",
        "photo": "s946835458127304065_p15_i14_w2362.webp",
        "seed": (
            "Χαμηλά δημητριακά με σολομό και 62% ζωική πρωτεΐνη, "
            "χονδροϊτίνη και γλυκοζαμίνη."
        ),
        "components": (
            "Σολομός, ρύζι, αφυδατωμένη πρωτεΐνη πουλερικών, όσπρια, πρωτεΐνη καλαμποκιού, "
            "λίπος κοτόπουλου, λάδι σολομού πλούσιο σε Ω3, μαγιά μπύρας, "
            "υδρόλυμα συκωτιού κοτόπουλου, μεταλλικές ουσίες, εκχύλισμα yucca schidigera, "
            "γλυκοζαμίνη, χονδροϊτίνη, MOS, FOS, πρεβιοτικά, φυσικά αντιοξειδωτικά."
        ),
        "variants": (
            (Decimal("3.00"), Decimal("18.00")),
            (Decimal("15.00"), Decimal("71.00")),
        ),
    },
    {
        "name": "Puppy ξηρά τροφή - για κουτάβια",
        "animal": "Dog",
        "photo": "s946835458127304065_p16_i24_w2362.webp",
        "seed": (
            "Χαμηλά δημητριακά με 66% ζωική πρωτεΐνη, γλυκοζαμίνη, χονδροϊτίνη "
            "και ταυρίνη για σωστή ανάπτυξη."
        ),
        "components": (
            "Υδρόλυση κοτόπουλου, ρύζι, εκχύλισμα φυτικής πρωτεΐνης, λίπος πουλερικών, "
            "αφυδατωμένη πρωτεΐνη ψαριού, μπιζέλια, αρνί, φυσικό άρωμα συκωτιού πουλερικών, "
            "μαγιά μπύρας, λάδι ψαριού, αφυδατωμένο αυγό, λιγνοκυτταρίνη, γλυκοζαμίνη, "
            "χονδροϊτίνη, ταυρίνη, MOS, FOS, φυσικά αντιοξειδωτικά, βιταμίνες και μέταλλα, "
            "L-καρνιτίνη."
        ),
        "variants": ((Decimal("15.00"), Decimal("62.00")),),
    },
    {
        "name": "Light Senior ξηρά τροφή - για σκύλους",
        "animal": "Dog",
        "photo": "s946835458127304065_p17_i29_w2362.webp",
        "seed": (
            "Συνταγή χαμηλών θερμίδων για μεγαλύτερους σκύλους, με 62% ζωική "
            "πρωτεΐνη, γλυκοζαμίνη και χονδροϊτίνη."
        ),
        "components": (
            "Συνταγή Light / Senior με υψηλή ζωική πρωτεΐνη, γλυκοζαμίνη, "
            "χονδροϊτίνη και ωμέγα 3 και 6."
        ),
        "variants": ((Decimal("15.00"), Decimal("52.00")),),
    },
    {
        "name": "Chicken ξηρά τροφή - για ενήλικες γάτες",
        "animal": "Cat",
        "photo": "s946835458127304065_p25_i18_w2362.webp",
        "seed": (
            "Χαμηλά δημητριακά με κοτόπουλο και 66% ζωική πρωτεΐνη, ταυρίνη "
            "και πρεβιοτικά FOS και MOS."
        ),
        "components": (
            "Προϊόν υδρόλυσης κοτόπουλου 30%, ρύζι, λίπος πουλερικών, τόνος, "
            "πρωτεΐνη καλαμποκιού, μαγιά μπύρας, λάδι σολομού πλούσιο σε Ω3, "
            "φυσικό άρωμα συκωτιού πουλερικών, λιγνοκυτταρίνη, χλωριούχο νάτριο, "
            "χλωριούχο κάλιο, ταυρίνη, L-λυσίνη, φυσικά αντιοξειδωτικά, "
            "εκχύλισμα yucca shidigera, χηλικός ψευδάργυρος, βιταμίνες και μέταλλα."
        ),
        "variants": ((Decimal("3.00"), Decimal("18.00")),),
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
    help = "Import Puro Instinto products with photos, Greek copy and Word-file prices."

    def add_arguments(self, parser):
        parser.add_argument("--photos-dir", default=str(TRANSFER_DEFAULT))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        photos_dir = Path(options["photos_dir"])
        dry_run = options["dry_run"]
        if not photos_dir.is_dir():
            raise CommandError(f"Photos directory not found: {photos_dir}")

        try:
            company = Company.objects.get(name="Puro Instinto")
        except Company.DoesNotExist as exc:
            raise CommandError(
                "Company 'Puro Instinto' not found. Run seed_data first."
            ) from exc

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
                sizes = ", ".join(f"{w}kg@{p}€" for w, p in spec["variants"])
                self.stdout.write(
                    f"[DRY RUN] {spec['name']} | {spec['animal']} | {sizes} | "
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
                    _save_image(product, photo_path, f"puro-{product.slug}.jpg")
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Puro Instinto: {created} new products, {updated} existing, "
                f"{variants} variants, {photos} photos. Activated for sale."
            )
        )
