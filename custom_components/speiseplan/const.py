"""Constants for the SpeisePlan integration."""

from __future__ import annotations

import logging
from datetime import timedelta

DOMAIN = "speiseplan"
LOGGER = logging.getLogger(__package__)

DEFAULT_PORT = 8080
DEFAULT_NAME = "SpeisePlan"
MANUFACTURER = "SpeisePlan"

# How many days of the plan to pull. SpeisePlan's own window is 7 days
# (today .. today+6) and the day entities are laid out to match.
PLAN_DAYS = 7

# The plan only changes when somebody edits it, so polling is cheap and five
# minutes is plenty. Day rollover is handled separately (see __init__.py).
SCAN_INTERVAL = timedelta(minutes=5)

# Served for days with no meal. ImageEntity.entity_picture can't be None, so the
# frontend always requests the proxy URL; returning None from async_image() turns
# that into a repeating HTTP 500. A 1x1 transparent PNG is the quiet answer.
PLACEHOLDER_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c63000100000500010d0a2db40000"
    "000049454e44ae426082"
)
PLACEHOLDER_CONTENT_TYPE = "image/png"
