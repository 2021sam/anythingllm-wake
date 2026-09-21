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
            self._expected[entity_id] = {
                "state": state,
                "brightness": brightness,
                "expires_at": (
                    self.clock() + self.suppression_seconds
                ),
            }

    def clear(self, entity_id: str) -> None:
        with self._lock:
            self._expected.pop(entity_id, None)

    def should_suppress(
        self,
        entity_id: str,
        state: dict,
    ) -> bool:
        """
        Return True only when the observed state matches a recent state
        that Jarvis explicitly expected to cause.

        Matching consumes the expectation.
        """
        with self._lock:
            expected = self._expected.get(entity_id)

            if expected is None:
                return False

            if self.clock() > expected["expires_at"]:
                self._expected.pop(entity_id, None)
                return False

            if state.get("state") != expected["state"]:
                return False

            expected_brightness = expected["brightness"]

            if expected_brightness is not None:
                actual_brightness = state.get("brightness")

                if actual_brightness is None:
                    return False

                # HA/device rounding may differ slightly from the requested
                # 0-255 value, so allow a very small hardware rounding delta.
                if abs(actual_brightness - expected_brightness) > 2:
                    return False

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
