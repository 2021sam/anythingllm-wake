from pathlib import Path
import time
import requests

BASE_DIR = Path(__file__).resolve().parent

HA_URL_FILE = BASE_DIR / ".homeassistant_url"
HA_TOKEN_FILE = BASE_DIR / ".homeassistant_token"

AUDIO_HELPER = "input_select.guard_1_audio_target"
TTS_ENTITY = "tts.google_translate_en_com"

PLAYBACK_POLL_SECONDS = 0.20
PLAYBACK_START_TIMEOUT_SECONDS = 3.0
PLAYBACK_FINISH_TIMEOUT_SECONDS = 60.0


def _get_media_state(
    ha_url: str,
    headers: dict,
    entity_id: str,
) -> str | None:
    response = requests.get(
        f"{ha_url}/api/states/{entity_id}",
        headers=headers,
        timeout=10,
    )

    if not response.ok:
        return None

    return response.json().get("state")


def _wait_for_tts_playback(
    ha_url: str,
    headers: dict,
    targets: list[str],
) -> None:
    start = time.monotonic()
    saw_playing = False

    # First wait briefly for at least one target to enter
    # the "playing" state.
    while (
        time.monotonic() - start
        < PLAYBACK_START_TIMEOUT_SECONDS
    ):
        states = [
            _get_media_state(
                ha_url,
                headers,
                entity_id,
            )
            for entity_id in targets
        ]

        if any(state == "playing" for state in states):
            saw_playing = True
            print(
                "[TIMING] "
                f"tts_playback_detected="
                f"{time.monotonic() - start:.3f}s"
            )
            break

        time.sleep(PLAYBACK_POLL_SECONDS)

    # If HA never reported playback, do not hang.
    if not saw_playing:
        return

    finish_start = time.monotonic()

    # Wait until all selected targets are no longer playing.
    while (
        time.monotonic() - finish_start
        < PLAYBACK_FINISH_TIMEOUT_SECONDS
    ):
        states = [
            _get_media_state(
                ha_url,
                headers,
                entity_id,
            )
            for entity_id in targets
        ]

        if not any(state == "playing" for state in states):
            print(
                "[TIMING] "
                f"tts_playback_duration="
                f"{time.monotonic() - finish_start:.3f}s"
            )
            return

        time.sleep(PLAYBACK_POLL_SECONDS)


def speak_home_assistant(message: str) -> None:
    ha_url = HA_URL_FILE.read_text().strip()
    token = HA_TOKEN_FILE.read_text().strip()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.get(
        f"{ha_url}/api/states/{AUDIO_HELPER}",
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()

    audio_choice = response.json()["state"]

    if audio_choice.lower() in (
        "none",
        "off",
        "unknown",
        "unavailable",
        "",
    ):
        return

    if audio_choice.lower() == "all" or audio_choice == "*":
        targets = [
            "media_player.amp_1",
            "media_player.amp_2",
        ]
    else:
        targets = [audio_choice]

    timing_tts_request_start = time.monotonic()

    response = requests.post(
        f"{ha_url}/api/services/tts/speak",
        headers=headers,
        json={
            "entity_id": TTS_ENTITY,
            "media_player_entity_id": targets,
            "message": message,
        },
        timeout=20,
    )

    response.raise_for_status()

    timing_tts_request_done = time.monotonic()

    print(
        "[TIMING] "
        f"tts_ha_request="
        f"{timing_tts_request_done - timing_tts_request_start:.3f}s"
    )

    _wait_for_tts_playback(
        ha_url,
        headers,
        targets,
    )


if __name__ == "__main__":
    speak_home_assistant(
        "Jarvis Home Assistant module test."
    )
