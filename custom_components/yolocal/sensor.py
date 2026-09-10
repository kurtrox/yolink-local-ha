"""Sensor platform for YoLink Local integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, METER_UNIT_TO_UNIT
from .coordinator import YoLocalCoordinator
from .entity import YoLocalEntity


def _state_value(state: dict[str, Any], key: str) -> Any:
    """Read a key from a device state, handling both flat and nested shapes.

    WaterMeterController reports ``state`` as an object
    (``state.valve``, ``state.meter``) while other devices report a flat
    dict at the top level.
    """
    nested = state.get("state")
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return state.get(key)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YoLink sensors from a config entry."""
    coordinator: YoLocalCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for device in coordinator.devices.values():
        if device.device_type == "THSensor":
            entities.append(YoLocalTemperatureSensor(coordinator, device))
            entities.append(YoLocalHumiditySensor(coordinator, device))
            entities.append(YoLocalBatterySensor(coordinator, device))
        elif device.device_type == "WaterMeterController":
            entities.append(YoLocalWaterMeterSensor(coordinator, device))
            entities.append(YoLocalWaterTempSensor(coordinator, device))
            entities.append(YoLocalBatterySensor(coordinator, device))

    async_add_entities(entities)


class YoLocalTemperatureSensor(YoLocalEntity, SensorEntity):
    """Temperature sensor for YoLink THSensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_name = "Temperature"

    def __init__(self, coordinator: YoLocalCoordinator, device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.device_id}_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the temperature."""
        return _state_value(self.device_state, "temperature")


class YoLocalHumiditySensor(YoLocalEntity, SensorEntity):
    """Humidity sensor for YoLink THSensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_name = "Humidity"

    def __init__(self, coordinator: YoLocalCoordinator, device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.device_id}_humidity"

    @property
    def native_value(self) -> float | None:
        """Return the humidity."""
        state = self.device_state.get("state", {})
        if isinstance(state, dict):
            return state.get("humidity")
        return self.device_state.get("humidity")


class YoLocalBatterySensor(YoLocalEntity, SensorEntity):
    """Battery sensor for YoLink devices."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_name = "Battery"

    def __init__(self, coordinator: YoLocalCoordinator, device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.device_id}_battery"

    @property
    def native_value(self) -> int | None:
        """Return the battery level as percentage."""
        level = _state_value(self.device_state, "battery")

        if level is None:
            return None
        # YoLink reports 0-4, convert to percentage
        return min(level * 25, 100)


class YoLocalWaterMeterSensor(YoLocalEntity, SensorEntity):
    """Cumulative water consumption for the YoLink water meter controller.

    The hub reports ``state.meter`` as a raw pulse count. The real volume is
    resolved by the coordinator, which prefers the device's own meter
    attributes (``attributes.meterStepFactor`` + ``attributes.meterUnit`` —
    the same conversion the YoLink app uses) and falls back to a user-set
    calibration baseline when those are absent. The sensor's unit follows the
    meter's configured unit (GAL / CCF / M3 / L).
    """

    _attr_name = "Water usage"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.WATER

    def __init__(self, coordinator: YoLocalCoordinator, device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.device_id}_water_meter"

    @property
    def _reading(self) -> dict[str, Any]:
        return self.coordinator.get_meter_reading(self._device.device_id)

    @property
    def native_value(self) -> float | None:
        """Return the cumulative water usage in the meter's unit."""
        reading = self._reading
        return reading.get("value")

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Follow the meter's configured unit; default to gallons."""
        reading = self._reading
        unit = reading.get("unit")
        if unit:
            return unit
        # No resolution yet: default unit so the WATER device class is valid.
        return METER_UNIT_TO_UNIT.get(0, "gal")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw count and how the reading was resolved."""
        reading = self._reading
        attrs: dict[str, Any] = {}
        if reading.get("raw") is not None:
            attrs["raw_meter"] = reading["raw"]
        attrs["reading_source"] = reading.get("source", "none")
        attrs.update(self.coordinator.get_calibration(self._device.device_id))
        return attrs


class YoLocalWaterTempSensor(YoLocalEntity, SensorEntity):
    """Water temperature sensor for the YoLink water meter controller.

    Reports ``temperature`` (celsius) from the device's top-level state.
    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_name = "Water temperature"

    def __init__(self, coordinator: YoLocalCoordinator, device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.device_id}_water_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the water temperature in celsius."""
        temp = self.device_state.get("temperature")
        if isinstance(temp, (int, float)):
            return float(temp)
        return None
