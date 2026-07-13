from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import forms
from django.utils.translation import gettext_lazy as _

from allauth.account.forms import ResetPasswordKeyForm as AllauthResetPasswordKeyForm
from allauth.account.forms import SignupForm

from .address_utils import (
    normalize_postal_code,
    parse_address_components_json,
    parse_address_from_place_id,
    resolve_greek_city,
)
from .models import CustomUser
from .password_help import translate_form_error
from .phone_validation import validate_greek_mobile


class ResetPasswordKeyForm(AllauthResetPasswordKeyForm):
    def add_error(self, field, error):
        if getattr(error, "error_list", None):
            for item in error.error_list:
                super().add_error(field, translate_form_error(item))
            return
        super().add_error(field, translate_form_error(error))


class KokkorisSignupForm(SignupForm):
    """Email + password signup; phone is verified via SMS in the auth modal."""

    field_order = ["email", "password1", "password2"]


class ProfileForm(forms.ModelForm):
    """
    Lets a logged-in customer view/edit their own account details:
    name and the delivery details that get filled in around checkout time
    (Part 4 will pre-fill/save these automatically from the checkout form
    as well; this page lets the customer manage them directly too).
    """

    address_place_id = forms.CharField(required=False, widget=forms.HiddenInput())
    address_components_json = forms.CharField(required=False, widget=forms.HiddenInput())
    address_search = forms.CharField(
        required=False,
        label=_("Αναζήτηση διεύθυνσης"),
    )

    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "city",
            "area",
            "street",
            "street_number",
            "address",
            "postal_code",
            "floor",
            "doorbell_name",
            "delivery_notes",
            "latitude",
            "longitude",
        ]
        widgets = {
            "delivery_notes": forms.Textarea(attrs={"rows": 3}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "city": forms.HiddenInput(),
            "area": forms.HiddenInput(),
            "street": forms.HiddenInput(),
            "street_number": forms.HiddenInput(),
            "postal_code": forms.HiddenInput(),
            "address": forms.HiddenInput(),
        }

    STRUCTURED_ADDRESS_FIELDS = (
        "city",
        "area",
        "street",
        "street_number",
        "postal_code",
        "address",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            "w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm font-inter "
            "text-slate-800 focus:outline-none focus:border-kokkoris-teal-dark "
            "focus:ring-2 focus:ring-kokkoris-teal-dark/25"
        )
        for name, field in self.fields.items():
            if name in {
                "address_place_id",
                "address_components_json",
                "latitude",
                "longitude",
                "city",
                "area",
                "street",
                "street_number",
                "postal_code",
                "address",
            }:
                continue
            field.widget.attrs.setdefault("class", input_class)

    def clean_phone_number(self):
        value = self.cleaned_data.get("phone_number")
        if not value or not str(value).strip():
            return ""
        return validate_greek_mobile(value)

    def _round_coord(self, value):
        if value in (None, ""):
            return None
        return Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def full_clean(self):
        if self.data is not None:
            mutable = self.data.copy()
            for name in ("latitude", "longitude"):
                raw = mutable.get(name)
                if raw not in (None, ""):
                    try:
                        mutable[name] = str(self._round_coord(raw))
                    except (InvalidOperation, TypeError, ValueError):
                        pass
            self.data = mutable
        super().full_clean()

    def clean_latitude(self):
        return self._round_coord(self.cleaned_data.get("latitude"))

    def clean_longitude(self):
        return self._round_coord(self.cleaned_data.get("longitude"))

    def _structured_values(self, cleaned_data):
        values = {
            name: (cleaned_data.get(name) or "").strip()
            for name in self.STRUCTURED_ADDRESS_FIELDS
        }
        values["postal_code"] = normalize_postal_code(values["postal_code"])
        return values

    def _instance_structured_values(self):
        values = {
            name: (getattr(self.instance, name) or "").strip()
            for name in self.STRUCTURED_ADDRESS_FIELDS
        }
        values["postal_code"] = normalize_postal_code(values["postal_code"])
        return values

    def _coords_present(self, cleaned_data):
        return (
            cleaned_data.get("latitude") is not None
            and cleaned_data.get("longitude") is not None
        )

    def _coords_changed(self, cleaned_data):
        def as_float(value):
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        lat = as_float(cleaned_data.get("latitude"))
        lng = as_float(cleaned_data.get("longitude"))
        prev_lat = as_float(self.instance.latitude)
        prev_lng = as_float(self.instance.longitude)
        return lat != prev_lat or lng != prev_lng

    def clean(self):
        cleaned_data = super().clean()
        current = self._structured_values(cleaned_data)
        previous = self._instance_structured_values()
        has_any = any(current.values())
        structured_changed = any(
            current[name] != previous[name] for name in self.STRUCTURED_ADDRESS_FIELDS
        )
        coords_changed = self._coords_changed(cleaned_data)

        components_json = cleaned_data.get("address_components_json") or ""
        place_id = (cleaned_data.get("address_place_id") or "").strip()
        parsed = parse_address_from_place_id(place_id) if place_id else None
        if parsed is None:
            parsed = parse_address_components_json(components_json)

        if not has_any:
            cleaned_data["latitude"] = None
            cleaned_data["longitude"] = None
        else:
            # Hidden lat/lng can be cleared by the browser/JS while the customer
            # only edits floor or notes — keep the saved pin when address is unchanged.
            if not self._coords_present(cleaned_data) and not structured_changed:
                if self.instance.latitude is not None and self.instance.longitude is not None:
                    cleaned_data["latitude"] = self.instance.latitude
                    cleaned_data["longitude"] = self.instance.longitude
                    coords_changed = False

            if structured_changed:
                if parsed:
                    parsed_dict = parsed.as_dict()
                    for name in self.STRUCTURED_ADDRESS_FIELDS:
                        cleaned_data[name] = parsed_dict[name]
                    current = self._structured_values(cleaned_data)
                else:
                    self.add_error(
                        "address_search",
                        "Επίλεξε έγκυρη διεύθυνση από τη λίστα ή τον χάρτη.",
                    )

                if not (cleaned_data.get("address_place_id") or "").strip():
                    if not self._coords_present(cleaned_data):
                        self.add_error(
                            "address_search",
                            "Επίλεξε έγκυρη διεύθυνση από τη λίστα ή τον χάρτη.",
                        )
                if not self._coords_present(cleaned_data):
                    self.add_error(
                        "address_search",
                        "Επιβεβαίωσε την τοποθεσία στον χάρτη (κουκίδα ή αναζήτηση).",
                    )
                if not current["postal_code"]:
                    self.add_error(
                        "address_search",
                        "Επίλεξε πιο συγκεκριμένη διεύθυνση — δεν βρέθηκε Τ.Κ.",
                    )
                if not current["street"]:
                    self.add_error(
                        "address_search",
                        "Δεν βρέθηκε δρόμος — επίλεξε πιο συγκεκριμένη διεύθυνση.",
                    )

        if has_any and not current["city"]:
            self.add_error(
                "address_search",
                "Η πόλη λείπει — επίλεξε διεύθυνση από τη λίστα ή τον χάρτη.",
            )

        if current["postal_code"]:
            cleaned_data["city"] = resolve_greek_city(
                current["city"], current["postal_code"]
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user
