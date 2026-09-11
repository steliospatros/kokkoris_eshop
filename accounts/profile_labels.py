"""Shared labels for account profile fields (Greek UI)."""
from django.utils.translation import gettext_lazy as _

# Editable via «Τα στοιχεία μου» — order shown in the details page.
PROFILE_EDITABLE_FIELDS = (
    ("first_name", _("Όνομα")),
    ("last_name", _("Επώνυμο")),
    ("phone_number", _("Τηλέφωνο")),
    ("address", _("Αναζήτηση διεύθυνσης")),
    ("city", _("Πόλη")),
    ("area", _("Περιοχή")),
    ("street", _("Δρόμος")),
    ("street_number", _("Αριθμός")),
    ("postal_code", _("Τ.Κ.")),
    ("floor", _("Όροφος")),
    ("doorbell_name", _("Όνομα κουδουνιού")),
    ("delivery_notes", _("Ειδικά σχόλια")),
)

ORDER_STATUS_LABELS = {
    "new": _("Καταχωρήθηκε"),
    "pending": _("Καταχωρήθηκε"),
    "paid": _("Καταχωρήθηκε"),
    "delivered": _("Παραδόθηκε"),
    "cancelled": _("Ακυρωμένη"),
    "failed": _("Ακυρωμένη"),
    "cancel_req": _("Αίτημα ακύρωσης"),
}

PAYMENT_METHOD_LABELS = {
    "card": _("Κάρτα"),
    "cash_on_delivery": _("Αντικαταβολή"),
}

# Settlement, not fulfillment: see Order.payment_state().
PAYMENT_STATE_LABELS = {
    "prepaid": _("Εξοφλήθηκε με κάρτα"),
    "collected": _("Εξοφλήθηκε"),
    "due_on_delivery": _("Αναμένεται πληρωμή κατά την παράδοση"),
    "refunded": _("Επιστροφή χρημάτων"),
    "not_charged": _("Δεν χρεώθηκε"),
}

DELIVERY_METHOD_LABELS = {
    "company_delivery": _("Παράδοση από υπάλληλο"),
    "courier": _("Αποστολή με courier"),
    "box_now": _("BOX NOW locker"),
}
