"""Intégration SimplyFeu : suivi du prix des granulés."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import SimplyFeuClient
from .const import CONF_COOKIE, CONF_PRICE_REGEX, CONF_URL, STORAGE_VERSION
from .coordinator import SimplyFeuConfigEntry, SimplyFeuCoordinator, storage_key

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SimplyFeuConfigEntry) -> bool:
    """Configure une entrée."""
    client = SimplyFeuClient(
        async_get_clientsession(hass),
        entry.data[CONF_URL],
        cookie=entry.options.get(CONF_COOKIE),
        price_regex=entry.options.get(CONF_PRICE_REGEX),
    )
    coordinator = SimplyFeuCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SimplyFeuConfigEntry) -> bool:
    """Décharge une entrée."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: SimplyFeuConfigEntry) -> None:
    """Supprime l'historique stocké quand l'entrée est supprimée."""
    await Store(hass, STORAGE_VERSION, storage_key(entry.entry_id)).async_remove()


async def _async_reload_entry(hass: HomeAssistant, entry: SimplyFeuConfigEntry) -> None:
    """Recharge l'entrée après modification des options."""
    await hass.config_entries.async_reload(entry.entry_id)
