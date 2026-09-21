from unittest.mock import patch

import device_event_handler


change = {
    "entity_id": "light.wall_dimmer_1",
    "device": {
        "room": "Family Room",
        "name": "Light",
        "domain": "light",
        "entity_id": "light.wall_dimmer_1",
    },
    "before": {
        "state": "off",
        "brightness": None,
    },
    "after": {
        "state": "on",
        "brightness": 191,
    },
}


# Training Mode OFF: monitor sees the change but says nothing.
with patch.object(
    device_event_handler,
    "should_suppress_device_change",
    return_value=False,
):
    assert device_event_handler.handle_device_change(
        change,
        training_enabled=False,
    ) is None


# Training Mode ON: manual/external change teaches a command.
with patch.object(
    device_event_handler,
    "should_suppress_device_change",
    return_value=False,
):
    announcement = device_event_handler.handle_device_change(
        change,
        training_enabled=True,
    )

assert announcement == (
    "Family Room light is on. "
    "You can say, 'Turn off the Family Room light.'"
)


# Jarvis-originated change is suppressed even when Training Mode is ON.
with patch.object(
    device_event_handler,
    "should_suppress_device_change",
    return_value=True,
):
    assert device_event_handler.handle_device_change(
        change,
        training_enabled=True,
    ) is None


print("ALL DEVICE EVENT HANDLER TESTS PASSED")
