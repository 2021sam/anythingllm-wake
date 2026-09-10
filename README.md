# AnythingLLM Wake

Local AI voice assistant using openWakeWord, faster-whisper, AnythingLLM, Kokoro TTS, and Home Assistant.

## Voice Pipeline

Hey Jarvis
→ openWakeWord
→ microphone
→ faster-whisper speech-to-text
→ AnythingLLM Developer API
→ workspace RAG
→ local Llama model
→ Kokoro TTS
→ audio output

The next stage will route responses through Home Assistant to the home's media-player helper.

## Project Files

- `test_wake.py` - end-to-end wake word and voice pipeline
- `anythingllm_client.py` - AnythingLLM API client
- `speak.py` - Kokoro text-to-speech
- `test_stt.py` - speech-to-text test
- `test_tts.py` - text-to-speech test

## Private Files

Secrets are stored locally and must never be committed to Git.

### AnythingLLM API Key

The AnythingLLM API key is stored in:

    .anythingllm_api_key

The file is protected by `.gitignore`.

On a new installation, create the file locally and restrict its permissions:

    printf '%s\n' 'YOUR_API_KEY' > .anythingllm_api_key
    chmod 600 .anythingllm_api_key

Never put the actual API key in source code or this README.

Home Assistant credentials will follow the same pattern: private credentials stay in ignored local files and are never committed.

## Python Environments

Two local virtual environments are currently used:

- `.venv/` - wake word, Whisper, and AnythingLLM client
- `.venv-tts/` - Python 3.12 environment for Kokoro/MLX TTS

Both are excluded from Git.

## AnythingLLM

AnythingLLM currently runs locally at:

    http://localhost:3001

The assistant uses workspace:

    my-workspace

Workspace documents and RAG data are managed by AnythingLLM and are not stored in this repository.

## Security

Never commit API keys, Home Assistant tokens, passwords, `.env` secrets, virtual environments, or generated recordings.

Before committing, verify changes with:

    git status
    git diff --cached
