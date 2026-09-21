from __future__ import annotations

import threading

from device_event_handler import handle_device_change
from device_monitor import DeviceMonitor
from device_training import get_training_mode
from homeassistant_tts import speak_home_assistant


_tts_lock = threading.Lock()


def announce_device_change(
    change: dict,
    speaker=speak_home_assistant,
    client=None,
) -> str | None:
    """
    Process one monitored device change.

    Physical dimmer brightness is intentionally not announced here.
    Some Zigbee dimmers can change physically without Home Assistant
    immediately reflecting the correct brightness value.

    Training Mode therefore teaches only from reliable on/off state.
    """
    mode = get_training_mode()

    announcement = handle_device_change(
        change,
        training_mode=mode,
    )

    if announcement is None:
        return None

    print(
        f"[TRAINING MODE] Speaking: {announcement}"
    )

    with _tts_lock:
        speaker(announcement)

    return announcement


def run_device_monitor() -> None:
    print("[DEVICE MONITOR] Starting...")

    try:
        monitor = DeviceMonitor(
            callback=announce_device_change,
        )
        monitor.run_forever()

    except Exception as exc:
        print(
            f"[DEVICE MONITOR ERROR] "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )


def start_device_monitor_thread() -> threading.Thread:
    thread = threading.Thread(
        target=run_device_monitor,
        name="jarvis-device-monitor",
        daemon=True,
    )
    thread.start()
    return thread
