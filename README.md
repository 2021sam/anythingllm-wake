# AnythingLLM Wake

Local AI home voice assistant running on macOS with openWakeWord, faster-whisper, AnythingLLM, and Home Assistant.

## Working Voice Pipeline

Hey Jarvis
→ openWakeWord wake detection
→ Silero VAD speech endpoint detection
→ faster-whisper speech-to-text
→ AnythingLLM Developer API
→ workspace RAG
→ local Llama model
→ Home Assistant
→ audio-target helper
→ selected home speaker(s)

After answering, Jarvis automatically returns to wake-word listening.

## Project Files

- `test_wake.py` - end-to-end Jarvis voice assistant
- `anythingllm_client.py` - AnythingLLM Developer API client
- `homeassistant_tts.py` - Home Assistant TTS and speaker routing
- `download_models.py` - downloads required openWakeWord models
- `requirements.txt` - main Python environment dependencies
- `test_stt.py` - standalone speech-to-text test
- `speak.py` - optional Kokoro local TTS
- `test_tts.py` - optional Kokoro TTS test

## Main Python Environment

The main Jarvis runtime uses Python 3.14.

Create the environment:

    python3.14 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt

Download the required openWakeWord models:

    python download_models.py

This installs the Hey Jarvis wake model and the feature/VAD models required by openWakeWord.

## Optional Kokoro TTS Environment

Kokoro/MLX uses a separate Python 3.12 environment:

    .venv-tts/

Kokoro was tested successfully and remains available for optional local TTS. The current home-speaker pipeline uses Home Assistant TTS instead.

## Private Files

Secrets and private configuration are stored locally and must never be committed to Git.

AnythingLLM API key:

    .anythingllm_api_key

Home Assistant URL:

    .homeassistant_url

Home Assistant long-lived access token:

    .homeassistant_token

Restrict private files to the local user:

    chmod 600 .anythingllm_api_key
    chmod 600 .homeassistant_url
    chmod 600 .homeassistant_token

These files are excluded by `.gitignore`.

Never put actual API keys, tokens, passwords, or private credentials in source code or this README.

## AnythingLLM

AnythingLLM runs locally at:

    http://localhost:3001

Jarvis uses workspace:

    my-workspace

Workspace documents and RAG data are managed by AnythingLLM and are not stored in this repository.

## Home Assistant Speaker Routing

Jarvis does not hard-code a physical speaker.

Speaker selection uses the existing Home Assistant helper:

    input_select.guard_1_audio_target

Routing behavior:

- `None` - no spoken output
- `All` - speak through both configured amplifiers
- a specific `media_player` - speak through that selected target

TTS uses:

    tts.google_translate_en_com

This reuses the same speaker-selection approach used by the existing Guardian automations.

## Start Jarvis

Activate the environment:

    cd /Users/server/apps/anythingllm-wake
    source .venv/bin/activate

Start Jarvis:

    python test_wake.py

Expected startup:

    Loading Whisper model...
    Listening for: HEY JARVIS
    Press Ctrl+C to stop.

Say:

    Hey Jarvis

Then ask a question normally. Silero VAD detects when the question begins and ends automatically.

## Security

Never commit:

- API keys
- Home Assistant tokens
- passwords
- `.env` secrets
- virtual environments
- generated audio recordings

Before committing changes:

    git status
    git diff --cached
