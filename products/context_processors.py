def nav_state(request):
    """Expose homepage flag and decorative page background for inner pages."""
    match = getattr(request, "resolver_match", None)
    url_name = getattr(match, "url_name", None) if match else None
    app_name = getattr(match, "app_name", None) if match else None
    is_homepage = match is not None and url_name == "home"

    page_background = None
    if not is_homepage:
        if app_name == "products" and url_name in ("dogs", "cats", "brands"):
            page_background = None
        else:
            page_background = "back1"

    return {
        "is_homepage": is_homepage,
        "page_background": page_background,
    }
