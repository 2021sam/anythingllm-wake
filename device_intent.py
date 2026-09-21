"""
Natural-language device intent interpretation for Jarvis.

This module interprets speech only. It NEVER controls Home Assistant.
Any proposed action must pass the deterministic validator before execution.
"""

import json
import time

import requests

from device_registry import DEVICES


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"


def _known_devices() -> str:
    lines = []

    for device_key, device in DEVICES.items():
        aliases = ", ".join(device.get("aliases", []))

        lines.append(
            f"{device_key}\n"
            f"  room: {device['room']}\n"
            f"  device: {device['name']}\n"
            f"  aliases: {aliases}"
        )

    return "\n".join(lines)


def _schema() -> dict:
    device_keys = list(DEVICES.keys())

    return {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "device_action",
                    "clarify",
                    "blocked",
                    "not_device",
                ],
            },
            "device_key": {
                "type": ["string", "null"],
                "enum": device_keys + [None],
            },
            "action": {
                "type": ["string", "null"],
                "enum": [
                    "turn_on",
                    "turn_off",
                    "get_state",
                    "set_brightness",
                    None,
                ],
            },
            "brightness_percent": {
                "type": ["integer", "null"],
                "minimum": 1,
                "maximum": 100,
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "clarification": {
                "type": ["string", "null"],
            },
        },
        "required": [
            "intent",
            "device_key",
            "action",
            "brightness_percent",
            "confidence",
            "clarification",
        ],
        "additionalProperties": False,
    }


def _safe_clarify(message: str) -> dict:
    return {
        "intent": "clarify",
        "device_key": None,
        "action": None,
        "brightness_percent": None,
        "confidence": 0.0,
        "clarification": message,
    }


def interpret_device_intent(
    message: str,
    context_device_key: str | None = None,
) -> dict:
    """
    Interpret natural speech into a proposed device intent.

    This function does not call Home Assistant and cannot execute
    a device action.
    """

    context_text = (
        context_device_key
        if context_device_key in DEVICES
        else "none"
    )

    prompt = f"""
You are the device-intent interpreter for Jarvis.
You interpret meaning only. You NEVER control anything.

REGISTERED DEVICES:
{_known_devices()}

CURRENT CONVERSATION DEVICE:
{context_text}

CRITICAL SAFETY RULES:

1. Only registered devices exist.

2. NEVER substitute one room or device for another.

3. If the person explicitly names an unregistered room or
device, return clarify with device_key=null and action=null.

Example:
"Turn on the kitchen light."
If Kitchen is not registered:
intent=clarify
device_key=null
action=null

NEVER map an unknown room onto a registered room.

4. Whole-house commands such as:
"all the lights"
"every light"
"all lights in the house"
are blocked.

For blocked requests:
device_key=null
action=null.

5. For not_device:
device_key=null
action=null.

6. For clarify:
If the intended action is not safe and certain,
action must be null.

7. A direct explicit command involving a registered device
should normally have high confidence.

8. The CURRENT CONVERSATION DEVICE may only resolve clear
references such as "it", "that", or "the light".
Do not use conversation context to override an explicitly
named room or device.

Examples:

"Could you shut the Family Room light off?"
intent=device_action
device_key=family_room_light
action=turn_off
confidence=0.98

"Is the Family Room light on?"
intent=device_action
device_key=family_room_light
action=get_state
brightness_percent=null
confidence=0.98

"Dim the Family Room light to 50%."
intent=device_action
device_key=family_room_light
action=set_brightness
brightness_percent=50
confidence=0.98

"Set the Family Room light to 25%."
intent=device_action
device_key=family_room_light
action=set_brightness
brightness_percent=25
confidence=0.98

"It's dark in the Family Room. Could you get the light for me?"
intent=device_action
device_key=family_room_light
action=turn_on
confidence=0.95

"The Family Room is too dark. Can you do something about that?"
intent=device_action
device_key=family_room_light
action=turn_on
confidence=0.90

"Can you get the Family Room light?"
intent=clarify
device_key=family_room_light
action=null

"Turn off all the lights."
intent=blocked
device_key=null
action=null

"What's the capital of France?"
intent=not_device
device_key=null
action=null

SPEECH:
{message}
"""

    start = time.monotonic()

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": _schema(),
                "options": {
                    "temperature": 0,
                    "num_predict": 80,
                },
                "keep_alive": "30m",
            },
            timeout=15,
        )

        response.raise_for_status()

        elapsed = time.monotonic() - start
        print(f"[TIMING] device_intent_ollama={elapsed:.3f}s")

        raw = response.json()["response"]
        result = json.loads(raw)

        return result

    except (
        requests.RequestException,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"[DEVICE INTENT ERROR] {exc}")

        return _safe_clarify(
            "I couldn't safely interpret that device request."
        )
