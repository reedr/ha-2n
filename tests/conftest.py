"""Fixtures for 2N tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest

from custom_components.hass2n.device import TwoNDevice

from .fake_2n import FakeIntercom, FakeNetwork

pytest_plugins = ("pytest_homeassistant_custom_component",)

GATE = {"host": "10.0.0.21", "username": "ha", "password": "pw"}
DOOR = {"host": "10.0.0.22", "username": "ha", "password": "pw"}
GATE_MAC = "7c-1e-b3-00-00-01"
DOOR_MAC = "7c-1e-b3-00-00-02"


@pytest.fixture(autouse=True)
def enable_hass2n(enable_custom_integrations):
    """Allow Home Assistant to load the custom integration under test."""


@pytest.fixture
def network() -> Generator[FakeNetwork]:
    """Two fake intercoms, reached through a mock transport."""
    net = FakeNetwork()
    net.intercoms[GATE["host"]] = FakeIntercom(
        GATE_MAC, "Gate", "2N IP Verso", ["led_secured", "relay1", "output1", "input1"], 4
    )
    net.intercoms[DOOR["host"]] = FakeIntercom(
        DOOR_MAC, "Front Door", "2N IP Solo", ["led_secured", "relay1", "input1", "tamper"], 4
    )

    def make(host, username, password):
        return TwoNDevice(host, username, password, transport=net.transport)

    with (
        patch("custom_components.hass2n.TwoNDevice", make),
        patch("custom_components.hass2n.config_flow.TwoNDevice", make),
    ):
        yield net
