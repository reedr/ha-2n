# 2N Intercom

A Home Assistant integration for **2N IP intercoms** (IP Verso, IP Solo, IP Style and others with
the 2N HTTP API). It polls the intercom over HTTPS every 5 s and passes its event log to Home
Assistant as events.

## Entities

| Entity | What it does |
|---|---|
| `switch` Switch *N* | Activates the switch (relay or lock output) until turned off. |
| `button` Switch *N* trigger | Pulses the switch for its configured time, like the keypad does. |
| `binary_sensor` Port *name* | Input, output, relay, LED and tamper ports. |
| `binary_sensor` Event tracking | On while the event log is being followed (diagnostic). |

## Events

Every event in the intercom's log is fired on the Home Assistant bus as `hass2n_event`, with the
intercom's event fields plus `device_id: "2N:<mac>"`. For example, to react to call button 1:

```yaml
triggers:
  - trigger: event
    event_type: hass2n_event
    event_data:
      event: KeyPressed
      params: {key: "%1"}
      device_id: "2N:7c-1e-b3-xx-xx-xx"
```

Other useful events include `CodeEntered` (with `params.valid`), `CardEntered`, `CallStateChanged`,
`DoorStateChanged` and `SwitchStateChanged`. See 2N's HTTP API manual for the full list.

## Intercom setup

Enable the HTTP API (**Services → HTTP API**) over HTTPS with digest authentication, and create an
account with access to **System**, **I/O**, **Switches** and **Logging**. A missing permission
only takes out that part: e.g. without Switches, the switch entities stay unavailable.

## Install

Add this repository to HACS as a custom repository (category: Integration), download
**2N Intercom**, restart, then add **2N Intercom** under **Settings → Devices & services** with the
intercom's address and the API account. Each intercom is identified by its MAC address, so
**Reconfigure** can change its address or login without changing any entity IDs.

## Migrating from `reedr/hass2n`

The pre-HACS package (repository `reedr/hass2n`) used the domain `2N`; this one uses `hass2n`.
Entity unique IDs, the `hass2n_event` event and its payload are unchanged.

1. Install **2N Intercom** from HACS. It installs to `custom_components/hass2n`, replacing the old
   files. Restart Home Assistant.
2. The old entries now show as failed. Leave them in place.
3. **Settings → Devices & services → Add integration → 2N Intercom → Import the existing 2N setup**.
   Every old entry is imported with its host and login; devices and entities move across with
   their IDs, names, areas and history, and the old entries are removed.

New after migrating: a **trigger** button per switch, and the device shows the intercom's name,
model, firmware and serial number.
