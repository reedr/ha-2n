"""Constants for the 2N Intercom integration."""

from datetime import timedelta

DOMAIN = "hass2n"
# The pre-HACS package registered under this (invalid) domain.
LEGACY_DOMAIN = "2N"
MANUFACTURER = "2N"

# Fired for every entry in the intercom's event log. The name and payload are
# unchanged from the pre-HACS package, so existing automations keep working.
EVENT = "hass2n_event"

CONF_LEGACY_ENTRY = "legacy_entry_id"

UPDATE_INTERVAL = timedelta(seconds=5)
REQUEST_TIMEOUT = 10
# A request that hits a dropped keep-alive connection or a refused connect is
# retried once on a fresh connection after this pause (seconds).
RETRY_DELAY = 0.5
# Polls that fail on the network (not on the intercom's own API errors) keep the
# last good state until this many fail in a row, so a short blip on the path to
# the intercom doesn't flip every entity to unavailable.
UNAVAILABLE_AFTER = 3
