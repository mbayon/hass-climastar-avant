"""Constants for Climastar Avant WiFi."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "climastar_avant"
NAME: Final = "Climastar Avant WiFi"
API_BASE: Final = "https://users-api.helki.com"
WS_URL: Final = "wss://users-api.helki.com/api/v2/ws_user"
CLIENT_ID: Final = "54bccbfb41a9a5113f0488d0"
CLIENT_SECRET: Final = "vdivdi"
SERIAL_ID: Final = "5"
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"
PLATFORMS: Final = ["binary_sensor", "climate", "sensor"]
HTTP_TIMEOUT: Final = 20
TOKEN_REFRESH_MARGIN: Final = timedelta(minutes=5)
RECONNECT_MAX_DELAY: Final = 300
