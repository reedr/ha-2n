"""Setup, entities, controls and events."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.hass2n.const import DOMAIN, EVENT

from .conftest import GATE, GATE_MAC


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Gate", unique_id=f"2N:{GATE_MAC}", data=GATE)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _tick(hass: HomeAssistant) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()


async def test_entities(hass: HomeAssistant, network) -> None:
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    ent_reg = er.async_get(hass)
    uid = lambda kind, key: ent_reg.async_get_entity_id(  # noqa: E731
        {"switch": "switch", "button": "button"}.get(kind, "binary_sensor"),
        DOMAIN,
        f"{kind}_2N:{GATE_MAC}_{key}",
    )
    assert hass.states.get(uid("switch", 1)).state == STATE_OFF
    assert hass.states.get(uid("button", 1)) is not None
    assert hass.states.get(uid("port", "relay1")).state == STATE_OFF
    assert hass.states.get(uid("event", "tracking")).state == STATE_ON
    assert hass.states.get("switch.gate_switch_1").attributes["friendly_name"] == "Gate Switch 1"

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, f"2N:{GATE_MAC}"), entry.entry_id
    )
    assert device.model == "2N IP Verso"
    assert device.name == "Gate"

    await hass.config_entries.async_unload(entry.entry_id)


async def test_controls(hass: HomeAssistant, network) -> None:
    await _setup(hass)
    gate = network.intercoms[GATE["host"]]
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.gate_switch_2"}, blocking=True
    )
    assert gate.switches[2] is True
    assert hass.states.get("switch.gate_switch_2").state == STATE_ON
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.gate_switch_1_trigger"}, blocking=True
    )
    assert "/api/switch/ctrl?switch=1&action=trigger" in gate.commands


async def test_events_fired_unchanged(hass: HomeAssistant, network) -> None:
    """Log events reach the bus with the legacy event type and device_id."""
    await _setup(hass)
    events = async_capture_events(hass, EVENT)
    network.intercoms[GATE["host"]].pending_events = [
        {"id": 7, "utcTime": 1790000000, "event": "KeyPressed", "params": {"key": "%1"}}
    ]
    await _tick(hass)
    assert len(events) == 1
    assert events[0].data == {
        "id": 7,
        "utcTime": 1790000000,
        "event": "KeyPressed",
        "params": {"key": "%1"},
        "device_id": f"2N:{GATE_MAC}",
    }


async def test_resubscribes_after_restart(hass: HomeAssistant, network) -> None:
    await _setup(hass)
    gate = network.intercoms[GATE["host"]]
    gate.log_ids.clear()  # the intercom restarted
    await _tick(hass)
    assert hass.states.get("binary_sensor.gate_event_tracking").state == STATE_OFF
    await _tick(hass)
    assert hass.states.get("binary_sensor.gate_event_tracking").state == STATE_ON


async def test_partial_and_full_outage(hass: HomeAssistant, network) -> None:
    await _setup(hass)
    gate = network.intercoms[GATE["host"]]
    gate.disabled = {"switch"}
    await _tick(hass)
    assert hass.states.get("switch.gate_switch_1").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.gate_port_relay1").state == STATE_OFF

    gate.down = True
    await _tick(hass)
    assert hass.states.get("binary_sensor.gate_port_relay1").state == STATE_UNAVAILABLE

    gate.down = False
    gate.disabled = set()
    await _tick(hass)
    assert hass.states.get("switch.gate_switch_1").state == STATE_OFF


@pytest.mark.parametrize("down", [True, False])
async def test_setup_failures(hass: HomeAssistant, network, down: bool) -> None:
    gate = network.intercoms[GATE["host"]]
    if down:
        gate.down = True
    else:
        gate.password_ok = False
    entry = MockConfigEntry(domain=DOMAIN, title="Gate", unique_id=f"2N:{GATE_MAC}", data=GATE)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    if down:
        assert entry.state is ConfigEntryState.SETUP_RETRY
    else:
        assert entry.state is ConfigEntryState.SETUP_ERROR
        assert [f["context"]["source"] for f in hass.config_entries.flow.async_progress()] == [
            "reauth"
        ]


async def test_one_refused_section_keeps_polling(hass: HomeAssistant, network) -> None:
    """A 401 on one API (e.g. no rights to it) doesn't stop the others or start reauth."""
    await _setup(hass)
    gate = network.intercoms[GATE["host"]]
    gate.denied = {"switch"}
    events = async_capture_events(hass, EVENT)
    gate.pending_events = [{"id": 1, "event": "KeyPressed", "params": {"key": "%1"}}]
    await _tick(hass)
    assert hass.states.get("switch.gate_switch_1").state == STATE_UNAVAILABLE
    assert hass.states.get("button.gate_switch_1_trigger").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.gate_port_relay1").state == STATE_OFF
    assert len(events) == 1
    assert hass.config_entries.flow.async_progress() == []


async def test_all_refused_starts_reauth(hass: HomeAssistant, network) -> None:
    await _setup(hass)
    network.intercoms[GATE["host"]].password_ok = False
    await _tick(hass)
    assert [f["context"]["source"] for f in hass.config_entries.flow.async_progress()] == ["reauth"]


async def test_garbled_data_keeps_events(hass: HomeAssistant, network) -> None:
    await _setup(hass)
    gate = network.intercoms[GATE["host"]]
    gate.garbled = True
    events = async_capture_events(hass, EVENT)
    gate.pending_events = [{"id": 2, "event": "CodeEntered", "params": {"valid": True}}, "junk"]
    await _tick(hass)
    assert [e.data["event"] for e in events] == ["CodeEntered"]
    assert hass.states.get("binary_sensor.gate_port_relay1").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.gate_event_tracking").state == STATE_ON


async def test_second_entry_for_same_intercom(hass: HomeAssistant, network) -> None:
    """The same unit under another address is refused rather than polled twice."""
    await _setup(hass)
    network.intercoms["gate.local"] = network.intercoms[GATE["host"]]
    dup = MockConfigEntry(domain=DOMAIN, title="Gate again", data={**GATE, "host": "gate.local"})
    dup.add_to_hass(hass)
    await hass.config_entries.async_setup(dup.entry_id)
    await hass.async_block_till_done()
    assert dup.state is ConfigEntryState.SETUP_ERROR


async def test_diagnostics_redacted(hass: HomeAssistant, network) -> None:
    from custom_components.hass2n.diagnostics import async_get_config_entry_diagnostics

    entry = await _setup(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = str(diag)
    assert GATE_MAC not in text
    assert "pw" not in text
    assert diag["state"]["events"] == "**REDACTED**"


async def test_legacy_device_id_attribute(hass: HomeAssistant, network) -> None:
    await _setup(hass)
    assert hass.states.get("switch.gate_switch_1").attributes["device_id"] == 1
    assert hass.states.get("binary_sensor.gate_port_relay1").attributes["device_id"] == "relay1"
