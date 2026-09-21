from unittest.mock import patch

from conversation_service import CASUAL, DIRECT, classify_utterance
from device_control import execute_validated_device_intent
from device_intent_validator import validate_device_intent


class FakeHA:
    calls = []

    def call_service(self, domain, service, data):
        self.__class__.calls.append(
            (domain, service, data)
        )
        return {}


def validate_brightness(percent):
    return validate_device_intent(
        {
            "intent": "device_action",
            "device_key": "family_room_light",
            "action": "set_brightness",
            "brightness_percent": percent,
            "confidence": 0.98,
            "clarification": None,
        }
    )


# Valid brightness boundaries and normal values.
for percent in (1, 5, 10, 50, 100):
    validated = validate_brightness(percent)
    assert validated["allowed"]
    assert validated["brightness_percent"] == percent


# Invalid brightness values must never reach Home Assistant.
for percent in (0, 101, None, "50", True):
    validated = validate_brightness(percent)
    assert not validated["allowed"]
    assert validated["reason"] == "invalid_brightness"


# Verify deterministic 50% -> 128/255 execution.
FakeHA.calls.clear()

validated = validate_brightness(50)

with patch(
    "device_control.HomeAssistantClient",
    FakeHA,
):
    answer = execute_validated_device_intent(validated)

assert answer == "Setting the Family Room light to 50%."

assert FakeHA.calls == [
    (
        "light",
        "turn_on",
        {
            "entity_id": "light.wall_dimmer_1",
            "brightness": 128,
        },
    )
]


# Conversation mode must allow dimming requests through.
for text in (
    "Dim the Family Room light to 50%.",
    "Dim the Family Room light to 10%.",
    "Dim the light to 1%.",
    "Could you dim the Family Room light to 5%?",
):
    assert (
        classify_utterance(
            text,
            active_conversation=True,
        )
        == DIRECT
    )


# Ordinary background conversation should still be ignored.
assert (
    classify_utterance(
        "I really like this game.",
        active_conversation=True,
    )
    == CASUAL
)

print("ALL DEVICE BRIGHTNESS TESTS PASSED")
