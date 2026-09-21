from device_action_tracker import DeviceActionTracker


now = [100.0]

tracker = DeviceActionTracker(
    suppression_seconds=5.0,
    clock=lambda: now[0],
)

entity_id = "light.wall_dimmer_1"


# Untracked manual action must not be suppressed.
assert tracker.should_suppress(
    entity_id,
    {
        "state": "on",
        "brightness": 191,
    },
) is False


# Jarvis expects an ON event.
tracker.expect(entity_id, "on")

assert tracker.should_suppress(
    entity_id,
    {
        "state": "on",
        "brightness": 191,
    },
) is True


# Expectations are consumed exactly once.
assert tracker.should_suppress(
    entity_id,
    {
        "state": "on",
        "brightness": 191,
    },
) is False


# Wrong state must not be suppressed.
tracker.expect(entity_id, "off")

assert tracker.should_suppress(
    entity_id,
    {
        "state": "on",
        "brightness": 191,
    },
) is False


# Correct state still matches the outstanding expectation.
assert tracker.should_suppress(
    entity_id,
    {
        "state": "off",
        "brightness": None,
    },
) is True


# Brightness requests require a matching brightness.
tracker.expect(
    entity_id,
    "on",
    brightness=191,
)

assert tracker.should_suppress(
    entity_id,
    {
        "state": "on",
        "brightness": 100,
    },
) is False

assert tracker.should_suppress(
    entity_id,
    {
        "state": "on",
        "brightness": 192,
    },
) is True


# Expired expectations must not suppress later manual activity.
tracker.expect(entity_id, "on")
now[0] += 6.0

assert tracker.should_suppress(
    entity_id,
    {
        "state": "on",
        "brightness": 255,
    },
) is False


print("ALL DEVICE ACTION TRACKER TESTS PASSED")
