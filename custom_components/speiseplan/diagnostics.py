"""Diagnostics support for SpeisePlan."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant

from .coordinator import SpeisePlanConfigEntry

TO_REDACT = {CONF_TOKEN, CONF_HOST, "instance_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SpeisePlanConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "info": async_redact_data(coordinator.info, TO_REDACT),
        "plan": coordinator.data,
    }
