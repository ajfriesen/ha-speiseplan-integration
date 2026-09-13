"""Coordinator: polls the SpeisePlan plan endpoint."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SpeisePlanClient, SpeisePlanError
from .const import DOMAIN, LOGGER, PLAN_DAYS, SCAN_INTERVAL

type SpeisePlanConfigEntry = ConfigEntry[SpeisePlanCoordinator]


class SpeisePlanCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holds the latest plan snapshot."""

    config_entry: SpeisePlanConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SpeisePlanConfigEntry,
        client: SpeisePlanClient,
        info: dict[str, Any],
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self.info = info

    @property
    def instance_id(self) -> str:
        """Stable id of this SpeisePlan, used as the Home Assistant device id."""
        return self.info["instance_id"]

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_plan(PLAN_DAYS)
        except SpeisePlanError as err:
            raise UpdateFailed(str(err)) from err

    def day(self, offset: int) -> dict[str, Any]:
        """The plan entry for a day offset (0 = today).

        The API always returns one entry per day, empty ones included, so this
        only has to guard against a short payload from an older server.
        """
        days = (self.data or {}).get("days") or []
        if offset < len(days):
            return days[offset]
        return {"offset": offset, "date": None, "weekday": None, "meals": []}

    @property
    def unassigned(self) -> list[dict[str, Any]]:
        """Meals that are staged but not yet on a day."""
        return (self.data or {}).get("unassigned") or []

    @property
    def assigned(self) -> list[dict[str, Any]]:
        """Every meal in the window that has a day, flat and ordered."""
        return (self.data or {}).get("meals") or []
