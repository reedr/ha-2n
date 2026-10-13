"""Coordinator for a 2N intercom."""

from __future__ import annotations

import dataclasses
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import EVENT, UNAVAILABLE_AFTER, UPDATE_INTERVAL
from .device import (
    TwoNAuthError,
    TwoNDevice,
    TwoNError,
    TwoNInfo,
    TwoNNetworkError,
    TwoNState,
)

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
        # Polls in a row that failed on the network while the last good state
        # was kept.
        self.network_failures = 0

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

    def _ride_out(self, err: TwoNNetworkError) -> bool:
        """Count a network failure; True while the last good state may be kept."""
        if self.data is None or self.network_failures >= UNAVAILABLE_AFTER - 1:
            return False
        self.network_failures += 1
        _LOGGER.debug(
            "%s: network failure %d of %d tolerated: %s",
            self.name,
            self.network_failures,
            UNAVAILABLE_AFTER,
            err,
        )
        return True

    async def _async_update_data(self) -> TwoNState:
        try:
            state = await self.device.async_update()
        except TwoNAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TwoNNetworkError as err:
            if self._ride_out(err):
                return dataclasses.replace(self.data, events=[])
            raise UpdateFailed(str(err)) from err
        except TwoNError as err:
            raise UpdateFailed(str(err)) from err
        if state.network_error and self._ride_out(TwoNNetworkError("partial poll")):
            # Some sections dropped out on the network: keep their last values.
            prev = self.data
            state = dataclasses.replace(
                state,
                ports=prev.ports if state.ports is None else state.ports,
                switches=prev.switches if state.switches is None else state.switches,
                events_online=state.events_online or prev.events_online,
            )
        elif not state.network_error:
            self.network_failures = 0
        for event in state.events:
            payload = {**event, "device_id": self.info.device_id}
            _LOGGER.debug("Fire %s: %s", EVENT, payload)
            self.hass.bus.async_fire(EVENT, payload)
        return state
