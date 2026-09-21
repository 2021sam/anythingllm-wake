from __future__ import annotations

from device_action_tracker import should_suppress_device_change
from device_training import (
    get_training_mode,
    training_announcement,
)


def handle_device_change(
    change: dict,
    training_enabled=None,
    training_mode=None,
) -> str | None:
    """
    Decide whether a monitored Home Assistant change should produce
    a Training Mode announcement.

    This layer does not perform TTS. It only returns the text that may
    later be spoken.

    Rules:
      1. Jarvis-originated changes are suppressed.
      2. Training Mode OFF means silent monitoring.
      3. Training Mode ON describes manual/external registered changes.
    """
    entity_id = change["entity_id"]
    after = change["after"]

    if should_suppress_device_change(
        entity_id,
        after,
    ):
        print(
            f"[DEVICE MONITOR] Suppressed Jarvis change: "
            f"{entity_id}"
        )
        return None

    if training_mode is None:
        if training_enabled is None:
            training_mode = get_training_mode()
        else:
            # Compatibility for existing tests/callers.
            training_mode = (
                "normal"
                if training_enabled
                else "off"
            )

    if training_mode == "off":
        print(
            f"[DEVICE MONITOR] Silent external change: "
            f"{entity_id}"
        )
        return None

    device = change["device"]
    room = device["room"]
    name = device["name"].lower()
    state = after.get("state")

    if device.get("domain") != "light":
        announcement = None

    elif state == "on":
        if training_mode == "short":
            announcement = f"{room} {name} is on."
        elif training_mode == "long":
            announcement = (
                f"{room} {name} is on. "
                f"You can say, 'Turn off the {room} {name}.' "
                f"You can also say, 'Set the {room} {name} "
                f"to 50%,' or another brightness percentage."
            )
        else:
            announcement = (
                f"{room} {name} is on. "
                f"You can say, 'Turn off the {room} {name}.'"
            )

    elif state == "off":
        if training_mode == "short":
            announcement = f"{room} {name} is off."
        elif training_mode == "long":
            announcement = (
                f"{room} {name} is off. "
                f"You can say, 'Turn on the {room} {name}.' "
                f"You can also turn it on at a specific "
                f"brightness percentage."
            )
        else:
            announcement = (
                f"{room} {name} is off. "
                f"You can say, 'Turn on the {room} {name}.'"
            )

    else:
        announcement = None

    if announcement:
        print(
            f"[TRAINING MODE] External change: "
            f"{entity_id}"
        )

    return announcement
