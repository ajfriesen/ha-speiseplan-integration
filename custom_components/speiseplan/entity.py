"""Base entity for SpeisePlan."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN, MANUFACTURER
from .coordinator import SpeisePlanCoordinator


class SpeisePlanEntity(CoordinatorEntity[SpeisePlanCoordinator]):
    """Common device wiring for every SpeisePlan entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SpeisePlanCoordinator, key: str) -> None:
        super().__init__(coordinator)
        info = coordinator.info
        self._attr_unique_id = f"{coordinator.instance_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.instance_id)},
            name=DEFAULT_NAME,
            manufacturer=MANUFACTURER,
            model="Meal planner",
            sw_version=info.get("version") or None,
            configuration_url=coordinator.client.base_url,
            entry_type=DeviceEntryType.SERVICE,
        )
