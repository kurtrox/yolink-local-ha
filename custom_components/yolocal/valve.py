"""Valve platform for YoLink Local integration (water meter controller valve)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import YoLocalCoordinator
from .entity import YoLocalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YoLink valves from a config entry."""
    coordinator: YoLocalCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ValveEntity] = []
    for device in coordinator.devices.values():
        if device.device_type == "WaterMeterController":
            entities.append(YoLocalValve(coordinator, device))

    async_add_entities(entities)


class YoLocalValve(YoLocalEntity, ValveEntity):
    """Valve entity for the YoLink water meter controller."""

    _attr_device_class = ValveDeviceClass.WATER
    _attr_name = "Valve"
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    def __init__(self, coordinator: YoLocalCoordinator, device) -> None:
        """Initialize the valve."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.device_id}_valve"

    @property
    def is_closed(self) -> bool | None:
        """Return True if the valve is closed.

        WaterMeterController reports ``state.valve`` as "open" or "close"
        per the protocol docs, but some firmware versions report booleans
        or numbers, so accept all common encodings.
        """
        state = self.device_state
        nested = state.get("state")
        valve = nested.get("valve") if isinstance(nested, dict) else state.get("valve")
        if valve is None:
            return None
        if isinstance(valve, str):
            v = valve.strip().lower()
            if v in ("open", "close", "closed"):
                return v in ("close", "closed")
            if v in ("0", "1"):
                return v == "0"
        elif isinstance(valve, bool):
            return not valve
        elif isinstance(valve, (int, float)):
            return valve == 0
        _LOGGER.warning("Unrecognized valve state for %s: %r", self._device.name, valve)
        return None

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        await self.coordinator.async_send_command(
            self._device.device_id,
            {"valve": "open"},
        )

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        await self.coordinator.async_send_command(
            self._device.device_id,
            {"valve": "close"},
        )
