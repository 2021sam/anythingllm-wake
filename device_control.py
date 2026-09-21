import re

from device_registry import (
    get_device,
    get_device_key,
    resolve_device,
)
from homeassistant_client import HomeAssistantClient


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
        # The utterance resolved to a real registered device, but it
        # was not an actionable on/off command. Do not pass the device
        # reference to AnythingLLM, because the LLM must not invent
        # device state, configuration, capabilities, or actions.
        #
        # Actual device-state questions will get their own deterministic
        # Home Assistant read path.
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
