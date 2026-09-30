"""2N Intercom coordinator."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import EVENT
from .device import Hass2NDevice

_LOGGER = logging.getLogger(__name__)

type Hass2NConfigEntry = ConfigEntry['Hass2NCoordinator']

class Hass2NCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: Hass2NConfigEntry, device: Hass2NDevice) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="2N Coordinator",
            config_entry=config_entry,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=5),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=False
        )
        self._device = device

    @property
    def device(self) -> Hass2NDevice:
        """The device handle."""
        return self._device

    async def _async_setup(self):
        """Set up the coordinator.

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        await self.device.get_system_info()

    async def _async_update_data(self):
        """Fetch data from API endpoint."""

        status = await self.device.get_status()
        if status is None:
            raise UpdateFailed

        events = status.get("events")
        if events is not None:
            for event in events:
                event["device_id"] = self.device.device_id
                _LOGGER.debug("Fire event: %s", event)
                self.hass.bus.async_fire(EVENT, event)
        return status
