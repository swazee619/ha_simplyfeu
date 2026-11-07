"""Capteurs SimplyFeu."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_URL, DOMAIN
from .coordinator import SimplyFeuConfigEntry, SimplyFeuCoordinator, SimplyFeuData


@dataclass(frozen=True, kw_only=True)
class SimplyFeuSensorDescription(SensorEntityDescription):
    """Description d'un capteur SimplyFeu."""

    value_fn: Callable[[SimplyFeuData], float | None]
    attrs_fn: Callable[[SimplyFeuData], dict[str, Any]] = lambda _: {}


SENSORS: tuple[SimplyFeuSensorDescription, ...] = (
    SimplyFeuSensorDescription(
        key="price",
        translation_key="price",
        icon="mdi:fire",
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.price,
        attrs_fn=lambda d: {
            "product_name": d.product_name,
            "previous_price": d.previous_price,
            "last_change": d.last_change,
        },
    ),
    SimplyFeuSensorDescription(
        key="lowest_price",
        translation_key="lowest_price",
        icon="mdi:arrow-collapse-down",
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda d: d.lowest_price,
        attrs_fn=lambda d: {"date": d.lowest_price_date},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SimplyFeuConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(SimplyFeuSensor(coordinator, desc) for desc in SENSORS)


class SimplyFeuSensor(CoordinatorEntity[SimplyFeuCoordinator], SensorEntity):
    """Capteur de prix."""

    _attr_has_entity_name = True
    entity_description: SimplyFeuSensorDescription

    def __init__(
        self,
        coordinator: SimplyFeuCoordinator,
        description: SimplyFeuSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="SimplyFeu",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.data[CONF_URL],
        )

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attrs_fn(self.coordinator.data)
