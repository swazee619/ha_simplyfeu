"""Extraction du prix d'une page produit (sans dépendance à Home Assistant)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import html
import json
import re
from typing import Any

MIN_PLAUSIBLE_PRICE = 1.0
MAX_PLAUSIBLE_PRICE = 5000.0

_NUM = r"[\d.,\s\u00a0\u202f]+?"

_HTML_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"""itemprop=["']price["'][^>]*?content=["'](?P<p>[\d.,]+)["']""", re.I
    ),
    re.compile(
        r"""content=["'](?P<p>[\d.,]+)["'][^>]*?itemprop=["']price["']""", re.I
    ),
    re.compile(rf"""itemprop=["']price["'][^>]*>\s*(?P<p>{_NUM})\s*<""", re.I),
    # Sites Odoo (dont SimplyFeu)
    re.compile(
        rf"""class=["'][^"']*\boe_currency_value\b[^"']*["'][^>]*>\s*(?P<p>{_NUM})\s*<""",
        re.I,
    ),
)

_JSONLD = re.compile(
    r"""<script[^>]+type=["']application/ld\+json["'][^>]*>(?P<j>.*?)</script>""",
    re.I | re.S,
)
_OG_TITLE = re.compile(
    r"""<meta[^>]+property=["']og:title["'][^>]+content=["'](?P<t>[^"']+)["']""", re.I
)
_TITLE = re.compile(r"<title[^>]*>(?P<t>.*?)</title>", re.I | re.S)


class PriceNotFoundError(Exception):
    """Aucun prix plausible n'a été trouvé dans la page."""


@dataclass(frozen=True, slots=True)
class ProductInfo:
    """Informations extraites de la page produit."""

    price: float
    name: str | None = None


def parse_price_text(raw: str) -> float:
    """Convertit « 1 234,56 € », « 493,00 » ou « 493.0 » en float."""
    clean = re.sub(r"[\s\u00a0\u202f€]", "", str(raw))
    if re.search(r",\d{1,2}$", clean):
        clean = clean.replace(".", "").replace(",", ".")
    else:
        clean = clean.replace(",", "")
    return float(clean)


def _plausible(value: float) -> bool:
    return MIN_PLAUSIBLE_PRICE <= value <= MAX_PLAUSIBLE_PRICE


def _iter_jsonld_prices(node: Any) -> Iterator[Any]:
    """Parcourt un JSON-LD et renvoie les valeurs des clés de prix des offres."""
    if isinstance(node, dict):
        for key in ("price", "lowPrice"):
            if key in node and not isinstance(node[key], (dict, list)):
                yield node[key]
        for value in node.values():
            yield from _iter_jsonld_prices(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_jsonld_prices(item)


def _candidates(page: str, custom_regex: str | None) -> Iterator[str]:
    if custom_regex:
        match = re.search(custom_regex, page, re.I | re.S)
        if match:
            yield match.group("p")

    for block in _JSONLD.finditer(page):
        try:
            data = json.loads(block.group("j"))
        except ValueError:
            continue
        for value in _iter_jsonld_prices(data):
            yield str(value)

    for pattern in _HTML_PATTERNS:
        for match in pattern.finditer(page):
            yield match.group("p")


def _extract_name(page: str) -> str | None:
    for pattern in (_OG_TITLE, _TITLE):
        if match := pattern.search(page):
            name = html.unescape(match.group("t")).strip()
            if name:
                return name.split("|")[0].strip()
    return None


def extract_product(page: str, custom_regex: str | None = None) -> ProductInfo:
    """Renvoie le premier prix plausible trouvé dans la page."""
    for raw in _candidates(page, custom_regex):
        try:
            price = parse_price_text(raw)
        except ValueError:
            continue
        if _plausible(price):
            return ProductInfo(price=round(price, 2), name=_extract_name(page))
    raise PriceNotFoundError("Aucun prix plausible trouvé dans la page")


def is_valid_price_regex(pattern: str) -> bool:
    """Vérifie qu'une regex compile et contient un groupe nommé « p »."""
    try:
        return "p" in re.compile(pattern).groupindex
    except re.error:
        return False
