import re

from device_registry import (
    get_device,
    get_device_key,
    resolve_device,
)
from homeassistant_client import HomeAssistantClient


def answer_device_command(
    message: str,
    current_request=None,
) -> str | None:
    """
    Handle deterministic Home Assistant device-control commands.

    Explicit device names establish conversational device context.
    Pronouns such as "it" can then resolve to that device.
    """
    text = message.strip().lower()

    device = resolve_device(message)

    # Resolve conversational commands such as "Turn it off."
    if (
        device is None
        and current_request is not None
        and current_request.device_key
        and re.search(r"\b(?:it|that)\b", text)
    ):
        device = get_device(current_request.device_key)

    if device is None:
        return None

    turn_on = bool(
        re.search(r"\bturn\s+(?:it\s+)?on\b", text)
        or re.search(r"\bswitch\s+(?:it\s+)?on\b", text)
    )

    turn_off = bool(
        re.search(r"\bturn\s+(?:it\s+)?off\b", text)
        or re.search(r"\bswitch\s+(?:it\s+)?off\b", text)
    )

    if not turn_on and not turn_off:
        return None

    client = HomeAssistantClient()
    entity_id = device["entity_id"]

    if turn_on:
        client.turn_on(entity_id)
        action = "on"
    else:
        client.turn_off(entity_id)
        action = "off"

    if current_request is not None:
        device_key = get_device_key(device)

        if device_key is not None:
            current_request.device_key = device_key

    room = device["room"]
    name = device["name"].lower()

    print(
        f"[DEVICE] {message!r} -> "
        f"{entity_id} -> {action}"
    )

    return f"Turning {action} the {room} {name}."
