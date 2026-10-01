"""Coordinator for a 2N intercom."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import EVENT, UPDATE_INTERVAL
from .device import TwoNAuthError, TwoNDevice, TwoNError, TwoNInfo, TwoNState

_LOGGER = logging.getLogger(__name__)

type TwoNConfigEntry = ConfigEntry[TwoNCoordinator]


class TwoNCoordinator(DataUpdateCoordinator[TwoNState]):
    """Polls the intercom and fires its log events on the bus."""

    config_entry: TwoNConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: TwoNConfigEntry, device: TwoNDevice
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"2N {device.host}",
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.device = device

    @property
    def info(self) -> TwoNInfo:
        """The intercom's identity, known once setup has succeeded."""
        assert self.device.info is not None
        return self.device.info

    async def _async_setup(self) -> None:
        try:
            await self.device.async_get_info()
        except TwoNAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TwoNError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_update_data(self) -> TwoNState:
        try:
            state = await self.device.async_update()
        except TwoNAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TwoNError as err:
            raise UpdateFailed(str(err)) from err
        for event in state.events:
            payload = {**event, "device_id": self.info.device_id}
            _LOGGER.debug("Fire %s: %s", EVENT, payload)
            self.hass.bus.async_fire(EVENT, payload)
        return state
