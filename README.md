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

- `jarvis.py` - end-to-end Jarvis voice assistant
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

    python jarvis.py

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

## Jarvis Home Hub API

The Jarvis Home Hub API is a separate FastAPI service used by
Home Assistant and other network clients.

Main application:

    jarvis_api.py

Mac mini address:

    10.0.0.250

API port:

    8001

### Manual Startup

From the Mac mini:

    cd /Users/server/apps/anythingllm-wake
    ./.venv/bin/python -m uvicorn jarvis_api:app --host 0.0.0.0 --port 8001

Manual startup is intended for troubleshooting when the automatic
LaunchAgent is stopped. Do not start a second copy while port 8001
is already in use.

### Health Check

On the Mac mini:

    curl http://127.0.0.1:8001/health

From another computer on the home network:

    curl http://10.0.0.250:8001/health

Expected response:

    {"status":"ok","service":"jarvis-home-hub"}

### Automatic Startup

macOS launchd manages two independent services:

Voice assistant:

    com.2021sam.jarvis

Home Hub API:

    com.2021sam.jarvis-api

The API LaunchAgent configuration is located at:

    ~/Library/LaunchAgents/com.2021sam.jarvis-api.plist

Both services use RunAtLoad and KeepAlive.

They start when the server user logs in and restart automatically
if their processes exit.

### Check API Service

    launchctl list | grep jarvis

    launchctl print gui/$(id -u)/com.2021sam.jarvis-api

### Restart API Service

    launchctl kickstart -k gui/$(id -u)/com.2021sam.jarvis-api

Verify afterward:

    curl http://127.0.0.1:8001/health

### API Logs

    tail -50 ~/Library/Logs/jarvis-api.log

    tail -50 ~/Library/Logs/jarvis-api-error.log

### Troubleshooting

If Home Assistant reports Jarvis unavailable:

1. Confirm the Mac mini is reachable at 10.0.0.250.
2. Check http://10.0.0.250:8001/health.
3. Check the API LaunchAgent status.
4. Restart the API service using launchctl kickstart.
5. Review jarvis-api-error.log if the API remains unavailable.

The voice assistant and Home Hub API are separate processes.
Restarting the API does not require restarting Home Assistant.

The API LaunchAgent configuration lives outside this Git repository.
A fresh Mac installation must recreate or restore that plist.


### Restore API LaunchAgent

On a new Mac, after cloning the repository, installing
requirements, and verifying the API manually:

    mkdir -p ~/Library/LaunchAgents
    mkdir -p ~/Library/Logs

    cp launchd/com.2021sam.jarvis-api.plist \
       ~/Library/LaunchAgents/

    plutil -lint \
       ~/Library/LaunchAgents/com.2021sam.jarvis-api.plist

    launchctl bootstrap gui/$(id -u) \
       ~/Library/LaunchAgents/com.2021sam.jarvis-api.plist

    curl http://127.0.0.1:8001/health

The plist currently contains absolute paths for the
server account. Adjust these paths when installing on
another Mac or under a different username.

If the service is already loaded, use launchctl kickstart
instead of bootstrap.
