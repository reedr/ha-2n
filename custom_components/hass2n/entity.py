"""2N Entity Base class."""

import logging

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import Hass2NCoordinator
from .device import Hass2NDevice

_LOGGER = logging.getLogger(__name__)

class Hass2NEntity(CoordinatorEntity[Hass2NCoordinator]):
    """Base class."""

    def __init__(self, coordinator: Hass2NCoordinator, entity: str, state: str) -> None:
        """Set up entity."""
        super().__init__(coordinator, entity)

        self._entity = entity
        self._state = state
        self._attr_name = f"{self.entity_type} {entity}"
        self._attr_unique_id = f"{self.entity_type}_{self.coordinator.device.device_id}_{self.device_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer=MANUFACTURER,
            model=coordinator.device.system_info["variant"],
            name=coordinator.device.device_id,
            sw_version=coordinator.device.system_info["swVersion"],
            connections={
                (dr.CONNECTION_NETWORK_MAC, coordinator.device.system_info["macAddr"])
            }
        )

#        _LOGGER.error(f"new entity={entity} state={state} name={self._attr_name} unique_id={self.unique_id}")

    @property
    def entity_type(self) -> str | None:
        """Type of entity."""
        return None

    @property
    def device_id(self):
        """Return entity id."""
        return self._entity

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {"device_id": self.device_id}

    @property
    def device_info(self) -> DeviceInfo:
        """Return information to link this entity with the correct device."""
        return self._attr_device_info

    @property
    def device(self) -> Hass2NDevice:
        """Return device."""
        return self.coordinator.device

    async def api_get(self, uri: str) -> bool:
        """Call the api."""
        return await self.device.api_get(uri)
