"""The SpeisePlan integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change

from .api import SpeisePlanAuthError, SpeisePlanClient, SpeisePlanError
from .const import LOGGER
from .coordinator import SpeisePlanConfigEntry, SpeisePlanCoordinator

PLATFORMS: list[Platform] = [
    Platform.IMAGE,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: SpeisePlanConfigEntry) -> bool:
    """Set up SpeisePlan from a config entry."""
    session = async_get_clientsession(hass)
    client = SpeisePlanClient(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_TOKEN],
        entry.data.get(CONF_SSL, False),
    )

    try:
        info = await client.async_get_info()
    except SpeisePlanAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except SpeisePlanError as err:
        raise ConfigEntryNotReady(str(err)) from err

    # "Today" is whatever SpeisePlan says it is. If the two disagree the day
    # entities will look off by one around midnight, which is worth a hint.
    server_tz = info.get("timezone")
    if server_tz and server_tz != str(hass.config.time_zone):
        LOGGER.warning(
            "SpeisePlan runs in %s but Home Assistant is in %s; "
            "the day entities follow SpeisePlan's calendar",
            server_tz,
            hass.config.time_zone,
        )

    coordinator = SpeisePlanCoordinator(hass, entry, client, info)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Roll the window over shortly after midnight. The five-minute poll would
    # get there anyway; this just stops "today" lagging at the turn of the day.
    async def _midnight(now: datetime) -> None:
        await coordinator.async_request_refresh()

    entry.async_on_unload(
        async_track_time_change(hass, _midnight, hour=0, minute=0, second=10)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SpeisePlanConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
