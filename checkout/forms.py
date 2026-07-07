from django import forms

from accounts.models import CustomUser
from orders.models import Order

# Shared Tailwind styling for plain text/textarea inputs, matching the
# temporary minimal style already used by accounts.forms.ProfileForm.
# (Full UI/UX pass happens in Part 5.)
_TEXT_INPUT_CLASS = (
    "w-full border border-slate-300 rounded px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-emerald-500"
)


class CheckoutAddressForm(forms.ModelForm):
    """
    Step 1 of checkout: delivery address. A ModelForm on CustomUser so that
    submitting it also permanently saves these details to the customer's
    profile (reused automatically on their next order). latitude/longitude
    are hidden inputs, populated by the Google Maps JavaScript on the
    template - the location *must* be confirmed via the map pin before the
    form can be submitted.
    """
    preferred_delivery_time = forms.CharField(
        max_length=100,
        required=False,
        label="Προτίμηση ώρας παράδοσης",
        widget=forms.TextInput(attrs={"placeholder": "π.χ. Τρίτη απόγευμα 5-7"}),
    )

    class Meta:
        model = CustomUser
        fields = [
            "phone_number", "city", "address", "postal_code", "floor",
            "latitude", "longitude", "delivery_notes",
        ]
        widgets = {
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "delivery_notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # These are optional on the CustomUser model itself (filled in over
        # time), but required at checkout time - the delivery location must
        # be fully known and map-validated before the order can proceed.
        for name in ("phone_number", "city", "address", "postal_code", "latitude", "longitude"):
            self.fields[name].required = True
        for name, field in self.fields.items():
            if name in ("latitude", "longitude"):
                continue
            field.widget.attrs.setdefault("class", _TEXT_INPUT_CLASS)


class PaymentMethodForm(forms.Form):
    """Step 3 of checkout: how the customer will pay."""
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect,
        label="Τρόπος πληρωμής",
    )
