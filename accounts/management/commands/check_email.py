"""Diagnostic command for SMTP / transactional email settings."""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify SMTP email configuration and optionally send a test message."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            dest="to_email",
            help="Send a test email to this address.",
        )

    def handle(self, *args, **options):
        backend = settings.EMAIL_BACKEND
        self.stdout.write(f"EMAIL_BACKEND: {backend}")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST or '(empty)'}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER or '(empty)'}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"SITE_BASE_URL: {settings.SITE_BASE_URL}")

        if backend.endswith("console.EmailBackend"):
            self.stdout.write(
                self.style.WARNING(
                    "SMTP is not configured — emails print to the console only. "
                    "Set EMAIL_HOST and EMAIL_HOST_USER in .env."
                )
            )
            return

        to_email = options.get("to_email")
        if not to_email:
            self.stdout.write(
                self.style.SUCCESS(
                    "SMTP appears configured. Run with --to your@email.com to send a test."
                )
            )
            return

        send_mail(
            subject="Kokkoris Pet Food — δοκιμαστικό email",
            message="Το SMTP λειτουργεί σωστά.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Test email sent to {to_email}"))
