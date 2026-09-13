import sounddevice as sd
import numpy as np
import wave
import time
from collections import deque

from openwakeword.model import Model
from openwakeword.vad import VAD
from faster_whisper import WhisperModel

from anythingllm_client import ask_anythingllm
from homeassistant_tts import speak_home_assistant
from weather_service import (
    answer_climate_question,
    answer_weather_question,
)


SAMPLE_RATE = 16000

# Wake-word model works with 1280-sample chunks.
WAKE_CHUNK = 1280

# Silero VAD works best with 480-sample chunks.
VAD_CHUNK = 480

DEVICE = 1
WAKE_THRESHOLD = 0.5

# These values came from our microphone/VAD test.
START_THRESHOLD = 0.003
CONTINUE_THRESHOLD = 0.002
SILENCE_SECONDS = 1.2
MAX_RECORD_SECONDS = 15
PRE_ROLL_SECONDS = 0.4

# Diagnostic interval while testing headset disconnect/reconnect.
AUDIO_HEALTH_INTERVAL_SECONDS = 60
EXPECTED_INPUT_DEVICE = "Arctis 7P+"

# Reopen the microphone if it delivers continuous digital silence.
ZERO_AUDIO_RECONNECT_SECONDS = 300  # 5 minutes
AUDIO_RECONNECT_RETRY_SECONDS = 5

# After Jarvis answers, remain available for natural follow-up
# questions without requiring the wake word again.
CONVERSATION_TIMEOUT_SECONDS = 30

# "Hey, chill" temporarily suspends conversation mode.
DEFAULT_CHILL_SECONDS = 5 * 60

WAV_FILE = "wake_question.wav"


wake_model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx",
)

vad = VAD()

print("Loading Whisper model...")

whisper_model = WhisperModel(
    "base.en",
    device="cpu",
    compute_type="int8",
)

print("Listening for: HEY JARVIS")
print("Press Ctrl+C to stop.")


def record_question():
    frames = []
    pre_roll_chunks = max(
        1,
        int(PRE_ROLL_SECONDS * SAMPLE_RATE / VAD_CHUNK),
    )
    pre_roll = deque(maxlen=pre_roll_chunks)
    speech_started = False
    last_speech_time = None
    record_start_time = None

    print("Waiting for your question...")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=VAD_CHUNK,
        device=DEVICE,
    ) as stream:

        while True:
            audio, overflowed = stream.read(VAD_CHUNK)
            audio = np.squeeze(audio)

            score = float(
                vad.predict(
                    audio,
                    frame_size=VAD_CHUNK,
                )
            )

            if not speech_started:
                pre_roll.append(audio.copy())

                if score >= START_THRESHOLD:
                    speech_started = True
                    record_start_time = time.monotonic()
                    last_speech_time = record_start_time

                    frames.extend(pre_roll)
                    pre_roll.clear()

                    print(
                        f"Speech detected. "
                        f"VAD={score:.4f}"
                    )

            else:
                frames.append(audio.copy())

                now = time.monotonic()

                if score >= CONTINUE_THRESHOLD:
                    last_speech_time = now

                if (
                    now - last_speech_time
                    >= SILENCE_SECONDS
                ):
                    print("Question complete.")
                    break

                if (
                    now - record_start_time
                    >= MAX_RECORD_SECONDS
                ):
                    print(
                        "Maximum recording time reached."
                    )
                    break

    if not frames:
        return False

    recorded = np.concatenate(frames).astype(
        np.int16
    )

    with wave.open(WAV_FILE, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(recorded.tobytes())

    duration = len(recorded) / SAMPLE_RATE

    print(f"Recorded {duration:.2f} seconds.")

    return True


def normalize_command(text):
    import re

    # Remove punctuation and collapse repeated whitespace.
    normalized = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(normalized.split())


def parse_chill_seconds(text):
    """
    Examples:
      Chill.                         -> 5 minutes
      Chill out.                     -> 5 minutes
      Go to sleep.                   -> 5 minutes
      Hey, chill.                    -> 5 minutes
      Hey, chill out.                -> 5 minutes
      Hey, go to sleep.              -> 5 minutes
      Chill for 10 minutes.          -> 10 minutes
      Chill out for an hour.         -> 1 hour
      Go to sleep for 30 seconds.    -> 30 seconds
    """
    import re

    normalized = normalize_command(text)

    match = re.fullmatch(
        r"(?:hey\s+)?"
        r"(?:chill(?:\s+out)?|go\s+to\s+sleep)"
        r"(?:\s+for\s+"
        r"(\d+|a|an|one)\s*"
        r"(second|seconds|minute|minutes|hour|hours)"
        r")?",
        normalized,
    )

    if not match:
        return None

    amount_text, unit = match.groups()

    if amount_text is None:
        return DEFAULT_CHILL_SECONDS

    if amount_text in {"a", "an", "one"}:
        amount = 1
    else:
        amount = int(amount_text)

    if unit.startswith("second"):
        return amount

    if unit.startswith("hour"):
        return amount * 60 * 60

    return amount * 60


def format_chill_duration(seconds):
    if seconds % 3600 == 0:
        hours = seconds // 3600
        return (
            "1 hour"
            if hours == 1
            else f"{hours} hours"
        )

    if seconds % 60 == 0:
        minutes = seconds // 60
        return (
            "1 minute"
            if minutes == 1
            else f"{minutes} minutes"
        )

    return (
        "1 second"
        if seconds == 1
        else f"{seconds} seconds"
    )


def find_input_device():
    devices = sd.query_devices()

    for index, device in enumerate(devices):
        if (
            EXPECTED_INPUT_DEVICE.lower()
            in device["name"].lower()
            and device["max_input_channels"] > 0
        ):
            return index

    raise RuntimeError(
        f"Input device not found: {EXPECTED_INPUT_DEVICE}"
    )


shutdown_requested = False

while not shutdown_requested:
    reconnect_requested = False
    reconnect_is_error = False

    try:
        DEVICE = find_input_device()

        print(
            f"\nOpening microphone: "
            f"{DEVICE}: {EXPECTED_INPUT_DEVICE}",
            flush=True,
        )

        zero_audio_since = None
        last_audio_health = time.monotonic()
        ignore_audio_until = time.monotonic() + 0.5

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=WAKE_CHUNK,
            device=DEVICE,
        ) as stream:

            while True:
                try:
                    audio, overflowed = stream.read(WAKE_CHUNK)
                except Exception as exc:
                    print(
                        f"\nAUDIO READ ERROR: "
                        f"{type(exc).__name__}: {exc}",
                        flush=True,
                    )
                    reconnect_requested = True
                    reconnect_is_error = True
                    break

                now = time.monotonic()

                if (
                    now - last_audio_health
                    >= AUDIO_HEALTH_INTERVAL_SECONDS
                ):
                    last_audio_health = now

                    try:
                        devices = sd.query_devices()

                        arctis_inputs = [
                            (index, device["name"])
                            for index, device in enumerate(devices)
                            if (
                                EXPECTED_INPUT_DEVICE.lower()
                                in device["name"].lower()
                                and device["max_input_channels"] > 0
                            )
                        ]

                        try:
                            selected_device = sd.query_devices(
                                DEVICE,
                                "input",
                            )
                            selected_name = selected_device["name"]
                        except Exception as exc:
                            selected_name = (
                                f"ERROR: {type(exc).__name__}: {exc}"
                            )

                        print(
                            f"\n[AUDIO HEALTH] "
                            f"stream_active={stream.active} "
                            f"stream_stopped={stream.stopped} "
                            f"selected_device={DEVICE}: "
                            f"{selected_name} "
                            f"arctis_inputs={arctis_inputs}",
                            flush=True,
                        )

                    except Exception as exc:
                        print(
                            f"\n[AUDIO HEALTH ERROR] "
                            f"{type(exc).__name__}: {exc}",
                            flush=True,
                        )

                if overflowed:
                    print(
                        "\n[AUDIO WARNING] Input overflow detected.",
                        flush=True,
                    )

                audio = np.squeeze(audio)

                if now < ignore_audio_until:
                    continue

                if np.all(audio == 0):
                    if zero_audio_since is None:
                        zero_audio_since = now

                    zero_seconds = now - zero_audio_since

                    if zero_seconds >= ZERO_AUDIO_RECONNECT_SECONDS:
                        print(
                            f"\n[AUDIO RECONNECT] "
                            f"Received zero audio for "
                            f"{zero_seconds:.0f} seconds. "
                            f"Reopening microphone.",
                            flush=True,
                        )
                        reconnect_requested = True
                        reconnect_is_error = True
                        break
                else:
                    zero_audio_since = None

                scores = wake_model.predict(audio)

                detected = False

                for name, score in scores.items():
                    if score >= WAKE_THRESHOLD:
                        print(
                            f"\nWAKE WORD DETECTED: "
                            f"{name} score={score:.2f}"
                        )
                        detected = True
                        break

                if not detected:
                    continue

                stream.stop()

                speak_home_assistant("Yes.")
                time.sleep(1.0)

                try:
                    if record_question():
                        print("Transcribing...")

                        segments, info = whisper_model.transcribe(
                            WAV_FILE,
                            language="en",
                        )

                        text = " ".join(
                            segment.text.strip()
                            for segment in segments
                        ).strip()

                        print(f"You said: {text}")

                        normalized_text = normalize_command(text)

                        if normalized_text in {
                            "exit",
                            "quit",
                            "shutdown",
                            "stop listening",
                            "go offline",
                        }:
                            print("Voice exit command received.")
                            speak_home_assistant("Goodbye.")
                            shutdown_requested = True
                            break

                        chill_seconds = parse_chill_seconds(text)

                        if chill_seconds is not None:
                            duration_text = format_chill_duration(
                                chill_seconds
                            )

                            print(
                                f"Chill command received. "
                                f"Sleeping for {duration_text}."
                            )

                            speak_home_assistant(
                                f"Okay. I'll chill for {duration_text}."
                            )

                            chill_until = (
                                time.monotonic() + chill_seconds
                            )

                            wake_model.reset()
                            vad.reset_states()

                            with sd.InputStream(
                                samplerate=SAMPLE_RATE,
                                channels=1,
                                dtype="int16",
                                blocksize=WAKE_CHUNK,
                                device=DEVICE,
                            ) as chill_stream:

                                while time.monotonic() < chill_until:
                                    audio, overflowed = chill_stream.read(
                                        WAKE_CHUNK
                                    )

                                    audio = np.squeeze(audio)

                                    scores = wake_model.predict(audio)

                                    woke_early = False

                                    for name, score in scores.items():
                                        if score >= WAKE_THRESHOLD:
                                            print(
                                                "\nWake word detected "
                                                "during chill mode."
                                            )

                                            chill_stream.stop()

                                            # Stay silent during chill mode.
                                            # Speaking "Yes" here can be picked
                                            # up by our own microphone.
                                            wake_model.reset()
                                            vad.reset_states()
                                            time.sleep(0.15)

                                            if record_question():
                                                print("Transcribing...")

                                                segments, info = (
                                                    whisper_model.transcribe(
                                                        WAV_FILE,
                                                        language="en",
                                                    )
                                                )

                                                wake_text = " ".join(
                                                    segment.text.strip()
                                                    for segment in segments
                                                ).strip()

                                                print(
                                                    f"You said: {wake_text}"
                                                )

                                                normalized_wake_text = (
                                                    normalize_command(
                                                        wake_text
                                                    )
                                                )

                                                wake_commands = {
                                                    "wake up",
                                                    "wake",
                                                    "come back",
                                                    "im back",
                                                    "i am back",
                                                }

                                                wake_command_text = (
                                                    normalized_wake_text
                                                )

                                                for prefix in (
                                                    "yes ",
                                                    "jarvis ",
                                                    "hey jarvis ",
                                                ):
                                                    if wake_command_text.startswith(
                                                        prefix
                                                    ):
                                                        wake_command_text = (
                                                            wake_command_text[
                                                                len(prefix):
                                                            ]
                                                        )

                                                if wake_command_text in wake_commands:
                                                    print(
                                                        "Chill mode "
                                                        "cancelled early."
                                                    )

                                                    speak_home_assistant(
                                                        "I'm back."
                                                    )

                                                    woke_early = True

                                            break

                                    if woke_early:
                                        break

                                    if not chill_stream.active:
                                        wake_model.reset()
                                        vad.reset_states()
                                        chill_stream.start()

                            print(
                                "Chill period complete. "
                                "Returning to wake-word mode."
                            )

                            wake_model.reset()
                            vad.reset_states()
                            reconnect_requested = True
                            break

                        if text:
                            answer = answer_climate_question(text)

                            if answer is None:
                                answer = answer_weather_question(text)

                            if answer is None:
                                answer = ask_anythingllm(text)

                            print(f"Assistant: {answer}")

                            speak_home_assistant(answer)

                finally:
                    vad.reset_states()
                    wake_model.reset()

                    if not shutdown_requested:
                        print(
                            "\nReopening microphone for wake-word detection...",
                            flush=True,
                        )
                        reconnect_requested = True

                if reconnect_requested and not shutdown_requested:
                    break

        if reconnect_requested and not shutdown_requested:
            vad.reset_states()
            wake_model.reset()

            if reconnect_is_error:
                print(
                    f"Retrying microphone in "
                    f"{AUDIO_RECONNECT_RETRY_SECONDS} seconds...",
                    flush=True,
                )

                time.sleep(AUDIO_RECONNECT_RETRY_SECONDS)
            else:
                print(
                    "Reopening microphone immediately...",
                    flush=True,
                )

    except KeyboardInterrupt:
        shutdown_requested = True

    except Exception as exc:
        print(
            f"\n[AUDIO CONNECTION ERROR] "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        if not shutdown_requested:
            print(
                f"Retrying microphone in "
                f"{AUDIO_RECONNECT_RETRY_SECONDS} seconds...",
                flush=True,
            )
            time.sleep(AUDIO_RECONNECT_RETRY_SECONDS)

print("Jarvis stopped.")
