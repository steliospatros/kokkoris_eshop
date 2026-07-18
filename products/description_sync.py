"""
Keep product descriptions aligned with current Greek product titles.

Generated copy often embeds the old English / literal title in guillemets
(«…») and still says «φυλών». This module rewrites those to match the
storefront name and the «ράτσα» vocabulary.
"""
from __future__ import annotations

import re

_GUILLEMET_TITLE_RE = re.compile(r"«[^»]+»")

# Longer / more specific phrases first.
_FYLI_REPLACEMENTS: list[tuple[str, str]] = [
    ("όλων των φυλών", "κάθε ράτσας"),
    ("Όλων των φυλών", "κάθε ράτσας"),
    ("μεγαλόσωμων φυλών", "μεγαλόσωμων ρατσών"),
    ("μικρόσωμων φυλών", "μικρόσωμων ρατσών"),
    ("μεσαίων φυλών", "μεσαίων ρατσών"),
    ("φυλών", "ρατσών"),
    ("φυλές", "ράτσες"),
    ("φυλή", "ράτσα"),
]


def sync_description_title(description: str, product_name: str) -> str:
    """
    Replace the first «quoted title» with ``product_name`` and normalise
    φυλή → ράτσα wording throughout the description.
    """
    if not description:
        return description

    text = description
    if product_name and _GUILLEMET_TITLE_RE.search(text):
        text = _GUILLEMET_TITLE_RE.sub(f"«{product_name}»", text, count=1)

    for old, new in _FYLI_REPLACEMENTS:
        text = text.replace(old, new)

    return text
