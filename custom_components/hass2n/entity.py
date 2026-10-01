"""Base entity for 2N intercoms."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import TwoNCoordinator
from .device import TwoNError


class TwoNEntity(CoordinatorEntity[TwoNCoordinator]):
    """An entity of one intercom.

    Unique IDs are ``<kind>_2N:<mac>_<key>``, unchanged from the pre-HACS package.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: TwoNCoordinator, kind: str, key: str | int) -> None:
        """Set up the entity."""
        super().__init__(coordinator)
        info = coordinator.info
        self._key = key
        self._attr_unique_id = f"{kind}_{info.device_id}_{key}"
        # Kept from the pre-HACS package, for templates that read it.
        self._attr_extra_state_attributes = {"device_id": key}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, info.device_id)},
            connections={(dr.CONNECTION_NETWORK_MAC, info.mac)},
            manufacturer=MANUFACTURER,
            model=info.model,
            name=info.name,
            serial_number=info.serial,
            sw_version=info.sw_version,
            configuration_url=f"https://{coordinator.device.host}",
        )

    async def _async_run(self, command: Awaitable[None]) -> None:
        """Run a device command, then refresh."""
        try:
            await command
        except TwoNError as err:
            raise HomeAssistantError(f"2N {self.coordinator.device.host}: {err}") from err
        await self.coordinator.async_request_refresh()
