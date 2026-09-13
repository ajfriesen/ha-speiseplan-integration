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
