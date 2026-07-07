def nav_state(request):
    """Expose homepage flag so nav can pick the correct butterfly placement."""
    match = getattr(request, "resolver_match", None)
    is_homepage = match is not None and match.url_name == "home"
    return {"is_homepage": is_homepage}
