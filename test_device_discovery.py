from device_discovery import is_physical_light_discovery_request


assert is_physical_light_discovery_request(
    "How do I turn this light on?"
)

assert is_physical_light_discovery_request(
    "How do I turn the light off?"
)

assert is_physical_light_discovery_request(
    "Which switch controls this light?"
)

assert is_physical_light_discovery_request(
    "What switch controls the light?"
)

assert not is_physical_light_discovery_request(
    "Turn on the Family Room light."
)

assert not is_physical_light_discovery_request(
    "What's the weather?"
)

print("ALL DEVICE DISCOVERY DETECTOR TESTS PASSED")
