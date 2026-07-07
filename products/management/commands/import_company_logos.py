"""
Import brand logo images from the client's LOGOS folder into Company.logo.

Each entry maps a Company.name to a source filename under LOGOS_DIR.
Re-running is safe: existing logos are overwritten only with --force, or
when the Company has no logo yet.

Usage:
    python manage.py import_company_logos
    python manage.py import_company_logos --force
"""
import subprocess
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from products.models import Company

# Client asset folder (WSL path to the Windows LOGOS directory).
LOGOS_DIR = Path("/mnt/c/Users/steli/KOKORIS_eshop/LOGOS")

# Company.name -> source filename inside LOGOS_DIR.
LOGO_MAP = {
    "CLUB4PAWS": "LOGO_CLUB4PAWS_FOTO.png",
    "Core": "LOGO_CORIS_PHOTO.pdf",
    "OWNAT": "LOGO_OWNAT_FOTO.png",
    "PROFINE": "LOGO_PROFINE_FOTO.png",
    "EVERCLEAN": "logo_Everclean_blue.jpg",
    "Wild Side": "LOGO_WILDSIDE_FOTO.png",
    "Puro Instinto": "pienso-puro-instinto.jpg",
}


class Command(BaseCommand):
    help = "Import company logo images from the client LOGOS folder into Company.logo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite logos even when Company.logo is already set.",
        )
        parser.add_argument(
            "--logos-dir",
            type=str,
            default=str(LOGOS_DIR),
            help="Override the LOGOS source directory.",
        )

    def handle(self, *args, **options):
        logos_dir = Path(options["logos_dir"])
        if not logos_dir.is_dir():
            raise CommandError(f"LOGOS directory not found: {logos_dir}")

        force = options["force"]
        imported = 0
        skipped = 0

        for company_name, filename in LOGO_MAP.items():
            source = logos_dir / filename
            if not source.is_file():
                self.stdout.write(
                    self.style.WARNING(f"  ! Missing file for {company_name}: {source}")
                )
                continue

            try:
                company = Company.objects.get(name=company_name)
            except Company.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ! Company '{company_name}' not in DB — run seed_data first."
                    )
                )
                continue

            if company.logo and not force:
                self.stdout.write(f"  = Skipped {company_name} (logo already set, use --force)")
                skipped += 1
                continue

            upload_path, upload_name, cleanup = self._prepare_upload(source, company.code)
            try:
                with upload_path.open("rb") as fh:
                    company.logo.save(upload_name, File(fh), save=True)
            finally:
                if cleanup:
                    upload_path.unlink(missing_ok=True)

            self.stdout.write(self.style.SUCCESS(f"  + Imported logo for {company_name}"))
            imported += 1

        self.stdout.write(
            self.style.SUCCESS(f"Done: {imported} imported, {skipped} skipped.")
        )

    def _prepare_upload(self, source: Path, company_code: str):
        """
        Return (path_to_upload, dest_filename, cleanup_flag).

        PDF sources are rasterised to PNG first because Company.logo is an
        ImageField and cannot store vector PDFs directly.
        """
        if source.suffix.lower() != ".pdf":
            dest_name = f"{company_code.lower()}_{source.stem}{source.suffix.lower()}"
            return source, dest_name, False

        tmp = Path(tempfile.mktemp(suffix=".png"))
        result = subprocess.run(
            ["convert", str(source), "-density", "200", str(tmp)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise CommandError(
                f"Failed to convert PDF logo {source}: {result.stderr.strip()}"
            )

        dest_name = f"{company_code.lower()}_{source.stem}.png"
        return tmp, dest_name, True
