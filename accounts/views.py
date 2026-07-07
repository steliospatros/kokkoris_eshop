from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm


@login_required
def profile_view(request):
    """
    Displays and lets the customer edit their own profile: name and
    delivery details. Registration itself only asks for email/password
    (handled by allauth); everything here is optional and usually filled
    in around the time of a customer's first order.
    """
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Το προφίλ σου ενημερώθηκε.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "accounts/profile.html", {"form": form})
