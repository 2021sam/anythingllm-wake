"""
Jarvis room/device registry.

This layer gives Home Assistant entities human-friendly property names.
Home Assistant remains authoritative for actual device state and control.
"""

DEVICES = {
    "family_room_light": {
        "room": "Family Room",
        "name": "Light",
        "domain": "light",
        "entity_id": "light.wall_dimmer_1",
        "aliases": [
            "family room light",
            "family room lights",
            "family room",
        ],
    },
    "front_left_bedroom_light": {
        "room": "Front Left Bedroom",
        "name": "Light",
        "domain": "light",
        "entity_id": "light.wall_dimmer_2",
        "aliases": [
            "front left bedroom light",
            "front left bedroom lights",
            "front left bedroom",
            "left front bedroom light",
            "left front bedroom lights",
            "left front bedroom",
        ],
    },
}


def get_device(device_key: str) -> dict | None:
    return DEVICES.get(device_key)


def get_device_key(device: dict) -> str | None:
    """Return the registry key for a device object."""
    for device_key, registered_device in DEVICES.items():
        if registered_device is device:
            return device_key

    return None


def get_device_key_by_entity_id(
    entity_id: str,
) -> str | None:
    """Return the registry key for a Home Assistant entity ID."""
    for device_key, device in DEVICES.items():
        if device["entity_id"] == entity_id:
            return device_key

    return None


def find_device(room: str, name: str = "Light") -> dict | None:
    room_lower = room.strip().lower()
    name_lower = name.strip().lower()

    for device in DEVICES.values():
        if (
            device["room"].lower() == room_lower
            and device["name"].lower() == name_lower
        ):
            return device

    return None


def resolve_device(text: str) -> dict | None:
    """Resolve natural human wording to a registered device."""
    normalized = text.strip().lower()

    for device in DEVICES.values():
        for alias in device.get("aliases", []):
            if alias.lower() in normalized:
                return device

    return None
