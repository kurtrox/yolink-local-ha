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
# volume it represents depends on the meter's mechanical resolution, which
# the user must calibrate against the physical meter face. The integration
# stores a baseline (raw reading + real-world gallons) and a scale factor
# (gallons per raw unit) and computes a calibrated total from them.
DEFAULT_GALLONS_PER_PULSE = 0.001

# Service to set the calibration baseline.
SERVICE_SET_METER_CALIBRATION = "set_water_meter_calibration"
CONF_DEVICE_ID = "device_id"
CONF_GALLONS = "gallons"
CONF_SCALE = "scale"

