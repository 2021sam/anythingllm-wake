from device_discovery import (
    active_candidate_announcement,
    flick_light_candidate,
    get_active_light_candidates,
)


class FakeHA:
    def __init__(self):
        self.calls = []

    def get_lights(self):
        return [
            {
                "entity_id": "light.wall_dimmer_2",
                "state": "off",
                "attributes": {
                    "friendly_name": "Wall Dimmer - 2",
                    "supported_color_modes": ["brightness"],
                },
            },
            {
                "entity_id": "light.wall_dimmer_1",
                "state": "on",
                "attributes": {
                    "friendly_name": "Wall Dimmer - 1",
                    "supported_color_modes": ["brightness"],
                    "brightness": 25,
                },
            },
            {
                "entity_id": "light.dead_light",
                "state": "unavailable",
                "attributes": {
                    "friendly_name": "Dead Light",
                },
            },
            {
                "entity_id": "light.other_light",
                "state": "off",
                "attributes": {
                    "friendly_name": "Other Light",
                },
            },
        ]

    def turn_on(self, entity_id):
        self.calls.append(("on", entity_id))

    def turn_off(self, entity_id):
        self.calls.append(("off", entity_id))

    def call_service(self, domain, service, data):
        self.calls.append((domain, service, data))


fake = FakeHA()
candidates = get_active_light_candidates(fake)

assert [c["entity_id"] for c in candidates] == [
    "light.wall_dimmer_1",
    "light.wall_dimmer_2",
]

known = candidates[0]
front_left = candidates[1]

assert known["registered_name"] == "Family Room light"
assert (
    active_candidate_announcement(known)
    == "Testing the Family Room dimmer."
)

assert (
    front_left["registered_name"]
    == "Front Left Bedroom light"
)
assert (
    active_candidate_announcement(front_left)
    == "Testing the Front Left Bedroom dimmer."
)

fake.calls.clear()
flick_light_candidate(known, fake, pause_seconds=0)
assert fake.calls == [
    ("off", "light.wall_dimmer_1"),
    (
        "light",
        "turn_on",
        {
            "entity_id": "light.wall_dimmer_1",
            "brightness": 25,
        },
    ),
]

fake.calls.clear()
flick_light_candidate(front_left, fake, pause_seconds=0)
assert fake.calls == [
    ("on", "light.wall_dimmer_2"),
    ("off", "light.wall_dimmer_2"),
]

print("ALL ACTIVE LIGHT DISCOVERY TESTS PASSED")

from device_discovery import (
    is_active_light_discovery_request,
    parse_active_discovery_confirmation,
)

assert is_active_light_discovery_request(
    "Jarvis, identify the dimmers."
)
assert is_active_light_discovery_request(
    "Can you cycle through the lights?"
)
assert is_active_light_discovery_request(
    "Test the dimmers."
)
assert is_active_light_discovery_request(
    "Which light is which?"
)

assert not is_active_light_discovery_request(
    "Turn on the Family Room light."
)
assert not is_active_light_discovery_request(
    "Dim the Family Room light to 10%."
)
assert not is_active_light_discovery_request(
    "What's the weather?"
)

for phrase in (
    "Yes",
    "Yeah",
    "Yep",
    "That one",
    "I saw it",
    "It flicked",
    "Yes, the light flicked.",
    "Yes, the lights are flicking.",
):
    assert parse_active_discovery_confirmation(phrase) is True

for phrase in (
    "No",
    "Nope",
    "Not that one",
    "I didn't see it",
    "Nothing happened",
):
    assert parse_active_discovery_confirmation(phrase) is False

for phrase in (
    "Maybe",
    "I don't know",
    "What was that?",
):
    assert parse_active_discovery_confirmation(phrase) is None

print("ALL ACTIVE DISCOVERY LANGUAGE TESTS PASSED")
