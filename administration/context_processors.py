from administration.permissions import user_is_administration_user


def administration_access(request):
    user = getattr(request, "user", None)
    return {
        "is_administration_user": user_is_administration_user(user) if user else False,
    }
