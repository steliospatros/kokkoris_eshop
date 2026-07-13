from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
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
    Lets a customer cancel their own order themselves, but only while it is
    still 'new' or 'pending' (see Order.can_be_cancelled_by_customer).
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.can_be_cancelled_by_customer():
        release_stock_for_order(order)
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status"])
        messages.success(request, "Η παραγγελία ακυρώθηκε.")
    else:
        messages.error(request, "Αυτή η παραγγελία δεν μπορεί να ακυρωθεί πλέον.")
    return redirect("orders:detail", order_id=order.id)
