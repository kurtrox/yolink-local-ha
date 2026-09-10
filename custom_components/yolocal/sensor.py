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

from .const import DEFAULT_GALLONS_PER_PULSE, DOMAIN
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
    """Calibrated cumulative water consumption for the YoLink water meter.

    The local hub reports ``state.meter`` as a raw pulse count — the actual
    volume is not derivable from the payload alone. The user calibrates the
    meter by calling ``yolocal.set_water_meter_calibration`` with the real
    volume shown on the meter face; the integration then reports::

        gallons = baseline_gallons + (raw_now - baseline_raw) * scale

    where ``scale`` is gallons per raw pulse unit (default 0.001). Until a
    baseline is set the sensor reports *unknown* (the raw pulse count is
    never mislabeled as gallons); it is always available as the ``raw_meter``
    state attribute for reference and for running a flow test.
    """

    _attr_name = "Water usage"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.GALLONS

    def __init__(self, coordinator: YoLocalCoordinator, device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.device_id}_water_meter"

    @property
    def _raw(self) -> float | None:
        meter = _state_value(self.device_state, "meter")
        if meter is None:
            return None
        try:
            return float(meter)
        except (TypeError, ValueError):
            return None

    @property
    def native_value(self) -> float | None:
        """Return the calibrated water usage in gallons.

        Returns None (unknown) until the meter has been calibrated via the
        ``yolocal.set_water_meter_calibration`` service, so the raw pulse
        count is never presented as a gallon reading.
        """
        raw = self._raw
        if raw is None:
            return None
        cal = self.coordinator.get_calibration(self._device.device_id)
        if not cal or cal.get("raw") is None:
            return None
        try:
            baseline_gallons = float(cal["gallons"])
            baseline_raw = float(cal["raw"])
            scale = float(cal.get("scale", DEFAULT_GALLONS_PER_PULSE))
        except (KeyError, TypeError, ValueError):
            return None
        return round(baseline_gallons + (raw - baseline_raw) * scale, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw count and calibration metadata."""
        attrs: dict[str, Any] = {}
        raw = self._raw
        if raw is not None:
            attrs["raw_meter"] = raw
        cal = self.coordinator.get_calibration(self._device.device_id)
        if cal:
            attrs["calibrated_gallons"] = cal.get("gallons")
            attrs["baseline_raw"] = cal.get("raw")
            attrs["scale_gallons_per_pulse"] = cal.get(
                "scale", DEFAULT_GALLONS_PER_PULSE
            )
        return attrs

