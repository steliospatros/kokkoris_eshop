"""Transactional emails for orders."""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from accounts.profile_labels import ORDER_STATUS_LABELS
from orders.models import Order
from orders.presentation import build_order_detail_context


def _site_base_url() -> str:
    return getattr(settings, "SITE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def build_order_status_intro(order: Order, *, previous_status=None, is_new=False) -> str:
    """Short Greek explanation of why the customer received this email."""
    details_note = (
        " Παρακάτω θα βρεις όλα τα στοιχεία, τα προϊόντα και το κόστος της παραγγελίας."
    )
    if is_new:
        if order.payment_method == Order.PAYMENT_METHOD_CARD:
            return (
                "Η παραγγελία σου καταχωρήθηκε και η πληρωμή με κάρτα "
                "ολοκληρώθηκε επιτυχώς."
                + details_note
            )
        return (
            "Η παραγγελία σου καταχωρήθηκε. Θα πληρώσεις με αντικαταβολή "
            "κατά την παράδοση."
            + details_note
        )

    status = order.status
    if status == Order.STATUS_CANCELLATION_REQUESTED:
        return (
            "Λάβαμε το αίτημα ακύρωσης της παραγγελίας σου. Η ομάδα μας θα "
            "το εξετάσει και θα ενημερωθείς για την επιστροφή χρημάτων, αν ισχύει."
        )
    if status == Order.STATUS_CANCELLED:
        return "Η παραγγελία σου ακυρώθηκε."
    if status == Order.STATUS_DELIVERED:
        return (
            "Η παραγγελία σου παραδόθηκε. Σε ευχαριστούμε που επέλεξες "
            "το Kokkoris Pet Food."
            + details_note
        )
    if status == Order.STATUS_PAID:
        return "Η παραγγελία σου επισημάνθηκε ως πληρωμένη."
    if status == Order.STATUS_FAILED:
        return "Η πληρωμή της παραγγελίας σου δεν ολοκληρώθηκε."

    previous_label = ORDER_STATUS_LABELS.get(previous_status, previous_status or "")
    current_label = ORDER_STATUS_LABELS.get(status, order.get_status_display())
    if previous_label:
        return f"Η κατάσταση της παραγγελίας σου άλλαξε από «{previous_label}» σε «{current_label}»."
    return f"Η κατάσταση της παραγγελίας σου είναι πλέον «{current_label}»."


def send_order_status_email(order: Order, *, previous_status=None, is_new=False) -> bool:
    """Send order confirmation or status-update email to the customer."""
    recipient = (order.user.email or "").strip()
    if not recipient:
        return False

    detail_url = (
        f"{_site_base_url()}"
        f"{reverse('orders:detail', kwargs={'order_id': order.pk})}"
    )
    is_new = bool(is_new)
    is_delivered = (not is_new) and order.status == Order.STATUS_DELIVERED
    context = {
        **build_order_detail_context(order),
        "status_intro": build_order_status_intro(
            order,
            previous_status=previous_status,
            is_new=is_new,
        ),
        "is_new_order": is_new,
        "is_delivered_order": is_delivered,
        "detail_url": detail_url,
        "site_name": "Kokkoris Pet Food",
    }

    if is_new:
        subject = f"Η παραγγελία σου {order.public_code_display} καταχωρήθηκε"
    elif is_delivered:
        subject = f"Η παραγγελία σου {order.public_code_display} παραδόθηκε"
    else:
        subject = (
            f"Ενημέρωση παραγγελίας {order.public_code_display} — "
            f"{context['status_label']}"
        )

    text_body = render_to_string("emails/order_update.txt", context)
    html_body = render_to_string("emails/order_update.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
    return True
