"""A fake 2N intercom HTTP API, served through httpx.MockTransport."""

from __future__ import annotations

from typing import Any

import httpx


class FakeIntercom:
    """Serves system info, I/O, switches, the event log and switch control."""

    def __init__(self, mac: str, name: str, variant: str, ports: list[str], switches: int) -> None:
        self.mac = mac
        self.name = name
        self.variant = variant
        self.ports = dict.fromkeys(ports, 0)
        self.switches = dict.fromkeys(range(1, switches + 1), False)
        self.password_ok = True
        self.down = False
        self.disabled: set[str] = set()
        self.pending_events: list[dict[str, Any]] = []
        self.log_ids: set[int] = set()
        self.commands: list[str] = []

    def _ok(self, result: dict[str, Any]) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "result": result})

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("down", request=request)
        if "authorization" not in request.headers:
            return httpx.Response(
                401,
                headers={"WWW-Authenticate": 'Digest realm="HTTP API", qop="auth", nonce="abc"'},
            )
        if not self.password_ok:
            return httpx.Response(401)
        path, params = request.url.path, request.url.params
        self.commands.append(str(request.url.raw_path, "ascii"))
        if path.startswith("/api/") and path.split("/")[2] in self.disabled:
            return httpx.Response(200, json={"success": False, "error": {"code": 8}})
        if path == "/api/system/info":
            return self._ok(
                {
                    "variant": self.variant,
                    "serialNumber": "54-0000-0000",
                    "macAddr": self.mac,
                    "swVersion": "2.49.0.75.4",
                    "deviceName": self.name,
                }
            )
        if path == "/api/io/status":
            return self._ok({"ports": [{"port": p, "state": s} for p, s in self.ports.items()]})
        if path == "/api/switch/status":
            return self._ok(
                {
                    "switches": [
                        {"switch": n, "active": a, "locked": False, "held": False}
                        for n, a in self.switches.items()
                    ]
                }
            )
        if path == "/api/log/subscribe":
            log_id = 1000 + len(self.log_ids)
            self.log_ids.add(log_id)
            return self._ok({"id": log_id})
        if path == "/api/log/pull":
            if int(params["id"]) not in self.log_ids:
                return httpx.Response(200, json={"success": False, "error": {"code": 12}})
            events, self.pending_events = self.pending_events, []
            return self._ok({"events": events})
        if path == "/api/switch/ctrl":
            n, action = int(params["switch"]), params["action"]
            if n not in self.switches:
                return httpx.Response(200, json={"success": False, "error": {"code": 14}})
            if action in ("on", "off"):
                self.switches[n] = action == "on"
            return self._ok({})
        return httpx.Response(404)


class FakeNetwork:
    """Routes requests to fake intercoms by host."""

    def __init__(self) -> None:
        self.intercoms: dict[str, FakeIntercom] = {}
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        intercom = self.intercoms.get(request.url.host)
        if intercom is None:
            raise httpx.ConnectError("no route", request=request)
        return intercom.handle(request)
