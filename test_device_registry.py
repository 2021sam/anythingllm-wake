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

device = resolve_device(
    "Turn off the Family Room."
)
assert device is not None
assert device["entity_id"] == "light.wall_dimmer_1"

assert resolve_device("Turn on the kitchen light.") is None

print("ALL DEVICE REGISTRY TESTS PASSED")


from device_registry import get_device_key_by_entity_id

assert (
    get_device_key_by_entity_id("light.wall_dimmer_1")
    == "family_room_light"
)

assert (
    get_device_key_by_entity_id("light.does_not_exist")
    is None
)

print("ENTITY-ID REGISTRY LOOKUP TESTS PASSED")


front_left = get_device("front_left_bedroom_light")
assert front_left is not None
assert front_left["room"] == "Front Left Bedroom"
assert front_left["entity_id"] == "light.wall_dimmer_2"

front_left = find_device("Front Left Bedroom", "Light")
assert front_left is not None
assert front_left["entity_id"] == "light.wall_dimmer_2"

front_left = resolve_device(
    "Turn on the Front Left Bedroom light."
)
assert front_left is not None
assert front_left["entity_id"] == "light.wall_dimmer_2"

front_left = resolve_device(
    "Turn off the left front bedroom light."
)
assert front_left is not None
assert front_left["entity_id"] == "light.wall_dimmer_2"

assert (
    get_device_key_by_entity_id("light.wall_dimmer_2")
    == "front_left_bedroom_light"
)

print("FRONT LEFT BEDROOM REGISTRY TESTS PASSED")
