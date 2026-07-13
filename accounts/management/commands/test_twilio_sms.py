from django.core.management.base import BaseCommand

from accounts.sms import SMSDeliveryError, send_sms


class Command(BaseCommand):
    help = "Send a test SMS via Twilio and print the exact error if it fails."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            default="6985019738",
            help="Greek mobile (10 digits, default 6985019738)",
        )

    def handle(self, *args, **options):
        to = options["to"]
        self.stdout.write(f"Sending test SMS to {to}…\n")
        try:
            send_sms(to, "Kokkoris test SMS")
        except SMSDeliveryError as exc:
            self.stdout.write(self.style.ERROR(f"FAILED: {exc}"))
            self.stdout.write(
                "\nIf error 21612 with US +1 sender:\n"
                "  → NOT Geo permissions. Greece blocks US long codes as sender.\n"
                "  → Add TWILIO_ALPHANUMERIC_SENDER=Kokkoris to .env\n"
            )
            return

        self.stdout.write(self.style.SUCCESS("OK — check your phone for the test message."))
