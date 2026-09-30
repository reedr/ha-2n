"""Support for ESPHome switches."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import Hass2NConfigEntry
from .entity import Hass2NEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant,
                            config_entry: Hass2NConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Add sensors for passed config_entry in HA."""
    coord = config_entry.runtime_data
    switches = coord.data["switches"]
    new_entities = [Hass2NSwitch(coord, switch["switch"], switch["active"]) for switch in switches]
    if new_entities:
        async_add_entities(new_entities)

class Hass2NSwitch(SwitchEntity, Hass2NEntity):
    """Port state sensor."""

    @property
    def is_on(self):
        """Return state."""
        return self._state

    @property
    def entity_type(self) -> str:
        """Type of entity."""
        return "switch"

    @property
    def available(self) -> bool:
        """"Return online state."""
        return self.coordinator.device.switches_online

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if await self.coordinator.device.async_turn_on(self._entity):
            self._state = True
            _LOGGER.debug("turned on")
            self.schedule_update_ha_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if await self.coordinator.device.async_turn_off(self._entity):
            self._state = False
            self.schedule_update_ha_state(True)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.device is not None:
            switch = next(sw for sw in self.coordinator.data["switches"] if sw["switch"] == self._entity)
            _LOGGER.debug("hcu: active=%s", switch["active"])
            self._state = switch["active"]
            self.async_write_ha_state()
