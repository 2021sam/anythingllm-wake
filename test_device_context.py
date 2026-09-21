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
