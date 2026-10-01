"""Pulse a 2N switch for its configured time, as the keypad or an app would."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TwoNConfigEntry, TwoNCoordinator
from .entity import TwoNEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TwoNConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a trigger button per 2N switch."""
    coord = entry.runtime_data
    async_add_entities(TwoNTriggerButton(coord, n) for n in sorted(coord.data.switches or {}))


class TwoNTriggerButton(TwoNEntity, ButtonEntity):
    """Trigger (pulse) a switch."""

    _attr_icon = "mdi:gesture-tap-button"

    def __init__(self, coordinator: TwoNCoordinator, switch: int) -> None:
        """Set up the button."""
        super().__init__(coordinator, "button", switch)
        self._attr_name = f"Switch {switch} trigger"

    async def async_press(self) -> None:
        """Pulse the switch."""
        await self._async_run(self.coordinator.device.async_trigger(self._key))
