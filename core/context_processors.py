def breadcrumbs(request):
    return {"breadcrumbs": getattr(request, "breadcrumbs", [])}
