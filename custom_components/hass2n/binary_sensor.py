"""Platform for sensor integration."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    ports = coord.data["ports"]
    new_entities = [Hass2NPortSensor(coord, port["port"], port["state"]) for port in ports]
    if new_entities:
        async_add_entities(new_entities)
    async_add_entities([Hass2NEventSensor(coord, "tracking", False)])

class Hass2NPortSensor(BinarySensorEntity,Hass2NEntity):
    """Port state sensor."""

    @property
    def is_on(self):
        """Return state."""
        return self._state == 1

    @property
    def entity_type(self) -> str:
        """Type of entity."""
        return "port"

    @property
    def available(self) -> bool:
        """"Return online state."""
        return self.coordinator.device.ports_online

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
#       _LOGGER.error(f"{self.coordinator.data} {self._entity}")
        if self.coordinator.data is not None:
            port = next(p for p in self.coordinator.data["ports"] if p["port"] == self._entity)
            self._state = port["state"]
            self.async_write_ha_state()

class Hass2NEventSensor(BinarySensorEntity,Hass2NEntity):
    """Port state sensor."""

    @property
    def is_on(self):
        """Return state."""
        self._state = self.coordinator.device.events_online
        return self._state

    @property
    def entity_type(self) -> str:
        """Type of entity."""
        return "event"

    @property
    def available(self) -> bool:
        """"Return online state."""
        return self.coordinator.device.online

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
