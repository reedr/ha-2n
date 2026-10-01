"""The 2N Intercom integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .coordinator import TwoNConfigEntry, TwoNCoordinator
from .device import TwoNDevice
from .migration import async_migrate_device, async_migrate_legacy_entry

_PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: TwoNConfigEntry) -> bool:
    """Set up a 2N intercom from a config entry."""
    await async_migrate_legacy_entry(hass, entry)

    dev = await hass.async_add_executor_job(
        TwoNDevice, entry.data[CONF_HOST], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    coord = TwoNCoordinator(hass, entry, dev)
    entry.runtime_data = coord
    entry.async_on_unload(dev.async_close)
    await coord.async_config_entry_first_refresh()

    async_migrate_device(hass, entry, coord.info)

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TwoNConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
