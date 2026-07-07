from django import forms

from .models import CustomUser


class ProfileForm(forms.ModelForm):
    """
    Lets a logged-in customer view/edit their own account details:
    name and the delivery details that get filled in around checkout time
    (Part 4 will pre-fill/save these automatically from the checkout form
    as well; this page lets the customer manage them directly too).
    """

    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "city",
            "address",
            "postal_code",
            "floor",
            "delivery_notes",
        ]
        widgets = {
            "delivery_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply a consistent Tailwind style to every field's input widget.
        # (Temporary, minimal styling - the full UI/UX pass happens in Part 5.)
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "w-full border border-slate-300 rounded px-3 py-2 text-sm "
                "focus:outline-none focus:ring-2 focus:ring-emerald-500"
            )
