"""Constantes de l'intégration SimplyFeu."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "simplyfeu"
LOGGER = logging.getLogger(__package__)

CONF_URL: Final = "url"
CONF_PRICE_REGEX: Final = "price_regex"
CONF_COOKIE: Final = "cookie"
CONF_SCAN_INTERVAL: Final = "scan_interval_hours"

DEFAULT_SCAN_INTERVAL: Final = 6
MIN_SCAN_INTERVAL: Final = 1
MAX_SCAN_INTERVAL: Final = 48

EVENT_PRICE_CHANGED: Final = f"{DOMAIN}_price_changed"

STORAGE_VERSION: Final = 1
