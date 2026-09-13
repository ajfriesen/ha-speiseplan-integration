"""Meal plan sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import PLAN_DAYS
from .coordinator import SpeisePlanConfigEntry, SpeisePlanCoordinator
from .entity import SpeisePlanEntity

# Home Assistant truncates longer states anyway; do it here so the value stays
# predictable rather than being cut off somewhere downstream.
MAX_STATE_LENGTH = 255

# key -> display name, one per offset into the window. The names are relative
# rather than weekday names so an entity keeps meaning the same thing as the
# days roll over, and they match the keys so the entity ids stay predictable.
DAY_KEYS: tuple[tuple[str, str], ...] = (
    ("today", "Today"),
    ("day_1", "Day 1"),
    ("day_2", "Day 2"),
    ("day_3", "Day 3"),
    ("day_4", "Day 4"),
    ("day_5", "Day 5"),
    ("day_6", "Day 6"),
)


def meal_summary(meal: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Flatten one meal into the shape templates read.

    photo_url is absolute so it can be templated straight into a renderer that
    fetches it — an OpenDisplay drawcustom `dlimg` element, say. SpeisePlan
    reports the path relative to its own root; joining it here is the only
    place that knows the address. The endpoint serves locally stored and
    externally hosted photos alike, so a consumer never has to tell them apart.
    """
    path = meal.get("photo_url")
    if path and not path.startswith(("http://", "https://")):
        path = f"{base_url}{path}"
    return {
        "name": meal.get("name"),
        "url": meal.get("url") or None,
        "photo_url": path or None,
        # False means photo_url still returns an image — a QR code linking to
        # the recipe, so somebody can scan it and add the missing photo.
        "has_photo": bool(meal.get("has_photo")),
        "minutes": meal.get("minutes"),
        "tag": meal.get("tag") or None,
        "recipe_id": meal.get("recipe_id"),
        "day": meal.get("day") or None,
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpeisePlanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the plan sensors."""
    coordinator = entry.runtime_data
    entities: list[SpeisePlanEntity] = [
        SpeisePlanDaySensor(coordinator, offset, key, name)
        for offset, (key, name) in enumerate(DAY_KEYS[:PLAN_DAYS])
    ]
    entities.append(SpeisePlanSummarySensor(coordinator))
    entities.append(SpeisePlanUnassignedSensor(coordinator))
    async_add_entities(entities)


class SpeisePlanDaySensor(SpeisePlanEntity, SensorEntity):
    """What is planned for one day of the window.

    The state is the first meal's name, or unknown when nothing is planned —
    never unavailable, which would mean SpeisePlan itself is unreachable and
    would blank the attributes templates rely on.
    """

    # None of this belongs in the recorder, and the meal lists would otherwise
    # push the row past its 16 KiB attribute ceiling and be dropped silently.
    _unrecorded_attributes = frozenset({MATCH_ALL})

    _attr_icon = "mdi:silverware-fork-knife"

    def __init__(
        self,
        coordinator: SpeisePlanCoordinator,
        offset: int,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, key)
        self._offset = offset
        self._attr_name = name

    @property
    def _day(self) -> dict[str, Any]:
        return self.coordinator.day(self._offset)

    @property
    def _meals(self) -> list[dict[str, Any]]:
        return self._day.get("meals") or []

    @property
    def native_value(self) -> StateType:
        meals = self._meals
        if not meals:
            return None
        return str(meals[0].get("name") or "")[:MAX_STATE_LENGTH] or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        day = self._day
        meals = self._meals
        base_url = self.coordinator.client.base_url
        first = meal_summary(meals[0], base_url) if meals else {}
        # Every key is always present, so templates never need a guard.
        return {
            "date": day.get("date"),
            "weekday": day.get("weekday"),
            "offset": self._offset,
            "meal_count": len(meals),
            "has_meal": bool(meals),
            "meals": [meal_summary(m, base_url) for m in meals],
            "name": first.get("name"),
            "url": first.get("url"),
            "photo_url": first.get("photo_url"),
            "has_photo": first.get("has_photo", False),
            "minutes": first.get("minutes"),
            "tag": first.get("tag"),
            "recipe_id": first.get("recipe_id"),
        }


class SpeisePlanSummarySensor(SpeisePlanEntity, SensorEntity):
    """Everything planned in the window, for templates that want one entity."""

    _unrecorded_attributes = frozenset({MATCH_ALL})

    _attr_name = "Meal plan"
    _attr_icon = "mdi:calendar-text"
    _attr_native_unit_of_measurement = "meals"

    def __init__(self, coordinator: SpeisePlanCoordinator) -> None:
        super().__init__(coordinator, "meal_plan")

    @property
    def native_value(self) -> StateType:
        return len(self.coordinator.assigned)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        base_url = self.coordinator.client.base_url
        meals = [meal_summary(m, base_url) for m in self.coordinator.assigned]
        return {
            "today": data.get("today"),
            "timezone": data.get("timezone"),
            "generated_at": data.get("generated_at"),
            "meals": meals,
            "next_meal": meals[0] if meals else None,
            "days": [
                {
                    "offset": day.get("offset"),
                    "date": day.get("date"),
                    "weekday": day.get("weekday"),
                    "meals": [
                        meal_summary(m, base_url) for m in day.get("meals") or []
                    ],
                }
                for day in data.get("days") or []
            ],
        }


class SpeisePlanUnassignedSensor(SpeisePlanEntity, SensorEntity):
    """Meals staged in SpeisePlan that have not been given a day yet."""

    _unrecorded_attributes = frozenset({MATCH_ALL})

    _attr_name = "Unassigned"
    _attr_icon = "mdi:tray-full"
    _attr_native_unit_of_measurement = "meals"

    def __init__(self, coordinator: SpeisePlanCoordinator) -> None:
        super().__init__(coordinator, "unassigned")

    @property
    def native_value(self) -> StateType:
        return len(self.coordinator.unassigned)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base_url = self.coordinator.client.base_url
        return {
            "meals": [meal_summary(m, base_url) for m in self.coordinator.unassigned]
        }
