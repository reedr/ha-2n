"""Config, reauth and reconfigure flows."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hass2n.const import DOMAIN

from .conftest import DOOR, GATE, GATE_MAC


async def test_user_flow(hass: HomeAssistant, network) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**GATE, "host": f" {GATE['host']} "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Gate"
    assert result["data"] == GATE
    assert result["result"].unique_id == f"2N:{GATE_MAC}"
    await hass.async_block_till_done()


async def test_user_flow_errors(hass: HomeAssistant, network) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    network.intercoms[GATE["host"]].password_ok = False
    result = await hass.config_entries.flow.async_configure(result["flow_id"], GATE)
    assert result["errors"] == {"base": "invalid_auth"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**GATE, "host": "10.9.9.9"}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth(hass: HomeAssistant, network) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=f"2N:{GATE_MAC}", data={**GATE, "password": "old"}
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": "ha", "password": "new"}
    )
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new"
    await hass.async_block_till_done()


async def test_reconfigure_wrong_device(hass: HomeAssistant, network) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=f"2N:{GATE_MAC}", data=GATE)
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], DOOR)
    assert result["reason"] == "wrong_device"
