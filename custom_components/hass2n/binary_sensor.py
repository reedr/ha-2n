"""2N I/O ports, and whether the event log is being followed."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TwoNConfigEntry, TwoNCoordinator
from .entity import TwoNEntity

PARALLEL_UPDATES = 0

_PORT_CLASSES = {"tamper": BinarySensorDeviceClass.TAMPER}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TwoNConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a sensor per I/O port, plus event-log tracking."""
    coord = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        TwoNPortSensor(coord, port) for port in sorted(coord.data.ports or {})
    ]
    entities.append(TwoNEventTrackingSensor(coord))
    async_add_entities(entities)


class TwoNPortSensor(TwoNEntity, BinarySensorEntity):
    """An input, output, relay, LED or tamper port."""

    def __init__(self, coordinator: TwoNCoordinator, port: str) -> None:
        """Set up the sensor."""
        super().__init__(coordinator, "port", port)
        self._attr_name = f"Port {port}"
        self._attr_device_class = _PORT_CLASSES.get(port)

    @property
    def available(self) -> bool:
        """Unavailable while the I/O API isn't answering or the port has gone."""
        ports = self.coordinator.data.ports
        return super().available and ports is not None and self._key in ports

    @property
    def is_on(self) -> bool | None:
        """Whether the port is active."""
        state = (self.coordinator.data.ports or {}).get(self._key)
        return None if state is None else state == 1


class TwoNEventTrackingSensor(TwoNEntity, BinarySensorEntity):
    """On while the intercom's event log is being followed (events reach HA)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "event_tracking"

    def __init__(self, coordinator: TwoNCoordinator) -> None:
        """Set up the sensor."""
        super().__init__(coordinator, "event", "tracking")

    @property
    def is_on(self) -> bool:
        """Whether events are being received."""
        return self.coordinator.data.events_online
