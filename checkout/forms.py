from django import forms

from accounts.forms import ProfileForm
from orders.models import Order


class CheckoutProfileForm(ProfileForm):
    """Profile delivery fields — all required at checkout."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
