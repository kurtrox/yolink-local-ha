"""Constants for the YoLink Local integration."""

DOMAIN = "yolocal"

# Configuration keys
CONF_HUB_IP = "hub_ip"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_NET_ID = "net_id"

# Default ports
DEFAULT_HTTP_PORT = 1080
DEFAULT_MQTT_PORT = 18080

# API endpoints
TOKEN_ENDPOINT = "/open/yolink/token"
API_ENDPOINT = "/open/yolink/v2/api"

# Platforms we support
PLATFORMS: list[str] = [
    "sensor",
    "binary_sensor",
    "lock",
    "switch",
    "siren",
    "valve",
]

# --- Water meter calibration ---------------------------------------------
# The local API reports ``state.meter`` as a raw pulse count. The actual
# volume it represents comes from the device's own meter attributes:
#   * ``attributes.meterUnit``      (0=GAL, 1=CCF, 2=M3, 3=L)
#   * ``attributes.meterStepFactor`` (meter measurement accuracy)
# The YoLink cloud app derives the reading as  raw * meterStepFactor / 1000
# in the meter's unit. When those attributes are present the integration uses
# them directly (no manual calibration needed); otherwise it falls back to a
# user-set baseline (raw reading + real-world volume + scale factor).
DEFAULT_GALLONS_PER_PULSE = 0.001

# Meter screen unit codes -> Home Assistant unit string.
METER_UNIT_TO_UNIT = {0: "gal", 1: "CCF", 2: "m³", 3: "L"}
METER_UNIT_LABEL = {0: "GAL", 1: "CCF", 2: "M3", 3: "L"}

# Service to set the calibration baseline (used when meterStepFactor is
# unavailable). ``unit`` optionally overrides the meter's own unit so the
# baseline is interpreted in the user's preferred unit.
SERVICE_SET_METER_CALIBRATION = "set_water_meter_calibration"
CONF_DEVICE_ID = "device_id"
CONF_GALLONS = "gallons"
CONF_SCALE = "scale"
CONF_UNIT = "unit"

