from __future__ import annotations

import threading
import time


DEFAULT_SUPPRESSION_SECONDS = 5.0


class DeviceActionTracker:
    """
    Track device state changes that Jarvis expects to cause.

    The background monitor can consume these expected changes so they are
    not mistaken for manual/external device activity.
    """

    def __init__(
        self,
        suppression_seconds: float = DEFAULT_SUPPRESSION_SECONDS,
        clock=None,
    ):
        self.suppression_seconds = suppression_seconds
        self.clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._expected = {}

    def expect(
        self,
        entity_id: str,
        state: str,
        brightness: int | None = None,
    ) -> None:
        with self._lock:
            expectation = {
                "state": state,
                "brightness": brightness,
                "expires_at": (
                    self.clock() + self.suppression_seconds
                ),
            }

            self._expected.setdefault(entity_id, []).append(
                expectation
            )

    def clear(self, entity_id: str) -> None:
        with self._lock:
            self._expected.pop(entity_id, None)

    def should_suppress(
        self,
        entity_id: str,
        state: dict,
    ) -> bool:
        """
        Return True when the observed state matches a recent state
        that Jarvis explicitly expected to cause.

        Expected changes are queued per entity so a short Jarvis
        sequence such as ON -> OFF cannot overwrite itself before
        the background monitor observes both changes.
        """
        with self._lock:
            queue = self._expected.get(entity_id)

            if not queue:
                return False

            now = self.clock()

            while queue and now > queue[0]["expires_at"]:
                queue.pop(0)

            if not queue:
                self._expected.pop(entity_id, None)
                return False

            expected = queue[0]

            if state.get("state") != expected["state"]:
                return False

            expected_brightness = expected["brightness"]

            if expected_brightness is not None:
                actual_brightness = state.get("brightness")

                if actual_brightness is None:
                    return False

                if abs(
                    actual_brightness - expected_brightness
                ) > 2:
                    return False

            queue.pop(0)

            if not queue:
                self._expected.pop(entity_id, None)

            return True


ACTION_TRACKER = DeviceActionTracker()


def expect_device_change(
    entity_id: str,
    state: str,
    brightness: int | None = None,
) -> None:
    ACTION_TRACKER.expect(
        entity_id,
        state,
        brightness,
    )


def should_suppress_device_change(
    entity_id: str,
    state: dict,
) -> bool:
    return ACTION_TRACKER.should_suppress(
        entity_id,
        state,
    )
