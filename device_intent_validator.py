"""
Safety boundary between AI intent interpretation and Home Assistant.

The AI may propose an action, but only this deterministic layer decides
whether that proposal is allowed to proceed.
"""

from device_registry import get_device


ALLOWED_ACTIONS = {
    "turn_on",
    "turn_off",
    "get_state",
    "set_brightness",
}

MINIMUM_CONFIDENCE = 0.85


def validate_device_intent(result: dict) -> dict:
    """
    Validate an AI-produced device intent without executing anything.
    """
    if not isinstance(result, dict):
        return {
            "allowed": False,
            "reason": "invalid_result",
        }

    intent = result.get("intent")

    if intent == "blocked":
        return {
            "allowed": False,
            "reason": "blocked",
        }

    if intent != "device_action":
        return {
            "allowed": False,
            "reason": intent or "unknown",
        }

    device_key = result.get("device_key")
    action = result.get("action")
    confidence = result.get("confidence", 0.0)

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    if confidence < MINIMUM_CONFIDENCE:
        return {
            "allowed": False,
            "reason": "low_confidence",
        }

    device = get_device(device_key)

    if device is None:
        return {
            "allowed": False,
            "reason": "unknown_device",
        }

    if action not in ALLOWED_ACTIONS:
        return {
            "allowed": False,
            "reason": "unsupported_action",
        }

    validated = {
        "allowed": True,
        "reason": None,
        "device_key": device_key,
        "action": action,
        "device": device,
    }

    if action == "set_brightness":
        brightness_percent = result.get("brightness_percent")

        # Do not silently round or coerce arbitrary model output.
        # The intent interpreter must provide a whole-number percentage.
        if (
            isinstance(brightness_percent, bool)
            or not isinstance(brightness_percent, int)
            or not 1 <= brightness_percent <= 100
        ):
            return {
                "allowed": False,
                "reason": "invalid_brightness",
            }

        validated["brightness_percent"] = brightness_percent

    return validated
