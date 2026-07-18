from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Order
from .presentation import build_order_detail_context
from .stock import release_stock_for_order


@login_required
def order_detail_view(request, order_id):
    """Full order detail page for order history."""
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product_variant__product"),
        id=order_id,
        user=request.user,
    )
    context = build_order_detail_context(order)
    return render(request, "orders/detail.html", context)


@login_required
@require_POST
def cancel_order_view(request, order_id):
    """
    Unpaid orders: immediate cancel + stock release.

    Paid card orders: submit a cancellation/refund request for admin review.
    The admin panel will process the Stripe refund manually and then mark the
    order as cancelled.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.can_be_cancelled_by_customer():
        release_stock_for_order(order)
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status"])
        messages.success(request, "Η παραγγελία ακυρώθηκε.")
    elif order.can_request_cancellation():
        order.status = Order.STATUS_CANCELLATION_REQUESTED
        order.cancellation_requested_at = timezone.now()
        order.save(update_fields=["status", "cancellation_requested_at"])
        messages.info(
            request,
            "Το αίτημα ακύρωσης καταχώρηθηκε. Η ομάδα μας θα εξετάσει την "
            "αίτηση και, μετά την επιβεβαίωση, θα επιστραφούν τα χρήματα "
            "στην κάρτα σου.",
        )
    elif order.is_refund_pending():
        messages.info(request, "Το αίτημα ακύρωσης είναι ήδη σε εξέλιξη.")
    else:
        messages.error(request, "Αυτή η παραγγελία δεν μπορεί να ακυρωθεί πλέον.")

    return redirect("orders:detail", order_id=order.id)
