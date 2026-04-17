"""2N Device."""

from json.decoder import JSONDecodeError
import logging
import re

import httpx

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

MAX_KEEPALIVE_TIME = 30.0

class Hass2NDeviceResponse:
    """API return status."""

    def __init__(self, resp: httpx.Response) -> None:
        """Set it up."""
        _LOGGER.debug("<- %d %s: %s", resp.status_code, resp.reason_phrase, re.sub("\\s+", " ", resp.text))
        self._status_code = resp.status_code
        if self._status_code == httpx.codes.OK:
            try:
                json = resp.json()
                if json.get("success"):
                    self._result = json.get("result")
                    return
            except JSONDecodeError:
                _LOGGER.error("JSON decode error")

            self._status_code = httpx.codes.INTERNAL_SERVER_ERROR
        self._result = None

    @property
    def status_code(self) -> int:
        """Return the last status."""
        return self._status_code

    @property
    def result(self) -> dict | None:
        """Return the result."""
        return self._result

    @property
    def has_result(self) -> bool:
        """Return true if result is valid."""
        return self._status_code == httpx.codes.OK and self._result is not None

    def result_value(self, key: str) -> str | None:
        """Return value from result or None."""
        if self.has_result:
            return self._result.get(key)
        return None



class Hass2NDevice:  # noqa: D101
    """Device interface."""

    def __init__(
        self, hass: HomeAssistant, host: str, username: str, password: str
    ) -> None:
        """Set up class."""

        self._hass = hass
        self._host = host
        self._username = username
        self._password = password
        self._auth = httpx.DigestAuth(username=username, password=password)
        self._client = httpx.AsyncClient(base_url="https://"+self._host,
                                         auth=self._auth,
                                         verify=False)
        self._device_name = None
        self._mac_addr = None
        self._device_id = None
        self._callbacks = set()
        self._system_info: dict | None
        self._log_id = None
        self._response = None
        self._switches_online = False
        self._ports_online = False
        self._events_online = False

    @property
    def device_id(self) -> str:
        """Use the mac."""
        return self._device_id

    @property
    def system_info(self) -> dict:
        """Return device info."""
        return self._system_info

    @property
    def ports_online(self) -> bool:
        """Return online."""
        return self._ports_online

    @property
    def switches_online(self) -> bool:
        """Return online."""
        return self._switches_online

    @property
    def events_online(self) -> bool:
        """Return online."""
        return self._events_online

    @property
    def online(self) -> bool:
        """Return any online."""
        return self._events_online or self._ports_online or self._switches_online

    async def api_call(self, uri: str) -> bool:
        """Make an API call."""
        tries = 2
        while tries > 0:
            try:
                _LOGGER.debug("-> GET %s", uri)
                resp = await self._client.get(uri)
                self._response = Hass2NDeviceResponse(resp)
                return self._response.status_code == httpx.codes.OK

            except httpx.RemoteProtocolError as exc:
                _LOGGER.error("GET error (%s): %s", self.device_id, exc)
            tries -= 1

        return False

    async def api_get(self, uri: str) -> bool:
        """Get some API info."""
        return await self.api_call(uri) and self._response.has_result

    async def get_system_info(self) -> bool:
        """Load initial system info."""
        if not await self.api_get("/api/system/info"):
            return False

        self._system_info = self._response.result
        self._device_name = self._response.result_value("deviceName")
        self._mac_addr = self._response.result_value("macAddr")
        self._device_id = "2N:" + self._mac_addr
        return True

    async def get_status(self) -> dict | None:
        """Load the current status."""
        status = {}
        self._ports_online = await self.api_get("/api/io/status")
        if self._ports_online:
            status["ports"] = self._response.result_value("ports")

        self._switches_online = await self.api_get("/api/switch/status")
        if self._switches_online:
            status["switches"] = self._response.result_value("switches")

        if self._log_id is None and await self.api_get("/api/log/subscribe"):
            self._log_id = self._response.result_value("id")

        self._events_online = (self._log_id is not None
                               and await self.api_get(f"/api/log/pull?id={self._log_id}"))
        if self._events_online:
            status["events"] = self._response.result_value("events")
        else:
            self._log_id = None

        return status

    async def async_turn_on (self, key: str) -> bool:
        """Turn sw on."""
        return await self.api_call(f"/api/switch/ctrl?switch={key}&action=on")

    async def async_turn_off (self, key: str) -> bool:
        """Turn sw off."""
        return await self.api_call(f"/api/switch/ctrl?switch={key}&action=off")

    async def async_press (self, key: str) -> bool:
        """Momentary sw."""
        return await self.api_call(f"/api/switch/ctrl?switch={key}&action=trigger")


    def register_callback(self, callback) -> None:
        """Register callback, called when device changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)
