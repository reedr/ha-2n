"""Import of the legacy "2N" package's entries."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import (
    area_registry as ar,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hass2n.const import CONF_LEGACY_ENTRY, DOMAIN, LEGACY_DOMAIN

from .conftest import DOOR, DOOR_MAC, GATE, GATE_MAC


def _legacy(hass: HomeAssistant, title: str, data: dict, mac: str, entities: dict) -> tuple:
    """Registry contents left by the old package, including its per-entity device IDs."""
    entry = MockConfigEntry(domain=LEGACY_DOMAIN, title=title, data=data)
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    device = None
    for unique_id in entities:
        device = dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(LEGACY_DOMAIN, unique_id)},
            connections={(dr.CONNECTION_NETWORK_MAC, mac)},
            manufacturer="2N",
            name=f"2N:{mac}",
        )
    ent_reg = er.async_get(hass)
    for unique_id, entity_id in entities.items():
        domain, object_id = entity_id.split(".")
        ent_reg.async_get_or_create(
            domain,
            LEGACY_DOMAIN,
            unique_id,
            config_entry=entry,
            device_id=device.id,
            suggested_object_id=object_id,
        )
    return entry, device


def _setup_legacy(hass: HomeAssistant):
    gate = _legacy(
        hass,
        "2N IP Verso",
        GATE,
        GATE_MAC,
        {
            f"switch_2N:{GATE_MAC}_1": "switch.gate_open_switch",
            f"switch_2N:{GATE_MAC}_2": "switch.gate_hold_open",
            f"port_2N:{GATE_MAC}_relay1": "binary_sensor.gate_open_relay",
            f"event_2N:{GATE_MAC}_tracking": "binary_sensor.event_tracking_2",
        },
    )
    door = _legacy(
        hass,
        "2N IP Solo",
        DOOR,
        DOOR_MAC,
        {
            f"switch_2N:{DOOR_MAC}_1": "switch.switch_1_2",
            f"port_2N:{DOOR_MAC}_tamper": "binary_sensor.port_tamper",
        },
    )
    area = ar.async_get(hass).async_create("Exterior")
    dr.async_get(hass).async_update_device(
        gate[1].id, name_by_user="Gate Intercom", area_id=area.id
    )
    er.async_get(hass).async_update_entity("switch.gate_open_switch", name="Gate Open Switch")
    return gate, door


async def test_import_all(hass: HomeAssistant, network) -> None:
    (_gate_legacy, gate_dev), (door_legacy, door_dev) = _setup_legacy(hass)
    dev_reg = dr.async_get(hass)
    # An empty extra device of the door's entry, and ONVIF's device for the same
    # unit carrying a leftover 2N identifier.
    empty = dev_reg.async_get_or_create(
        config_entry_id=door_legacy.entry_id, identifiers={(LEGACY_DOMAIN, "old")}
    )
    onvif = MockConfigEntry(domain="onvif", title="Front Door")
    onvif.add_to_hass(hass)
    onvif_dev = dev_reg.async_get_or_create(
        config_entry_id=onvif.entry_id,
        identifiers={("onvif", "door"), (LEGACY_DOMAIN, f"switch_2N:{DOOR_MAC}_9")},
        name="Front Door",
    )

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "import_legacy"}
    )
    assert result["description_placeholders"]["count"] == "2"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert hass.config_entries.async_entries(LEGACY_DOMAIN) == []
    entries = {e.title: e for e in hass.config_entries.async_entries(DOMAIN)}
    assert set(entries) == {"2N IP Verso", "2N IP Solo"}
    assert entries["2N IP Verso"].unique_id == f"2N:{GATE_MAC}"
    assert all(CONF_LEGACY_ENTRY not in e.data for e in entries.values())

    ent_reg = er.async_get(hass)
    for entity_id in (
        "switch.gate_open_switch",
        "binary_sensor.gate_open_relay",
        "binary_sensor.event_tracking_2",
        "switch.switch_1_2",
    ):
        reg = ent_reg.async_get(entity_id)
        assert reg.platform == DOMAIN, entity_id
        assert hass.states.get(entity_id) is not None, entity_id
    assert ent_reg.async_get("switch.gate_open_switch").name == "Gate Open Switch"
    assert hass.states.get("switch.gate_open_switch").state == "off"
    assert ent_reg.async_get("switch.gate_open_switch").device_id == gate_dev.id

    gate = dev_reg.async_get(gate_dev.id)
    assert gate.identifiers == {(DOMAIN, f"2N:{GATE_MAC}")}
    assert gate.name_by_user == "Gate Intercom"
    assert gate.model == "2N IP Verso"
    assert len(dr.async_entries_for_config_entry(dev_reg, entries["2N IP Verso"].entry_id)) == 1

    assert dev_reg.async_get(empty.id) is None
    assert dev_reg.async_get(door_dev.id).identifiers == {(DOMAIN, f"2N:{DOOR_MAC}")}
    # ONVIF's device is left alone.
    assert dev_reg.async_get(onvif_dev.id).config_entries == {onvif.entry_id}
