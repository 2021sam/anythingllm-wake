import re
import time

from device_registry import (
    DEVICES,
    get_device_key_by_entity_id,
)
from homeassistant_client import HomeAssistantClient


DISCOVERY_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 0.25


def is_physical_light_discovery_request(message: str) -> bool:
    """
    Detect requests where the person is asking how to operate
    the physical light in front of them.
    """
    text = message.strip().lower()

    patterns = [
        r"\bhow do i turn (?:this|the) light on\b",
        r"\bhow do i turn (?:this|the) light off\b",
        r"\bhow do i switch (?:this|the) light on\b",
        r"\bhow do i switch (?:this|the) light off\b",
        r"\bwhich switch controls (?:this|the) light\b",
        r"\bwhat switch controls (?:this|the) light\b",
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def _light_states(client: HomeAssistantClient) -> dict[str, str]:
    states = {}

    for entity in client.get_lights():
        entity_id = entity.get("entity_id")
        state = entity.get("state")

        if entity_id:
            states[entity_id] = state

    return states


def _friendly_device_name(entity_id: str) -> str | None:
    for device in DEVICES.values():
        if device["entity_id"] == entity_id:
            return f'{device["room"]} {device["name"].lower()}'

    return None


def watch_for_light_change(
    timeout: float = DISCOVERY_TIMEOUT_SECONDS,
    poll_interval: float = POLL_INTERVAL_SECONDS,
) -> dict | None:
    """
    Watch Home Assistant lights and return the first entity whose
    state changes during the discovery window.
    """
    client = HomeAssistantClient()
    before = _light_states(client)

    print(
        f"[DISCOVERY] Watching {len(before)} lights "
        f"for up to {timeout:g} seconds..."
    )

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        after = _light_states(client)

        changes = []

        for entity_id, new_state in after.items():
            old_state = before.get(entity_id)

            if old_state is not None and new_state != old_state:
                changes.append(
                    {
                        "entity_id": entity_id,
                        "before": old_state,
                        "after": new_state,
                        "friendly_name": _friendly_device_name(
                            entity_id
                        ),
                        "device_key": get_device_key_by_entity_id(
                            entity_id
                        ),
                    }
                )

        if len(changes) == 1:
            change = changes[0]

            print(
                "[DISCOVERY] Detected "
                f"{change['entity_id']}: "
                f"{change['before']} -> {change['after']}"
            )

            return change

        if len(changes) > 1:
            print(
                "[DISCOVERY] Multiple lights changed: "
                + ", ".join(
                    change["entity_id"]
                    for change in changes
                )
            )

            return {
                "multiple": True,
                "changes": changes,
            }

        before = after

    print("[DISCOVERY] No light change detected.")
    return None
