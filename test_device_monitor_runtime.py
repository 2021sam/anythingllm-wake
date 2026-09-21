from unittest.mock import patch

import device_monitor_runtime


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
        # Deliberately wrong/stale HA brightness.
        # Runtime must not announce it.
        "brightness": 5,
    },
}


def run_mode(mode, announcement):
    spoken = []

    with patch.object(
        device_monitor_runtime,
        "get_training_mode",
        return_value=mode,
    ), patch.object(
        device_monitor_runtime,
        "handle_device_change",
        return_value=announcement,
    ):
        result = device_monitor_runtime.announce_device_change(
            change,
            speaker=spoken.append,
        )

    return result, spoken


result, spoken = run_mode(
    "short",
    "Family Room light is on.",
)

assert result == "Family Room light is on."
assert spoken == [
    "Family Room light is on.",
]


result, spoken = run_mode(
    "normal",
    (
        "Family Room light is on. "
        "You can say, 'Turn off the Family Room light.'"
    ),
)

assert result == (
    "Family Room light is on. "
    "You can say, 'Turn off the Family Room light.'"
)

assert spoken == [
    (
        "Family Room light is on. "
        "You can say, 'Turn off the Family Room light.'"
    ),
]


result, spoken = run_mode(
    "long",
    (
        "Family Room light is on. "
        "You can say, 'Turn off the Family Room light.' "
        "You can also say, 'Set the Family Room light "
        "to 50%,' or another brightness percentage."
    ),
)

assert result == (
    "Family Room light is on. "
    "You can say, 'Turn off the Family Room light.' "
    "You can also say, 'Set the Family Room light "
    "to 50%,' or another brightness percentage."
)

assert spoken == [
    result,
]


result, spoken = run_mode(
    "off",
    None,
)

assert result is None
assert spoken == []


class FakeThread:
    def __init__(self, target, name, daemon):
        self.target = target
        self.name = name
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True


with patch.object(
    device_monitor_runtime.threading,
    "Thread",
    FakeThread,
):
    thread = (
        device_monitor_runtime.start_device_monitor_thread()
    )

assert thread.started is True
assert thread.daemon is True
assert thread.name == "jarvis-device-monitor"
assert thread.target is device_monitor_runtime.run_device_monitor


print("ALL DEVICE MONITOR RUNTIME TESTS PASSED")
print("PHYSICAL BRIGHTNESS IS NOT ANNOUNCED")
