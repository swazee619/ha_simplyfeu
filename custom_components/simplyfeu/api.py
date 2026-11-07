"""Client HTTP pour récupérer la page produit."""

from __future__ import annotations

import asyncio

import aiohttp

from .parser import ProductInfo, extract_product

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) HomeAssistant-SimplyFeu"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}
_TIMEOUT = 30


class SimplyFeuConnectionError(Exception):
    """La page n'a pas pu être téléchargée."""


class SimplyFeuClient:
    """Télécharge et analyse une page produit."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        url: str,
        *,
        cookie: str | None = None,
        price_regex: str | None = None,
    ) -> None:
        self._session = session
        self._url = url
        self._price_regex = price_regex or None
        self._headers = dict(_HEADERS)
        if cookie:
            self._headers["Cookie"] = cookie

    @property
    def url(self) -> str:
        return self._url

    async def async_fetch(self) -> ProductInfo:
        """Télécharge la page et en extrait le prix."""
        try:
            async with asyncio.timeout(_TIMEOUT):
                async with self._session.get(
                    self._url, headers=self._headers, allow_redirects=True
                ) as resp:
                    resp.raise_for_status()
                    page = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SimplyFeuConnectionError(str(err)) from err

        return extract_product(page, self._price_regex)
