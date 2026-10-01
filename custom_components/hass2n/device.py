"""2N IP intercom HTTP API client."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from . import const

_LOGGER = logging.getLogger(__name__)


class TwoNError(Exception):
    """Base error."""


class TwoNConnectionError(TwoNError):
    """The intercom could not be reached or gave an unusable answer."""


class TwoNAuthError(TwoNError):
    """The intercom rejected the username or password."""


@dataclass(frozen=True)
class TwoNInfo:
    """Identity from /api/system/info."""

    device_id: str  # "2N:<mac>", as used in event payloads and unique IDs
    name: str
    model: str | None
    serial: str | None
    sw_version: str | None
    mac: str
    raw: dict[str, Any] = field(repr=False, compare=False)


@dataclass(frozen=True)
class TwoNState:
    """One poll. A section is None when its API call failed."""

    ports: dict[str, int] | None = None
    switches: dict[int, bool] | None = None
    events_online: bool = False
    events: list[dict[str, Any]] = field(default_factory=list, compare=False)


class TwoNDevice:
    """A 2N IP intercom over HTTPS with digest auth."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Set up the client. The intercom's certificate is self-signed."""
        self.host = host
        self._client = httpx.AsyncClient(
            base_url=f"https://{host}",
            auth=httpx.DigestAuth(username=username, password=password),
            verify=False,
            timeout=const.REQUEST_TIMEOUT,
            transport=transport,
        )
        self._log_id: int | None = None
        self.info: TwoNInfo | None = None

    async def async_close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def _get(self, path: str) -> dict[str, Any]:
        """GET an API path and return its result object."""
        _LOGGER.debug("%s -> GET %s", self.host, path)
        try:
            resp = await self._client.get(path)
        except httpx.HTTPError as err:
            raise TwoNConnectionError(f"{self.host}: {err!r}") from err
        _LOGGER.debug(
            "%s <- %d %s", self.host, resp.status_code, re.sub(r"\s+", " ", resp.text)
        )
        if resp.status_code in (httpx.codes.UNAUTHORIZED, httpx.codes.FORBIDDEN):
            raise TwoNAuthError(f"{self.host} rejected the login ({resp.status_code})")
        if resp.status_code != httpx.codes.OK:
            raise TwoNConnectionError(f"{self.host} {path}: HTTP {resp.status_code}")
        try:
            body = resp.json()
        except ValueError as err:
            raise TwoNConnectionError(f"{self.host} {path}: not JSON") from err
        if not body.get("success"):
            raise TwoNConnectionError(f"{self.host} {path}: {body.get('error')}")
        return body.get("result") or {}

    async def async_get_info(self) -> TwoNInfo:
        """Read the intercom's identity."""
        result = await self._get("/api/system/info")
        mac = result.get("macAddr")
        if not mac:
            raise TwoNConnectionError(f"{self.host} did not report a MAC address")
        self.info = TwoNInfo(
            device_id=f"2N:{mac}",
            name=result.get("deviceName") or "2N Intercom",
            model=result.get("variant"),
            serial=result.get("serialNumber"),
            sw_version=result.get("swVersion"),
            mac=mac,
            raw=result,
        )
        return self.info

    async def async_update(self) -> TwoNState:
        """Poll ports, switches and new log events.

        Each section fails on its own, as the intercom can disable APIs one by
        one. Only a wrong login, or every section failing, raises.
        """
        errors: list[TwoNError] = []

        async def section(path: str, key: str) -> list[dict[str, Any]] | None:
            try:
                return (await self._get(path)).get(key) or []
            except TwoNAuthError:
                raise
            except TwoNError as err:
                errors.append(err)
                return None

        ports = await section("/api/io/status", "ports")
        switches = await section("/api/switch/status", "switches")

        events: list[dict[str, Any]] | None = None
        if self._log_id is None:
            subscribed = await section("/api/log/subscribe", "id")
            self._log_id = subscribed if isinstance(subscribed, int) else None
        if self._log_id is not None:
            events = await section(f"/api/log/pull?id={self._log_id}", "events")
            if events is None:
                # The subscription lapses when the intercom restarts.
                self._log_id = None

        if ports is None and switches is None and events is None:
            raise TwoNConnectionError("; ".join(str(err) for err in errors))
        return TwoNState(
            ports=None if ports is None else {p["port"]: p["state"] for p in ports},
            switches=(
                None if switches is None else {s["switch"]: bool(s["active"]) for s in switches}
            ),
            events_online=events is not None,
            events=events or [],
        )

    async def _switch(self, switch: int, action: str) -> None:
        await self._get(f"/api/switch/ctrl?switch={switch}&action={action}")

    async def async_turn_on(self, switch: int) -> None:
        """Activate a switch until turned off."""
        await self._switch(switch, "on")

    async def async_turn_off(self, switch: int) -> None:
        """Deactivate a switch."""
        await self._switch(switch, "off")

    async def async_trigger(self, switch: int) -> None:
        """Pulse a switch for its configured time (e.g. a door strike)."""
        await self._switch(switch, "trigger")

    async def async_test_connection(self) -> TwoNInfo:
        """Read the identity and close."""
        try:
            return await self.async_get_info()
        finally:
            await self.async_close()
