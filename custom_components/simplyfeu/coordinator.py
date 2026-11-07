"""Coordinateur de mise à jour SimplyFeu."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SimplyFeuClient, SimplyFeuConnectionError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_PRICE_CHANGED,
    LOGGER,
    STORAGE_VERSION,
)
from .parser import PriceNotFoundError

type SimplyFeuConfigEntry = ConfigEntry[SimplyFeuCoordinator]


@dataclass(frozen=True, slots=True)
class SimplyFeuData:
    """Données exposées aux entités."""

    price: float
    product_name: str | None
    previous_price: float | None
    last_change: str | None
    lowest_price: float
    lowest_price_date: str


def storage_key(entry_id: str) -> str:
    return f"{DOMAIN}.{entry_id}"


class SimplyFeuCoordinator(DataUpdateCoordinator[SimplyFeuData]):
    """Relève le prix et mémorise l'historique (prix précédent, plus bas)."""

    config_entry: SimplyFeuConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SimplyFeuConfigEntry,
        client: SimplyFeuClient,
    ) -> None:
        hours = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN} {entry.title}",
            config_entry=entry,
            update_interval=timedelta(hours=hours),
        )
        self.client = client
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, storage_key(entry.entry_id)
        )
        self._history: dict[str, Any] = {}

    async def _async_setup(self) -> None:
        self._history = await self._store.async_load() or {}

    async def _async_update_data(self) -> SimplyFeuData:
        try:
            info = await self.client.async_fetch()
        except SimplyFeuConnectionError as err:
            raise UpdateFailed(f"Page inaccessible : {err}") from err
        except PriceNotFoundError as err:
            raise UpdateFailed(
                "Prix introuvable dans la page ; "
                "renseignez une regex personnalisée dans les options"
            ) from err

        now = dt_util.utcnow().isoformat()
        hist = self._history
        last_price: float | None = hist.get("last_price")
        lowest: float | None = hist.get("lowest_price")

        changed = last_price is not None and info.price != last_price
        new_low = lowest is None or info.price < lowest

        if new_low:
            hist["lowest_price"] = info.price
            hist["lowest_price_date"] = now
        if changed:
            hist["previous_price"] = last_price
            hist["last_change"] = now
        if last_price is None or changed or new_low:
            hist["last_price"] = info.price
            await self._store.async_save(hist)

        if changed:
            self.hass.bus.async_fire(
                EVENT_PRICE_CHANGED,
                {
                    "entry_id": self.config_entry.entry_id,
                    "name": self.config_entry.title,
                    "url": self.client.url,
                    "old_price": last_price,
                    "new_price": info.price,
                    "lowest_price": hist["lowest_price"],
                    "is_new_low": new_low,
                },
            )

        return SimplyFeuData(
            price=info.price,
            product_name=info.name,
            previous_price=hist.get("previous_price"),
            last_change=hist.get("last_change"),
            lowest_price=hist["lowest_price"],
            lowest_price_date=hist["lowest_price_date"],
        )
