from django.http import Http404
from django.shortcuts import render

from .content import INFO_PAGES
from .store_location import (
    STORE_ADDRESS_LINE,
    build_store_maps_link,
    build_store_static_map_url,
)


def info_page_view(request, slug):
    page = INFO_PAGES.get(slug)
    if page is None:
        raise Http404
    context = {"page": page}
    if slug == "store":
        context.update(
            {
                "store_map_url": build_store_static_map_url(),
                "store_maps_link": build_store_maps_link(),
                "store_address_line": STORE_ADDRESS_LINE,
            }
        )
    return render(request, "pages/info.html", context)
