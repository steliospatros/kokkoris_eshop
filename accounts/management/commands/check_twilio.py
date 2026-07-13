import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.sms import is_sms_configured


class Command(BaseCommand):
    help = "Diagnose Twilio SMS setup — exact cause of Greece delivery failures."

    def handle(self, *args, **options):
        sid = settings.TWILIO_ACCOUNT_SID
        token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_PHONE_NUMBER
        messaging_sid = settings.TWILIO_MESSAGING_SERVICE_SID
        alpha = settings.TWILIO_ALPHANUMERIC_SENDER

        self.stdout.write(self.style.HTTP_INFO("=== Twilio SMS diagnosis ===\n"))

        if not (sid and token):
            self.stdout.write(self.style.ERROR("✗ Missing TWILIO_ACCOUNT_SID or AUTH_TOKEN"))
            return

        if not is_sms_configured():
            self.stdout.write(self.style.ERROR("✗ No sender configured"))
            return

        base = f"https://api.twilio.com/2010-04-01/Accounts/{sid}"
        auth = (sid, token)

        acc = requests.get(f"{base}.json", auth=auth, timeout=15).json()
        account_type = acc.get("type", "?")
        self.stdout.write(f"Account type: {account_type}")

        self.stdout.write("\nSender config in .env:")
        self.stdout.write(f"  TWILIO_PHONE_NUMBER          = {from_number or '(not set)'}")
        self.stdout.write(f"  TWILIO_ALPHANUMERIC_SENDER   = {alpha or '(not set)'}")
        self.stdout.write(f"  TWILIO_MESSAGING_SERVICE_SID = {messaging_sid or '(not set)'}")

        if from_number and from_number.startswith("+1") and not alpha and not messaging_sid:
            self.stdout.write(
                self.style.ERROR(
                    "\n✗ PROBLEM FOUND:\n"
                    "  US long code (+1) cannot send SMS to Greece (+30).\n"
                    "  Twilio Greece guidelines: 'Long code international → Not Supported'.\n"
                    "  This is NOT a Geo permissions issue.\n"
                    "\n  FIX — add to .env:\n"
                    "    TWILIO_ALPHANUMERIC_SENDER=Kokkoris\n"
                    "  Then restart the server and test again.\n"
                    "\n  Alternative: create a Messaging Service with alphanumeric sender\n"
                    "  and set TWILIO_MESSAGING_SERVICE_SID=MGxxxxxxxx\n"
                )
            )

        # Route test: US virtual phone vs Greece
        if from_number:
            self.stdout.write("\nRoute test (using TWILIO_PHONE_NUMBER as From):")
            for to, label in [("+18777804236", "US virtual phone"), ("+306985019738", "Greece mobile")]:
                r = requests.post(
                    f"{base}/Messages.json",
                    auth=auth,
                    data={"From": from_number, "To": to, "Body": "route test"},
                    timeout=15,
                )
                if r.status_code < 400:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {label}: OK"))
                else:
                    body = r.json()
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ {label}: error {body.get('code')} — {body.get('message', '')[:80]}"
                        )
                    )

        if alpha:
            self.stdout.write(f"\nRoute test (alphanumeric From={alpha}):")
            r = requests.post(
                f"{base}/Messages.json",
                auth=auth,
                data={"From": alpha, "To": "+306985019738", "Body": "route test"},
                timeout=15,
            )
            if r.status_code < 400:
                self.stdout.write(self.style.SUCCESS("  ✓ Greece via alphanumeric: OK"))
            else:
                body = r.json()
                code = body.get("code")
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Greece via alphanumeric: error {code} — {body.get('message', '')[:80]}"
                    )
                )
                if code == 21267:
                    self.stdout.write(
                        self.style.WARNING(
                            "  → Alphanumeric sender blocked on TRIAL accounts.\n"
                            "  → Upgrade Twilio account to send SMS to Greece.\n"
                        )
                    )

        if account_type.lower() == "trial":
            self.stdout.write(
                self.style.WARNING(
                    "\n=== TRIAL SUMMARY ===\n"
                    "  1. US +1 → Greece (+30) = blocked (error 21612) — NOT Geo permissions\n"
                    "  2. Alphanumeric sender = blocked on trial (error 21267)\n"
                    "  3. Only fix: Upgrade account (100 free SMS after upgrade)\n"
                    "     console.twilio.com → Upgrade your account\n"
                )
            )
