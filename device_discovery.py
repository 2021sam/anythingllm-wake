import re
import time

from device_action_tracker import expect_device_change
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


def get_active_light_candidates(
    client: HomeAssistantClient | None = None,
) -> list[dict]:
    """
    Return available light entities that Jarvis may actively identify.

    Likely wall dimmers are ranked first. Registered devices remain in
    the list so Jarvis can announce and demonstrate known locations too.
    """
    if client is None:
        client = HomeAssistantClient()

    candidates = []

    for entity in client.get_lights():
        entity_id = entity.get("entity_id")
        state = entity.get("state")

        if not entity_id or state in ("unavailable", "unknown"):
            continue

        attributes = entity.get("attributes", {})
        ha_name = attributes.get("friendly_name") or entity_id

        device_key = get_device_key_by_entity_id(entity_id)
        registered_name = _friendly_device_name(entity_id)

        searchable = f"{entity_id} {ha_name}".lower()
        looks_like_dimmer = (
            "dimmer" in searchable
            or "brightness" in attributes.get(
                "supported_color_modes",
                [],
            )
        )

        # Active discovery deliberately operates only likely dimmers.
        # Other light entities remain available to the original physical
        # switch discovery path, which is intentionally unchanged.
        if not looks_like_dimmer:
            continue

        candidates.append(
            {
                "entity_id": entity_id,
                "state": state,
                "ha_name": ha_name,
                "device_key": device_key,
                "registered_name": registered_name,
                "looks_like_dimmer": True,
                "attributes": attributes,
            }
        )

    candidates.sort(
        key=lambda item: (
            not item["looks_like_dimmer"],
            item["device_key"] is None,
            item["ha_name"].lower(),
        )
    )

    return candidates


def active_candidate_announcement(candidate: dict) -> str:
    """
    Return the human-facing name Jarvis should announce immediately
    before operating this candidate.
    """
    registered_name = candidate.get("registered_name")

    if registered_name:
        room = registered_name.rsplit(" ", 1)[0]
        return f"Testing the {room} dimmer."

    ha_name = candidate.get("ha_name") or candidate["entity_id"]
    return f"Testing {ha_name}."


def flick_light_candidate(
    candidate: dict,
    client: HomeAssistantClient | None = None,
    pause_seconds: float = 0.7,
) -> None:
    """
    Visibly identify one light, then restore its original state.

    Discovery uses full brightness temporarily so even a dimmer whose
    remembered brightness is extremely low can be identified visually.
    Normal Jarvis light-control behavior is not changed.
    """
    if client is None:
        client = HomeAssistantClient()

    entity_id = candidate["entity_id"]
    original_state = candidate["state"]
    original_brightness = candidate.get(
        "attributes",
        {},
    ).get("brightness")

    discovery_brightness = 255

    if original_state == "on":
        # Make an already-on light visibly change:
        # OFF -> full brightness -> original brightness.
        expect_device_change(entity_id, "off")
        client.turn_off(entity_id)
        time.sleep(pause_seconds)

        expect_device_change(
            entity_id,
            "on",
            brightness=discovery_brightness,
        )
        client.call_service(
            "light",
            "turn_on",
            {
                "entity_id": entity_id,
                "brightness": discovery_brightness,
            },
        )
        time.sleep(pause_seconds)

        if original_brightness is not None:
            expect_device_change(
                entity_id,
                "on",
                brightness=original_brightness,
            )
            client.call_service(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "brightness": original_brightness,
                },
            )
        else:
            expect_device_change(entity_id, "on")
            client.turn_on(entity_id)

    elif original_state == "off":
        # Make an off light unmistakably visible, then return it to off.
        expect_device_change(
            entity_id,
            "on",
            brightness=discovery_brightness,
        )
        client.call_service(
            "light",
            "turn_on",
            {
                "entity_id": entity_id,
                "brightness": discovery_brightness,
            },
        )
        time.sleep(pause_seconds)

        expect_device_change(entity_id, "off")
        client.turn_off(entity_id)

    else:
        raise ValueError(
            f"Cannot flick {entity_id} from state {original_state!r}"
        )

    print(
        f"[ACTIVE DISCOVERY] Tested {entity_id} "
        f"and restored state={original_state}"
    )


def is_active_light_discovery_request(message: str) -> bool:
    """
    Detect requests where Jarvis should actively cycle through dimmers
    so the person can visually identify them.
    """
    text = message.strip().lower()

    device_words = r"(?:lights?|dimmers?|light switches?)"

    patterns = [
        rf"\bidentify (?:the )?{device_words}\b",
        rf"\bfind (?:the )?{device_words}\b",
        rf"\btest (?:the )?{device_words}\b",
        rf"\bcycle through (?:the )?{device_words}\b",
        rf"\bshow me (?:the )?{device_words}\b",
        r"\bwhich (?:light|dimmer|light switch) is which\b",
        rf"\bhow (?:do|would) (?:you|i|we) test (?:the )?{device_words}\b",
        rf"\bhow (?:do|can) (?:you|i|we) identify (?:the )?{device_words}\b",
        rf"\bfigure out (?:which|what) {device_words}\b",
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def parse_active_discovery_confirmation(message: str) -> bool | None:
    """
    Interpret a short human confirmation during active discovery.

    True  -> the tested light visibly flicked
    False -> it did not
    None  -> unclear; ask again
    """
    text = re.sub(r"[^\w\s]", " ", message.lower())
    text = " ".join(text.split())

    yes_phrases = {
        "yes",
        "yeah",
        "yep",
        "yup",
        "hell yeah",
        "absolutely",
        "definitely",
        "sure",
        "for sure",
        "yes it did",
        "yeah it did",
        "that one",
        "that s it",
        "thats it",
        "i saw it",
        "it flicked",
        "the light flicked",
        "yes the light flicked",
        "yes the lights are flicking",
        "the lights are flicking",
    }

    no_phrases = {
        "no",
        "nope",
        "nah",
        "no it didn t",
        "no it didnt",
        "not that one",
        "i didn t see it",
        "i didnt see it",
        "nothing happened",
    }

    if text in yes_phrases:
        return True

    if text in no_phrases:
        return False

    return None
