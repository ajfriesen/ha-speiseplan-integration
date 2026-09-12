"""Meal photo image entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import SpeisePlanError
from .const import (
    LOGGER,
    PLACEHOLDER_CONTENT_TYPE,
    PLACEHOLDER_PNG,
    PLAN_DAYS,
)
from .coordinator import SpeisePlanConfigEntry, SpeisePlanCoordinator
from .entity import SpeisePlanEntity
from .sensor import DAY_KEYS

# Only today and tomorrow are on by default. The image component rewrites every
# image entity's state every five minutes to rotate its access token, so each
# enabled entity costs ~288 state changes a day whether or not the photo moved.
DEFAULT_ENABLED_OFFSETS = {0, 1}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpeisePlanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the meal photo images."""
    coordinator = entry.runtime_data
    async_add_entities(
        SpeisePlanDayImage(hass, coordinator, offset, key, name)
        for offset, (key, name) in enumerate(DAY_KEYS[:PLAN_DAYS])
    )


class SpeisePlanDayImage(SpeisePlanEntity, ImageEntity):
    """The photo of the first meal planned for one day."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: SpeisePlanCoordinator,
        offset: int,
        key: str,
        name: str,
    ) -> None:
        # ImageEntity.__init__ needs hass and never runs through the cooperative
        # chain, because CoordinatorEntity's base doesn't call super().__init__.
        super().__init__(coordinator, key)
        ImageEntity.__init__(self, hass)
        self._offset = offset
        self._attr_name = name
        self._attr_entity_registry_enabled_default = offset in DEFAULT_ENABLED_OFFSETS
        self._image_key: tuple[Any, ...] | None = None
        self._attr_image_last_updated = None

    def _first_meal(self) -> dict[str, Any] | None:
        meals = self.coordinator.day(self._offset).get("meals") or []
        for meal in meals:
            if meal.get("photo_url"):
                return meal
        return meals[0] if meals else None

    def _sync_image(self) -> None:
        """Refresh the cache key and timestamp when the day's meal changes.

        image_last_updated *is* this entity's state, so a value that does not
        move produces no state change and every consumer keeps showing the old
        photo. Two recipes imported in the same second share an updated_at, so
        the recipe identity has to drive this, not the server timestamp alone.
        """
        meal = self._first_meal()
        key = (meal.get("recipe_id"), meal.get("image")) if meal else None
        if key == self._image_key:
            return

        self._image_key = key
        self._cached_image = None

        stamp: datetime | None = None
        if meal and meal.get("updated_at"):
            stamp = dt_util.parse_datetime(meal["updated_at"])
        if stamp is None or stamp == self._attr_image_last_updated:
            # Fall back to "now" so a different meal never reuses a timestamp.
            stamp = dt_util.utcnow()
        self._attr_image_last_updated = stamp

    async def async_added_to_hass(self) -> None:
        """Seed the image identity before the first state is written."""
        self._sync_image()
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sync_image()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        meal = self._first_meal()
        recipe_id = meal.get("recipe_id") if meal else None
        if not meal or not meal.get("photo_url") or recipe_id is None:
            # entity_picture can't be None, so the frontend asks regardless;
            # a placeholder keeps that from becoming a repeating 500.
            self._attr_content_type = PLACEHOLDER_CONTENT_TYPE
            return PLACEHOLDER_PNG
        try:
            image, content_type = await self.coordinator.client.async_get_photo(
                int(recipe_id)
            )
        except SpeisePlanError as err:
            LOGGER.debug("No photo for recipe %s: %s", recipe_id, err)
            self._attr_content_type = PLACEHOLDER_CONTENT_TYPE
            return PLACEHOLDER_PNG
        self._attr_content_type = content_type
        return image
