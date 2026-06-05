"""JSON-LD structured data — the safe set.

BreadcrumbList + ItemList for the generated hub and budget pages. Deliberately
NO Offer/Product/price markup: the fares are directional ("best seen" + an
estimated ground cost), not bookable offers, so pricing them as Offers would
violate Google's structured-data policy and is a trust risk on travel/money
content. Organization + WebSite are hand-placed in index.html (homepage only).
"""
import json

BASE = "https://promptiv.io"


def _ld_script(graph: list) -> str:
    data = {"@context": "https://schema.org", "@graph": graph}
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # Prevent a literal "</script>" in any string value from breaking out.
    js = js.replace("</", "<\\/")
    return f'<script type="application/ld+json">{js}</script>'


def breadcrumb(crumbs: list) -> dict:
    """crumbs: list of (name, url) from root to current page."""
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(crumbs)
        ],
    }


def item_list(name: str, item_names: list) -> dict:
    """An ordered list of named items (no prices)."""
    return {
        "@type": "ItemList",
        "name": name,
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "numberOfItems": len(item_names),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n}
            for i, n in enumerate(item_names)
        ],
    }


def page_ld(crumbs: list, list_name: str, item_names: list) -> str:
    """The full <script> block for a list page (breadcrumb + item list)."""
    return _ld_script([breadcrumb(crumbs), item_list(list_name, item_names)])


def breadcrumb_ld(crumbs: list) -> str:
    """A <script> block with just the breadcrumb (for non-list pages)."""
    return _ld_script([breadcrumb(crumbs)])
