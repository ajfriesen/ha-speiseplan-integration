"""The SpeisePlan integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change

from .api import SpeisePlanClient, SpeisePlanError
from .const import LOGGER
from .coordinator import SpeisePlanConfigEntry, SpeisePlanCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SpeisePlanConfigEntry) -> bool:
    """Set up SpeisePlan from a config entry."""
    session = async_get_clientsession(hass)
    client = SpeisePlanClient(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_SSL, False),
    )

    try:
        info = await client.async_get_info()
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

    _async_remove_image_entities(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Roll the window over shortly after midnight. The five-minute poll would
    # get there anyway; this just stops "today" lagging at the turn of the day.
    async def _midnight(now: datetime) -> None:
        await coordinator.async_request_refresh()

    entry.async_on_unload(
        async_track_time_change(hass, _midnight, hour=0, minute=0, second=10)
    )

    return True


@callback
def _async_remove_image_entities(
    hass: HomeAssistant, entry: SpeisePlanConfigEntry
) -> None:
    """Drop the image entities earlier versions created.

    Photos are now handed out as a URL on the sensors, so nothing recreates
    these. Home Assistant keeps registry entries whose platform no longer sets
    them up, and they would sit there permanently unavailable.
    """
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.domain == Platform.IMAGE:
            LOGGER.debug("Removing obsolete image entity %s", reg_entry.entity_id)
            registry.async_remove(reg_entry.entity_id)


async def async_unload_entry(hass: HomeAssistant, entry: SpeisePlanConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
