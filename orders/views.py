from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Order


@login_required
@require_POST
def cancel_order_view(request, order_id):
    """
    Lets a customer cancel their own order themselves, but only while it is
    still 'new' or 'pending' (see Order.can_be_cancelled_by_customer). Once
    paid/shipped, cancellation must go through staff instead (e.g. to handle
    a refund) - not built here.

    POST-only (not a GET link) so the order can never be cancelled by
    accident via a crawler or link preview. get_object_or_404 is scoped to
    user=request.user so nobody can ever cancel someone else's order.
    Cancelling never deletes the order - it only changes its status, in
    line with the "no order is ever deleted" policy.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.can_be_cancelled_by_customer():
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status"])
        messages.success(request, "Η παραγγελία ακυρώθηκε.")
    else:
        messages.error(request, "Αυτή η παραγγελία δεν μπορεί να ακυρωθεί πλέον.")
    return redirect("checkout:confirmation", order_id=order.id)
