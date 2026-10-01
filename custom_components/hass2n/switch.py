"""2N switches (relay/lock outputs), held on until turned off."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Add a switch per 2N switch."""
    coord = entry.runtime_data
    async_add_entities(TwoNSwitch(coord, n) for n in sorted(coord.data.switches or {}))


class TwoNSwitch(TwoNEntity, SwitchEntity):
    """A 2N switch."""

    def __init__(self, coordinator: TwoNCoordinator, switch: int) -> None:
        """Set up the switch."""
        super().__init__(coordinator, "switch", switch)
        self._attr_name = f"Switch {switch}"

    @property
    def available(self) -> bool:
        """Unavailable while the switch API isn't answering."""
        return super().available and self.coordinator.data.switches is not None

    @property
    def is_on(self) -> bool | None:
        """Whether the switch is active."""
        switches = self.coordinator.data.switches or {}
        return switches.get(self._key)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the switch."""
        await self._async_run(self.coordinator.device.async_turn_on(self._key))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the switch."""
        await self._async_run(self.coordinator.device.async_turn_off(self._key))
