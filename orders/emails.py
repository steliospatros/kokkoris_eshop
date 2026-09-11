"""Transactional emails for orders."""
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from accounts.emails import welcome_display_name
from accounts.profile_labels import ORDER_STATUS_LABELS
from orders.models import Order
from orders.presentation import build_order_detail_context

_IMAGE_SUBTYPES = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".gif": "gif",
    ".webp": "webp",
}


def _site_base_url() -> str:
    return getattr(settings, "SITE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _attach_product_images(message: EmailMultiAlternatives, item_rows: list) -> None:
    """Embed product photos inline so they show in Gmail without public URLs."""
    for index, row in enumerate(item_rows):
        path = Path(row.get("image_path") or "")
        if not path.is_file():
            continue
        subtype = _IMAGE_SUBTYPES.get(path.suffix.lower(), "jpeg")
        cid = f"product{index}"
        with path.open("rb") as handle:
            image = MIMEImage(handle.read(), _subtype=subtype)
        image.add_header("Content-ID", f"<{cid}>")
        image.add_header("Content-Disposition", "inline", filename=path.name)
        message.attach(image)
        row["image_cid"] = cid


def build_order_status_intro(order: Order, *, previous_status=None, is_new=False) -> str:
    """Polite, formal Greek explanation of why the customer received this email."""
    thanks = " Σας ευχαριστούμε θερμά που προτιμήσατε το κατάστημά μας."
    details_note = " Παρακάτω θα βρείτε όλα τα στοιχεία της παραγγελίας σας."
    if is_new:
        if order.payment_method == Order.PAYMENT_METHOD_CARD:
            return (
                "Σας ενημερώνουμε ότι η παραγγελία σας καταχωρήθηκε με επιτυχία "
                "και η πληρωμή με κάρτα ολοκληρώθηκε."
                + thanks
                + details_note
            )
        return (
            "Σας ενημερώνουμε ότι η παραγγελία σας καταχωρήθηκε με επιτυχία. "
            "Η πληρωμή θα πραγματοποιηθεί με αντικαταβολή κατά την παράδοση."
            + thanks
            + details_note
        )

    status = order.status
    if status == Order.STATUS_CANCELLATION_REQUESTED:
        return (
            "Λάβαμε το αίτημά σας για ακύρωση της παραγγελίας. Η ομάδα μας θα "
            "το εξετάσει και θα σας ενημερώσουμε σχετικά με την επιστροφή "
            "χρημάτων, εφόσον αυτή προβλέπεται."
        )
    if status in (Order.STATUS_CANCELLED, Order.STATUS_FAILED):
        reason = (order.cancellation_reason or "").strip()
        if reason:
            return (
                "Σας ενημερώνουμε ότι η παραγγελία σας ακυρώθηκε. "
                f"Λόγος ακύρωσης: {reason}"
            )
        return "Σας ενημερώνουμε ότι η παραγγελία σας ακυρώθηκε."
    if status == Order.STATUS_DELIVERED:
        return (
            "Σας ενημερώνουμε ότι η παραγγελία σας παραδόθηκε με επιτυχία. "
            "Σας ευχαριστούμε για την εμπιστοσύνη σας."
            + details_note
        )

    previous_label = ORDER_STATUS_LABELS.get(previous_status, previous_status or "")
    current_label = ORDER_STATUS_LABELS.get(status, order.get_status_display())
    if previous_label:
        return (
            "Σας ενημερώνουμε ότι η κατάσταση της παραγγελίας σας άλλαξε "
            f"από «{previous_label}» σε «{current_label}»."
        )
    return (
        "Σας ενημερώνουμε ότι η κατάσταση της παραγγελίας σας είναι πλέον "
        f"«{current_label}»."
    )


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
        "greeting_name": welcome_display_name(order.user),
        "brand_contact_email": settings.BRAND_CONTACT_EMAIL,
    }

    if is_new:
        subject = f"Η παραγγελία σας {order.public_code_display} καταχωρήθηκε"
    elif is_delivered:
        subject = f"Η παραγγελία σας {order.public_code_display} παραδόθηκε"
    elif (not is_new) and order.status == Order.STATUS_CANCELLED:
        subject = f"Η παραγγελία σας {order.public_code_display} ακυρώθηκε"
    else:
        subject = (
            f"Ενημέρωση παραγγελίας {order.public_code_display} — "
            f"{context['status_label']}"
        )

    text_body = render_to_string("emails/order_update.txt", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    _attach_product_images(message, context["item_rows"])
    html_body = render_to_string("emails/order_update.html", context)
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
    return True
