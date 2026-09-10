from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent

HA_URL_FILE = BASE_DIR / ".homeassistant_url"
HA_TOKEN_FILE = BASE_DIR / ".homeassistant_token"

AUDIO_HELPER = "input_select.guard_1_audio_target"
TTS_ENTITY = "tts.google_translate_en_com"


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
        targets = audio_choice

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


if __name__ == "__main__":
    speak_home_assistant("Jarvis Home Assistant module test.")
