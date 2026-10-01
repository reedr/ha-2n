"""Registry migrations from the legacy "2N" package."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_LEGACY_ENTRY, DOMAIN, LEGACY_DOMAIN
from .coordinator import TwoNConfigEntry
from .device import TwoNInfo

_LOGGER = logging.getLogger(__name__)


async def async_migrate_legacy_entry(hass: HomeAssistant, entry: TwoNConfigEntry) -> None:
    """Move the legacy entry's devices and entities onto this entry, then remove it.

    Registry IDs are kept, so entity IDs, history, names, areas and labels carry
    over. Unique IDs need no change: they were already MAC-based.
    """
    legacy_id = entry.data.get(CONF_LEGACY_ENTRY)
    if legacy_id is None:
        return

    legacy = hass.config_entries.async_get_entry(legacy_id)
    if legacy is not None and legacy.domain == LEGACY_DOMAIN:
        # Loaded entities can't change platform; the legacy package is normally
        # gone by now (this one replaces its folder), but unload it if not.
        if legacy.state is ConfigEntryState.LOADED:
            await hass.config_entries.async_unload(legacy_id)

        ent_reg = er.async_get(hass)
        dev_reg = dr.async_get(hass)
        for entity in er.async_entries_for_config_entry(ent_reg, legacy_id):
            ent_reg.async_update_entity_platform(
                entity.entity_id, DOMAIN, new_config_entry_id=entry.entry_id
            )
            _LOGGER.info("Took over %s from the legacy 2N integration", entity.entity_id)
        for device in dr.async_entries_for_config_entry(dev_reg, legacy_id):
            dev_reg.async_update_device(
                device.id,
                new_config_entry_id=entry.entry_id,
                new_identifiers={
                    (DOMAIN, ident) if domain == LEGACY_DOMAIN else (domain, ident)
                    for domain, ident in device.identifiers
                },
            )
        await hass.config_entries.async_remove(legacy_id)

    data = {k: v for k, v in entry.data.items() if k != CONF_LEGACY_ENTRY}
    hass.config_entries.async_update_entry(entry, data=data)


@callback
def async_migrate_device(hass: HomeAssistant, entry: TwoNConfigEntry, info: TwoNInfo) -> None:
    """Give the intercom a single device identifier, and drop empty extra devices.

    The legacy package used every entity's unique ID as a device identifier. Keep
    the device holding this entry's entities; another device of this entry with
    none of them is an orphan.
    """
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    target = (DOMAIN, info.device_id)
    if devices:
        counts = {d.id: 0 for d in devices}
        for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            if entity.device_id in counts:
                counts[entity.device_id] += 1
        primary = max(devices, key=lambda d: counts[d.id])
        wanted = {i for i in primary.identifiers if i[0] != DOMAIN} | {target}
        if primary.identifiers != wanted:
            dev_reg.async_update_device(primary.id, new_identifiers=wanted)
        for device in devices:
            if device.id != primary.id and counts[device.id] == 0:
                _LOGGER.info("Removing empty device %s of %s", device.id, entry.title)
                dev_reg.async_remove_device(device.id)

    if entry.unique_id is None and not any(
        other.unique_id == info.device_id for other in hass.config_entries.async_entries(DOMAIN)
    ):
        hass.config_entries.async_update_entry(entry, unique_id=info.device_id)
