from device_monitor import (
    DeviceMonitor,
    detect_state_changes,
    normalized_device_state,
)


entity = {
    "entity_id": "light.wall_dimmer_1",
    "state": "on",
    "attributes": {
        "brightness": 191,
        "friendly_name": "Wall Dimmer 1",
    },
}

assert normalized_device_state(entity) == {
    "state": "on",
    "brightness": 191,
}


# No change.
previous = {
    "light.wall_dimmer_1": {
        "state": "off",
        "brightness": None,
    },
}

current = {
    "light.wall_dimmer_1": {
        "state": "off",
        "brightness": None,
    },
}

assert detect_state_changes(previous, current) == []


# Manual off -> on at 75%.
current = {
    "light.wall_dimmer_1": {
        "state": "on",
        "brightness": 191,
    },
}

changes = detect_state_changes(previous, current)

assert len(changes) == 1
assert changes[0]["entity_id"] == "light.wall_dimmer_1"
assert changes[0]["device"]["room"] == "Family Room"
assert changes[0]["before"]["state"] == "off"
assert changes[0]["after"] == {
    "state": "on",
    "brightness": 191,
}


# Brightness-only changes count too.
previous = current

current = {
    "light.wall_dimmer_1": {
        "state": "on",
        "brightness": 102,
    },
}

changes = detect_state_changes(previous, current)

assert len(changes) == 1
assert changes[0]["before"]["brightness"] == 191
assert changes[0]["after"]["brightness"] == 102


# A newly observed entity is baseline, not an event.
assert detect_state_changes(
    {},
    {
        "light.wall_dimmer_1": {
            "state": "on",
            "brightness": 191,
        },
    },
) == []

print("ALL DEVICE MONITOR TESTS PASSED")


# Home Assistant outage behavior:
# - log outage once
# - preserve last known baseline
# - recover automatically
# - do not create false startup events
class RecoveringClient:
    def __init__(self):
        self.fail = False
        self.family_state = "off"

    def get_state(self, entity_id):
        if self.fail:
            raise ConnectionError("Home Assistant unavailable")

        if entity_id == "light.wall_dimmer_1":
            return {
                "state": self.family_state,
                "attributes": {},
            }

        return {
            "state": "off",
            "attributes": {},
        }


recovering_client = RecoveringClient()
recovery_changes = []

recovery_monitor = DeviceMonitor(
    callback=recovery_changes.append,
    client=recovering_client,
)

assert recovery_monitor.initialize() is True
baseline_before_outage = dict(recovery_monitor._previous)

recovering_client.fail = True

assert recovery_monitor.poll_once() == []
assert recovery_monitor.poll_once() == []
assert recovery_monitor._previous == baseline_before_outage
assert recovery_monitor._ha_available is False

recovering_client.fail = False

assert recovery_monitor.poll_once() == []
assert recovery_monitor._ha_available is True
assert recovery_changes == []

# A real state change after recovery must still be detected.
recovering_client.family_state = "on"

changes = recovery_monitor.poll_once()

assert len(changes) == 1
assert changes[0]["entity_id"] == "light.wall_dimmer_1"
assert changes[0]["before"]["state"] == "off"
assert changes[0]["after"]["state"] == "on"

print("DEVICE MONITOR OUTAGE/RECOVERY TEST PASSED")
