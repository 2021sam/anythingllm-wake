from __future__ import annotations

import time

from device_registry import DEVICES
from homeassistant_client import HomeAssistantClient


POLL_INTERVAL_SECONDS = 1.0
OUTAGE_RETRY_SECONDS = 5.0


def monitored_devices() -> dict[str, dict]:
    """
    Return registered devices keyed by Home Assistant entity ID.
    """
    return {
        device["entity_id"]: device
        for device in DEVICES.values()
        if device.get("entity_id")
    }


def normalized_device_state(entity: dict) -> dict:
    """
    Keep only the state information relevant to device monitoring.
    """
    attributes = entity.get("attributes") or {}

    return {
        "state": entity.get("state"),
        "brightness": attributes.get("brightness"),
    }


def read_registered_states(
    client: HomeAssistantClient,
) -> dict[str, dict]:
    """
    Read all registered devices.

    A read failure is allowed to propagate so DeviceMonitor can treat
    Home Assistant as temporarily unavailable instead of logging one
    error per device on every poll.
    """
    states = {}

    for entity_id in monitored_devices():
        entity = client.get_state(entity_id)
        states[entity_id] = normalized_device_state(entity)

    return states


def detect_state_changes(
    previous: dict[str, dict],
    current: dict[str, dict],
) -> list[dict]:
    """
    Compare two snapshots and return registered device changes.

    Initial observations are baseline only.
    """
    devices = monitored_devices()
    changes = []

    for entity_id, new_state in current.items():
        old_state = previous.get(entity_id)

        if old_state is None:
            continue

        if old_state == new_state:
            continue

        device = devices.get(entity_id)

        if device is None:
            continue

        changes.append(
            {
                "entity_id": entity_id,
                "device": device,
                "before": old_state,
                "after": new_state,
            }
        )

    return changes


class DeviceMonitor:
    """
    Poll registered Home Assistant devices and report state changes.

    Temporary Home Assistant outages do not destroy the last known
    baseline. This lets monitoring recover automatically.
    """

    def __init__(
        self,
        callback,
        poll_interval: float = POLL_INTERVAL_SECONDS,
        outage_retry: float = OUTAGE_RETRY_SECONDS,
        client: HomeAssistantClient | None = None,
    ):
        self.callback = callback
        self.poll_interval = poll_interval
        self.outage_retry = outage_retry
        self.client = client or HomeAssistantClient()
        self._previous = {}
        self._ha_available = True

    def _read_states(self) -> dict[str, dict] | None:
        try:
            states = read_registered_states(self.client)

        except Exception as exc:
            if self._ha_available:
                print(
                    "[DEVICE MONITOR] Home Assistant unavailable: "
                    f"{type(exc).__name__}: {exc}"
                )

            self._ha_available = False
            return None

        if not self._ha_available:
            print(
                "[DEVICE MONITOR] Home Assistant connection restored."
            )

        self._ha_available = True
        return states

    def initialize(self) -> bool:
        current = self._read_states()

        if current is None:
            return False

        self._previous = current
        return True

    def poll_once(self) -> list[dict]:
        current = self._read_states()

        if current is None:
            return []

        # If Jarvis started while HA was unavailable, the first
        # successful snapshot becomes the baseline rather than being
        # treated as a collection of new events.
        if not self._previous:
            self._previous = current
            return []

        changes = detect_state_changes(
            self._previous,
            current,
        )

        self._previous = current

        for change in changes:
            self.callback(change)

        return changes

    def run_forever(self) -> None:
        self.initialize()

        while True:
            if self._ha_available:
                time.sleep(self.poll_interval)
            else:
                time.sleep(self.outage_retry)

            self.poll_once()
