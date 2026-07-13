from django import forms

from accounts.forms import ProfileForm
from orders.models import Order


class CheckoutProfileForm(ProfileForm):
    """Profile delivery fields — all required at checkout."""

    def __init__(self, *args, phone_locked=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.phone_locked = phone_locked
        required = (
            "first_name",
            "last_name",
            "phone_number",
            "city",
            "street",
            "street_number",
            "postal_code",
            "floor",
        )
        for name in required:
            if name in self.fields:
                self.fields[name].required = True
        if phone_locked and self.instance.phone_verified_at:
            self.fields["phone_number"].disabled = True

    def clean_phone_number(self):
        if self.phone_locked and self.instance.phone_verified_at:
            return self.instance.phone_number
        return super().clean_phone_number()


class PaymentMethodForm(forms.Form):
    """Step 3 of checkout: how the customer will pay."""
    payment_method = forms.ChoiceField(
        choices=(
            (Order.PAYMENT_METHOD_COD, "Αντικαταβολή"),
            (Order.PAYMENT_METHOD_CARD, "Πληρωμή μέσω κάρτας"),
        ),
        widget=forms.RadioSelect,
        label="Τρόπος πληρωμής",
    )
