"""Support for ports as buttons."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import Hass2NConfigEntry
from .entity import Hass2NEntity


async def async_setup_entry(hass: HomeAssistant,
                            config_entry: Hass2NConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Add sensors for passed config_entry in HA."""
    coord = config_entry.runtime_data
    switches = coord.data["switches"]
    new_entities = [Hass2NButton(coord, switch["switch"], switch["active"]) for switch in switches]
    if new_entities:
        async_add_entities(new_entities)

class Hass2NButton(ButtonEntity, Hass2NEntity):
    """Port state sensor."""

    @property
    def is_on(self):
        """Return state."""
        return self._state

    @property
    def entity_type(self) -> str:
        """Type of entity."""
        return "button"

    async def async_press(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.coordinator.device.async_press(self._entity)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is not None:
            switch = next(sw for sw in self.coordinator.data["switches"] if sw["switch"] == self._entity)
            self._state = switch["active"]
            self.async_write_ha_state()
