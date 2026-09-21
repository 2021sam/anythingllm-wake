import re

from device_registry import (
    get_device,
    get_device_key,
    resolve_device,
)
from homeassistant_client import HomeAssistantClient
from device_action_tracker import ACTION_TRACKER


def _looks_like_home_control_command(text: str) -> bool:
    """
    Return True when speech resembles a device-control command.

    Unresolved commands are handled locally rather than sent to
    AnythingLLM. This prevents invented device actions.

    Whole-house/all-lights control is intentionally unsupported.
    """
    normalized = text.strip().lower()

    control_patterns = [
        r"\bturn\s+(?:on|off)\b",
        r"\bswitch\s+(?:on|off)\b",
        r"\b(?:lights?|lamps?)\s+(?:on|off)\b",

        # Broad imperative home-control requests must also stay inside
        # Jarvis's deterministic device layer. AnythingLLM is never
        # allowed to invent or claim successful Home Assistant actions.
        r"^(?:control|operate)\s+(?:the\s+)?"
        r"(?:lights?|light switches?|dimmers?)\b",
    ]

    return any(
        re.search(pattern, normalized)
        for pattern in control_patterns
    )


def _requests_all_lights(text: str) -> bool:
    """
    Detect whole-house or all-light requests.

    Jarvis intentionally does not execute these commands.
    """
    normalized = text.strip().lower()

    patterns = [
        r"\ball\s+(?:the\s+)?lights?\b",
        r"\bevery\s+light\b",
        r"\bevery\s+light\s+in\s+the\s+house\b",
        r"\bwhole\s+house\b.*\blights?\b",
        r"\blights?\b.*\bwhole\s+house\b",
    ]

    return any(
        re.search(pattern, normalized)
        for pattern in patterns
    )


def answer_device_command(
    message: str,
    current_request=None,
    allow_natural_fallback: bool = False,
) -> str | None:
    """
    Handle deterministic Home Assistant device-control commands.

    Explicit device names establish conversational device context.
    Pronouns such as "it" can then resolve to that device.
    """
    text = message.strip().lower()

    # Never execute whole-house/all-lights commands.
    # Jarvis requires a specific registered room/device.
    if _requests_all_lights(text):
        return (
            "I won't control all the lights at once. "
            "Please name a specific room or light."
        )

    device = resolve_device(message)

    # Resolve contextual commands such as:
    #   "Turn it off."
    #   "Turn that off."
    #   "Turn off."
    #
    # A bare on/off command may use the current device only when a
    # previous deterministic device command established that context.
    contextual_device_command = bool(
        re.fullmatch(
            r"(?:turn|switch)\s+"
            r"(?:(?:it|that)\s+)?"
            r"(?:on|off)[.!?]*",
            text,
        )
    )

    if (
        device is None
        and current_request is not None
        and current_request.device_key
        and (
            re.search(r"\b(?:it|that)\b", text)
            or contextual_device_command
        )
    ):
        device = get_device(current_request.device_key)

    # Device-looking commands must never fall through to AnythingLLM.
    # If there is no known target, ask for it instead of allowing the
    # LLM to invent devices or claim that an action occurred.
    incomplete_device_command = bool(
        re.fullmatch(
            r"(?:turn|switch)\s+"
            r"(?:(?:it|that)\s+)?"
            r"(?:on|off)[.!?]*",
            text,
        )
    )

    if device is None:
        if incomplete_device_command:
            return (
                "Turn on what?"
                if re.search(r"\bon\b", text)
                else "Turn off what?"
            )

        # Speech that still resembles a home-control command must
        # never fall through to AnythingLLM. The LLM is not allowed
        # to invent a device, automation, or successful action.
        if _looks_like_home_control_command(text):
            return (
                "Which specific room or light would you like "
                "me to control?"
            )

        return None

    turn_on = bool(
        re.search(r"\bturn\s+(?:it\s+)?on\b", text)
        or re.search(r"\bswitch\s+(?:it\s+)?on\b", text)
    )

    turn_off = bool(
        re.search(r"\bturn\s+(?:it\s+)?off\b", text)
        or re.search(r"\bswitch\s+(?:it\s+)?off\b", text)
    )

    # Questions about a registered device must read the real state
    # from Home Assistant rather than asking AnythingLLM.
    state_question = bool(
        re.search(
            r"\b(?:is|are)\b.*\b(?:on|off)\b",
            text,
        )
        or re.search(
            r"\bstate\b",
            text,
        )
        or re.search(
            r"\bstatus\b",
            text,
        )
    )

    if state_question:
        client = HomeAssistantClient()
        entity = client.get_state(device["entity_id"])
        state = entity.get("state", "unknown")

        room = device["room"]
        name = device["name"].lower()

        if current_request is not None:
            device_key = get_device_key(device)

            if device_key is not None:
                current_request.device_key = device_key

        print(
            f"[DEVICE STATE] {message!r} -> "
            f"{device['entity_id']} -> {state}"
        )

        if state in ("on", "off"):
            return f"The {room} {name} is {state}."

        if state == "unavailable":
            return (
                f"The {room} {name} is currently unavailable."
            )

        return (
            f"The {room} {name} currently reports {state}."
        )

    if not turn_on and not turn_off:
        # The utterance resolved to a registered device but the
        # deterministic parser did not understand the requested action.
        #
        # The request router may now give the safe natural-language
        # device interpreter a chance to understand it. This is NOT
        # ordinary AnythingLLM fallback; any resulting action still
        # requires deterministic validation before Home Assistant.
        if allow_natural_fallback:
            return None

        room = device["room"]
        name = device["name"].lower()

        if current_request is not None:
            device_key = get_device_key(device)

            if device_key is not None:
                current_request.device_key = device_key

        return (
            f"What would you like me to do with the "
            f"{room} {name}?"
        )

    client = HomeAssistantClient()
    entity_id = device["entity_id"]

    if turn_on:
        ACTION_TRACKER.expect(entity_id, "on")
        try:
            client.turn_on(entity_id)
        except Exception:
            ACTION_TRACKER.clear(entity_id)
            raise
        action = "on"
    else:
        ACTION_TRACKER.expect(entity_id, "off")
        try:
            client.turn_off(entity_id)
        except Exception:
            ACTION_TRACKER.clear(entity_id)
            raise
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


def execute_validated_device_intent(
    validated: dict,
    current_request=None,
) -> str | None:
    """
    Execute a device intent only after it passed the deterministic validator.

    The AI never supplies an entity ID. The entity ID always comes from
    the trusted device registry through the validated device object.
    """
    if not validated.get("allowed"):
        return None

    device = validated["device"]
    action = validated["action"]
    device_key = validated["device_key"]

    entity_id = device["entity_id"]
    room = device["room"]
    name = device["name"].lower()

    client = HomeAssistantClient()

    if action == "turn_on":
        ACTION_TRACKER.expect(entity_id, "on")
        try:
            client.turn_on(entity_id)
        except Exception:
            ACTION_TRACKER.clear(entity_id)
            raise
        response = f"Turning on the {room} {name}."

    elif action == "turn_off":
        ACTION_TRACKER.expect(entity_id, "off")
        try:
            client.turn_off(entity_id)
        except Exception:
            ACTION_TRACKER.clear(entity_id)
            raise
        response = f"Turning off the {room} {name}."

    elif action == "get_state":
        entity = client.get_state(entity_id)
        state = entity.get("state", "unknown")

        if state in ("on", "off"):
            response = f"The {room} {name} is {state}."
        elif state == "unavailable":
            response = (
                f"The {room} {name} is currently unavailable."
            )
        else:
            response = (
                f"The {room} {name} currently reports {state}."
            )

    elif action == "set_brightness":
        brightness_percent = validated["brightness_percent"]

        # Home Assistant light brightness uses the range 0-255.
        # The validator guarantees a percentage from 1-100.
        brightness = round(
            255 * brightness_percent / 100
        )

        ACTION_TRACKER.expect(
            entity_id,
            "on",
            brightness=brightness,
        )

        try:
            client.call_service(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "brightness": brightness,
                },
            )
        except Exception:
            ACTION_TRACKER.clear(entity_id)
            raise

        response = (
            f"Setting the {room} {name} to "
            f"{brightness_percent}%."
        )

    else:
        # Defense in depth. The validator should make this unreachable.
        return None

    if current_request is not None:
        current_request.device_key = device_key

    print(
        f"[NATURAL DEVICE] "
        f"{device_key} -> {entity_id} -> {action}"
    )

    return response
