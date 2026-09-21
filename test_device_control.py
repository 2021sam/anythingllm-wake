from unittest.mock import patch

from device_control import answer_device_command


class FakeHomeAssistantClient:
    calls = []

    def turn_on(self, entity_id):
        self.calls.append(("on", entity_id))

    def turn_off(self, entity_id):
        self.calls.append(("off", entity_id))


with patch(
    "device_control.HomeAssistantClient",
    FakeHomeAssistantClient,
):
    FakeHomeAssistantClient.calls = []

    answer = answer_device_command(
        "Turn on the Family Room light."
    )

    assert answer == "Turning on the Family Room light."
    assert FakeHomeAssistantClient.calls == [
        ("on", "light.wall_dimmer_1")
    ]

    FakeHomeAssistantClient.calls = []

    answer = answer_device_command(
        "Turn off the Family Room light."
    )

    assert answer == "Turning off the Family Room light."
    assert FakeHomeAssistantClient.calls == [
        ("off", "light.wall_dimmer_1")
    ]

    FakeHomeAssistantClient.calls = []

    answer = answer_device_command(
        "What's the temperature?"
    )

    assert answer is None
    assert FakeHomeAssistantClient.calls == []

print("ALL DEVICE CONTROL TESTS PASSED")
