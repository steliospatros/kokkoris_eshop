from django.http import Http404
from django.shortcuts import render

from .content import INFO_PAGES


def info_page_view(request, slug):
    page = INFO_PAGES.get(slug)
    if page is None:
        raise Http404
    return render(request, "pages/info.html", {"page": page})
