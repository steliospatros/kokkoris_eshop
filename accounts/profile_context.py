"""Shared profile form context for account details and checkout."""
from django.conf import settings

from accounts.floor_options import FLOOR_OTHER_LABEL, FLOOR_PRESET_OPTIONS
from accounts.profile_labels import PROFILE_EDITABLE_FIELDS
from accounts.views import (
    PROFILE_ADDRESS_AUTO_FIELDS,
    PROFILE_ADDRESS_EXTRA_FIELDS,
    PROFILE_ADDRESS_SEARCH_FIELD,
    _profile_address_auto_rows,
    _profile_address_extra_rows,
    _profile_address_search_row,
    _profile_field_rows,
)


def build_profile_form_context(user, form=None):
    return {
        "form": form,
        "field_rows": _profile_field_rows(user, form=form),
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "address_search_row": _profile_address_search_row(user, form=form),
        "address_auto_rows": _profile_address_auto_rows(user, form=form),
        "address_extra_rows": _profile_address_extra_rows(user, form=form),
        "floor_preset_options": FLOOR_PRESET_OPTIONS,
        "floor_other_label": FLOOR_OTHER_LABEL,
        "profile_editable_fields": PROFILE_EDITABLE_FIELDS,
        "profile_address_search_field": PROFILE_ADDRESS_SEARCH_FIELD,
        "profile_address_auto_fields": PROFILE_ADDRESS_AUTO_FIELDS,
        "profile_address_extra_fields": PROFILE_ADDRESS_EXTRA_FIELDS,
    }
