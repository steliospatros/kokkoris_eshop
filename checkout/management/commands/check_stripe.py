from django.conf import settings
from django.core.management.base import BaseCommand

from checkout.stripe_service import stripe_payments_enabled


class Command(BaseCommand):
    help = "Verify Stripe API keys are configured for card checkout."

    def handle(self, *args, **options):
        if not stripe_payments_enabled():
            self.stdout.write(
                self.style.WARNING(
                    "Stripe is NOT configured. Add STRIPE_PUBLISHABLE_KEY and "
                    "STRIPE_SECRET_KEY to .env (see .env.example)."
                )
            )
            return

        import stripe

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            account = stripe.Account.retrieve()
        except stripe.error.AuthenticationError:
            self.stdout.write(self.style.ERROR("Stripe secret key is invalid."))
            return

        self.stdout.write(self.style.SUCCESS("Stripe keys are valid."))
        self.stdout.write(f"Account: {account.get('id', 'unknown')}")
        if not settings.STRIPE_WEBHOOK_SECRET:
            self.stdout.write(
                self.style.WARNING(
                    "STRIPE_WEBHOOK_SECRET is empty — webhooks will not verify yet."
                )
            )
