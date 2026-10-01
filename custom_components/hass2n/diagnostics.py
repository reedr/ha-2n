"""Diagnostics for 2N intercoms."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import TwoNConfigEntry

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
    "serialNumber",
    "serial",
    "macAddr",
    "mac",
    "unique_id",
    "events",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TwoNConfigEntry
) -> dict[str, Any]:
    """Return the entry, the system info and the last poll."""
    coord = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "system_info": async_redact_data(coord.info.raw, TO_REDACT),
        "state": async_redact_data(asdict(coord.data), TO_REDACT) if coord.data else None,
    }
