from unittest.mock import patch

from current_request import CurrentRequest
from device_control import answer_device_command


class FakeHomeAssistantClient:
    calls = []

    def turn_on(self, entity_id):
        self.calls.append(("on", entity_id))

    def turn_off(self, entity_id):
        self.calls.append(("off", entity_id))


current = CurrentRequest()

with patch(
    "device_control.HomeAssistantClient",
    FakeHomeAssistantClient,
):
    FakeHomeAssistantClient.calls = []

    answer = answer_device_command(
        "Turn on the Family Room light.",
        current,
    )

    assert answer == "Turning on the Family Room light."
    assert current.device_key == "family_room_light"

    answer = answer_device_command(
        "Turn it off.",
        current,
    )

    assert answer == "Turning off the Family Room light."

    assert FakeHomeAssistantClient.calls == [
        ("on", "light.wall_dimmer_1"),
        ("off", "light.wall_dimmer_1"),
    ]

print("ALL DEVICE CONTEXT TESTS PASSED")


# A bare command may use an already-established device context.
current = CurrentRequest()

with patch(
    "device_control.HomeAssistantClient",
    FakeHomeAssistantClient,
):
    FakeHomeAssistantClient.calls = []

    answer = answer_device_command(
        "Turn on the Family Room light.",
        current,
    )

    assert current.device_key == "family_room_light"

    FakeHomeAssistantClient.calls = []

    answer = answer_device_command(
        "Turn off.",
        current,
    )

    assert answer == "Turning off the Family Room light."
    assert FakeHomeAssistantClient.calls == [
        ("off", "light.wall_dimmer_1")
    ]


# Without established context, a bare command must NOT fall through
# to AnythingLLM or guess which home device the person meant.
current = CurrentRequest()

with patch(
    "device_control.HomeAssistantClient",
    FakeHomeAssistantClient,
):
    FakeHomeAssistantClient.calls = []

    answer = answer_device_command(
        "Turn off.",
        current,
    )

    assert answer == "Turn off what?"
    assert FakeHomeAssistantClient.calls == []

print("ALL BARE DEVICE CONTEXT TESTS PASSED")

from conversation_service import DIRECT, classify_utterance

assert classify_utterance(
    "I changed my mind, make it 5%.",
    active_conversation=True,
) == DIRECT

assert classify_utterance(
    "I change my mind, make it 5%.",
    active_conversation=True,
) == DIRECT

assert classify_utterance(
    "Make it 20%.",
    active_conversation=True,
) == DIRECT

assert classify_utterance(
    "Actually, make it 50%.",
    active_conversation=True,
) == DIRECT

print("ALL NATURAL DEVICE FOLLOW-UP CLASSIFIER TESTS PASSED")

# Natural correction phrases during active device conversation.
assert classify_utterance(
    "Never mind, set it to 90.",
    active_conversation=True,
) == DIRECT

assert classify_utterance(
    "Nevermind set it to 90.",
    active_conversation=True,
) == DIRECT

assert classify_utterance(
    "Never mind, make it 25%.",
    active_conversation=True,
) == DIRECT

print("ALL NEVER-MIND DEVICE FOLLOW-UP TESTS PASSED")

# Conversational filler or imperfect STT before an unmistakable
# contextual device command must not cause the command to be ignored.
assert classify_utterance(
    "Yo, forget about it. Just turn them off.",
    active_conversation=True,
) == DIRECT

assert classify_utterance(
    "You'll forget about it. Just turn them off.",
    active_conversation=True,
) == DIRECT

assert classify_utterance(
    "Okay, whatever. Just turn it off.",
    active_conversation=True,
) == DIRECT

assert classify_utterance(
    "Actually forget that, just set it to 50.",
    active_conversation=True,
) == DIRECT

print("ALL EMBEDDED DEVICE FOLLOW-UP TESTS PASSED")
