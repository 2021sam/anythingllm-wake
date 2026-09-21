from device_registry import (
    find_device,
    get_device,
    resolve_device,
)


device = get_device("family_room_light")
assert device is not None
assert device["room"] == "Family Room"
assert device["entity_id"] == "light.wall_dimmer_1"

device = find_device("Family Room", "Light")
assert device is not None
assert device["entity_id"] == "light.wall_dimmer_1"

device = find_device("family room", "light")
assert device is not None
assert device["entity_id"] == "light.wall_dimmer_1"

device = resolve_device("Turn off the Family Room light.")
assert device is not None
assert device["entity_id"] == "light.wall_dimmer_1"

device = resolve_device("Turn the family room lights on.")
assert device is not None
assert device["entity_id"] == "light.wall_dimmer_1"

assert resolve_device("Turn on the kitchen light.") is None

print("ALL DEVICE REGISTRY TESTS PASSED")
