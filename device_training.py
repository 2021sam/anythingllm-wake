from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
TRAINING_MODE_FILE = BASE_DIR / ".device_training_mode"


def brightness_to_percent(brightness) -> int | None:
    """
    Convert Home Assistant's 0-255 brightness value to a human percentage.
    """
    if brightness is None:
        return None

    try:
        value = int(brightness)
    except (TypeError, ValueError):
        return None

    value = max(0, min(255, value))
    return round(value * 100 / 255)


TRAINING_MODES = {
    "off",
    "short",
    "normal",
    "long",
}

DEFAULT_TRAINING_MODE = "off"


def get_training_mode() -> str:
    """
    Return the persistent Training Mode level.

    Legacy values from the original boolean implementation are accepted
    so existing installations migrate cleanly.
    """
    if not TRAINING_MODE_FILE.exists():
        return DEFAULT_TRAINING_MODE

    value = TRAINING_MODE_FILE.read_text().strip().lower()

    if value in TRAINING_MODES:
        return value

    if value in {"1", "true", "on", "yes", "enabled"}:
        return "normal"

    return DEFAULT_TRAINING_MODE


def training_mode_enabled() -> bool:
    return get_training_mode() != "off"


def set_training_mode(mode: str | bool) -> None:
    """
    Persist off, short, normal, or long.

    Boolean input remains supported for compatibility with existing
    callers: True means normal and False means off.
    """
    if isinstance(mode, bool):
        mode = "normal" if mode else "off"

    mode = str(mode).strip().lower()

    if mode not in TRAINING_MODES:
        raise ValueError(
            f"Invalid Training Mode: {mode}"
        )

    TRAINING_MODE_FILE.write_text(f"{mode}\n")


def training_announcement(
    device: dict,
    state: str,
    attributes: dict | None = None,
) -> str | None:
    """
    Describe a manually/external changed registered light and teach one
    useful voice command.

    This function does not decide whether the change was caused by Jarvis.
    The background monitor will handle source suppression separately.
    """
    if device.get("domain") != "light":
        return None

    room = device["room"]
    name = device["name"].lower()
    attributes = attributes or {}

    if state == "off":
        return (
            f"{room} {name} is off. "
            f"You can say, 'Turn on the {room} {name}.'"
        )

    if state != "on":
        return None

    brightness_percent = brightness_to_percent(
        attributes.get("brightness")
    )

    if brightness_percent is None:
        return (
            f"{room} {name} is on. "
            f"You can say, 'Turn off the {room} {name}.'"
        )

    if brightness_percent < 100:
        return (
            f"{room} {name} is on at {brightness_percent}%. "
            f"You can say, 'Set the {room} {name} to 100%.'"
        )

    return (
        f"{room} {name} is on at 100%. "
        f"You can say, 'Turn off the {room} {name}.'"
    )


def answer_training_mode_command(message: str) -> str | None:
    """
    Handle deterministic Training Mode voice commands.

    Training, learning, and hint mode are aliases.
    """
    import re

    text = message.strip().lower()

    mode_pattern = (
        r"(?:training|learning|hint)\s+mode"
        r"|(?:light|device)\s+hints?"
        r"|voice\s+command\s+hints?"
    )

    if not re.search(mode_pattern, text):
        return None

    current = get_training_mode()

    status_patterns = [
        r"\bis\b.*\b(?:training|learning|hint)\s+mode\b",
        r"\bwhat\b.*\b(?:training|learning|hint)\s+mode\b",
        r"\b(?:training|learning|hint)\s+mode\b.*\bstatus\b",
        r"\bare\b.*\b(?:light|device)\s+hints?\b",
    ]

    if any(re.search(pattern, text) for pattern in status_patterns):
        if current == "off":
            return "Training Mode is off."

        # Yes/no status questions should report whether Training Mode is
        # enabled, rather than confusing the enabled level ("normal")
        # with the enabled/disabled state.
        if re.search(
            r"\b(?:is|are)\b.*\b(?:enabled|on|active)\b"
            r"|\b(?:is|are)\b.*\b(?:training|learning|hint)\s+mode\b.*\b(?:enabled|on|active)\b",
            text,
        ):
            return "Training Mode is enabled."

        return f"Training Mode is {current}."

    off_patterns = [
        r"\bturn\s+off\b",
        r"\bswitch\s+off\b",
        r"\bdisable\b",
        r"\bstop\b",
        r"\bno\s+more\b",
    ]

    if any(re.search(pattern, text) for pattern in off_patterns):
        set_training_mode("off")
        return "Training Mode is off."

    requested_level = None

    if re.search(r"\bshort(?:er)?\b", text):
        requested_level = "short"
    elif re.search(r"\blong(?:er)?\b", text):
        requested_level = "long"
    elif re.search(r"\bnormal\b", text):
        requested_level = "normal"

    on_patterns = [
        r"\bturn\s+on\b",
        r"\bswitch\s+on\b",
        r"\benable\b",
        r"\bstart\b",
    ]

    if requested_level is not None:
        set_training_mode(requested_level)
        return f"Training Mode is {requested_level}."

    if any(re.search(pattern, text) for pattern in on_patterns):
        set_training_mode("normal")
        return "Training Mode is normal."

    if current == "off":
        return "Training Mode is off."

    return f"Training Mode is {current}."



def training_brightness_followup(
    device: dict,
    state: str,
    attributes: dict | None = None,
) -> str | None:
    """
    Build the second part of an off -> on training announcement.

    This should be called with a fresh Home Assistant state after the
    initial "light is on" message has finished playing.
    """
    if device.get("domain") != "light":
        return None

    if state != "on":
        return None

    room = device["room"]
    name = device["name"].lower()
    attributes = attributes or {}

    brightness_percent = brightness_to_percent(
        attributes.get("brightness")
    )

    if brightness_percent is None:
        return (
            f"You can say, 'Turn off the {room} {name}.'"
        )

    if brightness_percent < 100:
        return (
            f"It's at {brightness_percent}%. "
            f"You can say, "
            f"'Set the {room} {name} to 100%.'"
        )

    return (
        "It's at 100%. "
        f"You can say, 'Turn off the {room} {name}.'"
    )


def settled_light_announcement(
    device: dict,
    state: str,
    attributes: dict | None,
    mode: str,
) -> str | None:
    """
    Describe a freshly re-read light state according to Training Mode.
    Used after a physical off -> on transition has had time to settle.
    """
    if device.get("domain") != "light":
        return None

    if state != "on":
        return None

    room = device["room"]
    name = device["name"].lower()
    attributes = attributes or {}

    brightness_percent = brightness_to_percent(
        attributes.get("brightness")
    )

    if mode == "short":
        if brightness_percent is None:
            return f"{room} {name} is on."

        return (
            f"{room} {name} is on at "
            f"{brightness_percent}%."
        )

    followup = training_brightness_followup(
        device,
        state,
        attributes,
    )

    if mode == "long" and followup:
        return (
            f"{followup} "
            "You can also set the brightness to any "
            "percentage from 1 to 100."
        )

    return followup
