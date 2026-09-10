"""Binary sensor platform for YoLink Local integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import YoLocalCoordinator
from .entity import YoLocalEntity


DEVICE_TYPE_TO_CLASS = {
    "DoorSensor": BinarySensorDeviceClass.DOOR,
    "LeakSensor": BinarySensorDeviceClass.MOISTURE,
}

DEVICE_TYPE_TO_ON_STATE = {
    "DoorSensor": "open",
    "LeakSensor": "alert",
}

# Water meter controller alarm states, from the WaterMeterController spec
# (``data.alarm.<key>``). Each becomes a binary sensor that is "on" while the
# corresponding alarm is active.
WATER_ALARM_SENSORS: list[tuple[str, str, BinarySensorDeviceClass]] = [
    ("leak", "Leak", BinarySensorDeviceClass.MOISTURE),
    ("valveError", "Valve error", BinarySensorDeviceClass.PROBLEM),
    ("freezeError", "Freeze error", BinarySensorDeviceClass.PROBLEM),
    ("amountOverrun", "Overrun amount", BinarySensorDeviceClass.PROBLEM),
    ("durationOverrun", "Overrun duration", BinarySensorDeviceClass.PROBLEM),
    ("openReminder", "Valve left open", BinarySensorDeviceClass.PROBLEM),
    ("reminder", "Reminder", BinarySensorDeviceClass.PROBLEM),
]


def _state_value(state: dict[str, Any], key: str) -> Any:
    """Read a key from a device state, handling both flat and nested shapes."""
    nested = state.get("state")
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return state.get(key)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YoLink binary sensors from a config entry."""
    coordinator: YoLocalCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []
    for device in coordinator.devices.values():
        if device.device_type in DEVICE_TYPE_TO_CLASS:
            entities.append(YoLocalBinarySensor(coordinator, device))
        elif device.device_type == "WaterMeterController":
            # Real flow state (state.waterFlowing) — not a valve-position proxy.
            entities.append(YoLocalWaterFlowBinarySensor(coordinator, device))
            for alarm_key, name, cls in WATER_ALARM_SENSORS:
                entities.append(
                    YoLocalWaterAlarmBinarySensor(
                        coordinator, device, alarm_key, name, cls
                    )
                )

    async_add_entities(entities)


class YoLocalBinarySensor(YoLocalEntity, BinarySensorEntity):
    """Binary sensor for YoLink door/leak sensors."""

    _attr_name = None  # Use device name

    def __init__(self, coordinator: YoLocalCoordinator, device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_device_class = DEVICE_TYPE_TO_CLASS.get(device.device_type)
        self._on_state = DEVICE_TYPE_TO_ON_STATE.get(device.device_type, "open")

    @property
    def is_on(self) -> bool | None:
        """Return True if the sensor is triggered."""
        state = self.device_state.get("state", {})
        if isinstance(state, dict):
            sensor_state = state.get("state")
        else:
            sensor_state = state

        if sensor_state is None:
            return None
        return sensor_state == self._on_state


class YoLocalWaterFlowBinarySensor(YoLocalEntity, BinarySensorEntity):
    """Water-flowing binary sensor for the YoLink water meter controller.

    Reads ``state.waterFlowing`` (a boolean) directly from the hub — this is
    the actual flow state, not a proxy for the valve position.
    """

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_name = "Water flowing"

    def __init__(self, coordinator: YoLocalCoordinator, device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.device_id}_water_flowing"

    @property
    def is_on(self) -> bool | None:
        """Return True while water is flowing."""
        flowing = _state_value(self.device_state, "waterFlowing")
        if flowing is None:
            return None
        if isinstance(flowing, str):
            return flowing.strip().lower() in ("true", "1", "yes", "on")
        return bool(flowing)


class YoLocalWaterAlarmBinarySensor(YoLocalEntity, BinarySensorEntity):
    """Alarm binary sensor for a YoLink water meter controller alarm state."""

    def __init__(
        self,
        coordinator: YoLocalCoordinator,
        device,
        alarm_key: str,
        name: str,
        device_class: BinarySensorDeviceClass,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_device_class = device_class
        self._attr_name = name
        self._attr_unique_id = f"{device.device_id}_alarm_{alarm_key}"
        self._alarm_key = alarm_key

    @property
    def is_on(self) -> bool | None:
        """Return True while this alarm is active."""
        alarm = self.device_state.get("alarm")
        if not isinstance(alarm, dict):
            return None
        value = alarm.get(self._alarm_key)
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes", "on")
        return bool(value)
