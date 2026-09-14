import sounddevice as sd
import numpy as np
import wave
import time
import json
from pathlib import Path
from collections import deque

from openwakeword.model import Model
from openwakeword.vad import VAD
from faster_whisper import WhisperModel

from anythingllm_client import ask_anythingllm
from time_service import answer_time_question
from conversation_service import CASUAL, ROOM_QUESTION, classify_utterance
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
START_THRESHOLD = 0.008
CONTINUE_THRESHOLD = 0.003
SILENCE_SECONDS = 0.8
MAX_RECORD_SECONDS = 15
PRE_ROLL_SECONDS = 0.4
SPEECH_START_TIMEOUT_SECONDS = 30
SPEECH_START_CONSECUTIVE_CHUNKS = 3

# Diagnostic interval while testing headset disconnect/reconnect.
AUDIO_HEALTH_INTERVAL_SECONDS = 60
EXPECTED_INPUT_DEVICE = "Arctis 7P+"

# Reopen the microphone if it delivers continuous digital silence.
ZERO_AUDIO_RECONNECT_SECONDS = 300  # 5 minutes
AUDIO_RECONNECT_RETRY_SECONDS = 5

# After Jarvis answers, remain available for natural follow-up
# questions without requiring the wake word again.
CONVERSATION_TIMEOUT_SECONDS = 30

# Runtime-adjustable Jarvis settings.
SETTINGS_FILE = Path(".jarvis_settings.json")

DEFAULT_SETTINGS = {
    # How long Jarvis gives another person in the room
    # a chance to answer an overheard question.
    "room_answer_delay": 2.0,
}

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



def human_speaks_during_room_delay(delay_seconds):
    """
    Give another person a chance to answer a room question.

    Returns True if human speech begins during the grace period.
    If speech begins, wait for that person to finish before
    returning so Jarvis does not immediately capture the answer
    as another follow-up.
    """
    if delay_seconds <= 0:
        return False

    print(
        f"[ROOM] Waiting {format_seconds(delay_seconds)} "
        "for someone else to answer..."
    )

    speech_hits = 0
    speech_started = False
    last_speech_time = None

    start_time = time.monotonic()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=VAD_CHUNK,
        device=DEVICE,
    ) as stream:

        while True:
            audio, _ = stream.read(VAD_CHUNK)
            audio = np.squeeze(audio)

            score = float(
                vad.predict(
                    audio,
                    frame_size=VAD_CHUNK,
                )
            )

            now = time.monotonic()

            if not speech_started:
                if score >= START_THRESHOLD:
                    speech_hits += 1
                else:
                    speech_hits = 0

                if (
                    speech_hits
                    >= SPEECH_START_CONSECUTIVE_CHUNKS
                ):
                    speech_started = True
                    last_speech_time = now

                    print(
                        "[ROOM] Someone else started speaking. "
                        "Jarvis will stay quiet."
                    )

                elif now - start_time >= delay_seconds:
                    print(
                        "[ROOM] Nobody answered."
                    )
                    return False

            else:
                if score >= CONTINUE_THRESHOLD:
                    last_speech_time = now

                if (
                    last_speech_time is not None
                    and now - last_speech_time
                    >= SILENCE_SECONDS
                ):
                    return True


def record_question():
    frames = []
    pre_roll_chunks = max(
        1,
        int(PRE_ROLL_SECONDS * SAMPLE_RATE / VAD_CHUNK),
    )
    pre_roll = deque(maxlen=pre_roll_chunks)
    speech_started = False
    speech_start_hits = 0
    last_speech_time = None
    record_start_time = None

    print("Waiting for your question...")
    wait_start_time = time.monotonic()

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
                if (
                    time.monotonic() - wait_start_time
                    >= SPEECH_START_TIMEOUT_SECONDS
                ):
                    print("No speech detected.")
                    return False

                pre_roll.append(audio.copy())

                if score >= START_THRESHOLD:
                    speech_start_hits += 1
                else:
                    speech_start_hits = 0

                if (
                    speech_start_hits
                    >= SPEECH_START_CONSECUTIVE_CHUNKS
                ):
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


def load_settings():
    settings = DEFAULT_SETTINGS.copy()

    if not SETTINGS_FILE.exists():
        return settings

    try:
        saved = json.loads(SETTINGS_FILE.read_text())

        for name in DEFAULT_SETTINGS:
            if name in saved:
                settings[name] = saved[name]

    except Exception as exc:
        print(
            f"Could not load {SETTINGS_FILE}: "
            f"{type(exc).__name__}: {exc}"
        )

    return settings


def save_settings(settings):
    SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2) + "\n"
    )


def format_seconds(value):
    value = float(value)

    if value.is_integer():
        value = int(value)

    return (
        "1 second"
        if value == 1
        else f"{value} seconds"
    )


def handle_parameter_command(text, settings):
    """
    Returns True when text is a Jarvis parameter command.

    Examples:
      Set room answer delay to 3 seconds.
      Update room answer delay to 2.5 seconds.
      What is the room answer delay?
    """
    import re

    normalized = normalize_command(text)

    if normalized in {
        "list parameters",
        "list parameter",
        "show parameters",
        "show parameter",
        "what are the parameters",
    }:
        room_delay = format_seconds(
            settings["room_answer_delay"]
        )

        conversation_timeout = format_seconds(
            CONVERSATION_TIMEOUT_SECONDS
        )

        default_sleep = format_chill_duration(
            DEFAULT_CHILL_SECONDS
        )

        message = (
            f"Room answer delay is {room_delay}. "
            f"Follow-up timeout is {conversation_timeout}. "
            f"Default sleep time is {default_sleep}."
        )

        print(message)
        speak_home_assistant(message)

        return True

    query_match = re.fullmatch(
        r"(?:what is|whats|tell me)"
        r"(?: the)? room answer delay",
        normalized,
    )

    if query_match:
        value = settings["room_answer_delay"]
        value_text = format_seconds(value)

        print(
            f"Room answer delay is {value_text}."
        )

        speak_home_assistant(
            f"Room answer delay is {value_text}."
        )

        return True

    update_match = re.fullmatch(
        r"(?:set|sit|update)"
        r"(?: parameter)?"
        r"(?: the)? room answer delay"
        r"(?: parameter)?"
        r"(?: to)?"
        r" (.+?)"
        r"(?: second| seconds| sec| secs)?",
        normalized,
    )

    if update_match:
        value_text = update_match.group(1).strip()

        spoken_numbers = {
            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "thirteen": 13,
            "fourteen": 14,
            "fifteen": 15,
            "sixteen": 16,
            "seventeen": 17,
            "eighteen": 18,
            "nineteen": 19,
            "twenty": 20,
            "twenty one": 21,
            "twenty two": 22,
            "twenty three": 23,
            "twenty four": 24,
            "twenty five": 25,
            "twenty six": 26,
            "twenty seven": 27,
            "twenty eight": 28,
            "twenty nine": 29,
            "thirty": 30,
        }

        if value_text in spoken_numbers:
            value = float(spoken_numbers[value_text])
        else:
            try:
                value = float(value_text)
            except ValueError:
                print(
                    "[PARAMETER PARSER] Value unclear; "
                    "passing to AI."
                )
                return False

    elif (
        "room answer delay" in normalized
        and normalized.startswith(
            ("set ", "sit ", "update ")
        )
    ):
        print(
            "[PARAMETER PARSER] Command unclear; "
            "passing to AI."
        )
        return False

    else:
        return False

    if value < 0 or value > 30:
        speak_home_assistant(
            "Room answer delay must be between "
            "zero and 30 seconds."
        )
        return True

    settings["room_answer_delay"] = value
    save_settings(settings)

    value_text = format_seconds(value)

    print(
        f"Room answer delay updated to {value_text}."
    )

    speak_home_assistant(
        f"Room answer delay updated to {value_text}."
    )

    return True


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


settings = load_settings()

print(
    "Room answer delay: "
    f"{format_seconds(settings['room_answer_delay'])}"
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

                # Start listening immediately after the wake word.
                # This avoids clipping commands spoken naturally as:
                # "Hey Jarvis, what time is it?"
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

                        if handle_parameter_command(
                            text,
                            settings,
                        ):
                            reconnect_requested = True
                            break

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
                            answer = answer_time_question(text)

                            if answer is None:
                                answer = answer_climate_question(text)

                            if answer is None:
                                answer = answer_weather_question(text)

                            if answer is None:
                                answer = ask_anythingllm(text)

                            print(f"Assistant: {answer}")

                            speak_home_assistant(answer)

                            # Basic conversation follow-up mode.
                            # After answering, listen for another question
                            # without requiring the wake word.
                            while not shutdown_requested:
                                print(
                                    "\nConversation mode: "
                                    f"listening for up to "
                                    f"{CONVERSATION_TIMEOUT_SECONDS} seconds..."
                                )

                                # record_question() normally uses the global
                                # speech-start timeout. Temporarily use the
                                # conversation timeout here.
                                previous_timeout = (
                                    SPEECH_START_TIMEOUT_SECONDS
                                )
                                SPEECH_START_TIMEOUT_SECONDS = (
                                    CONVERSATION_TIMEOUT_SECONDS
                                )

                                try:
                                    got_followup = record_question()
                                finally:
                                    SPEECH_START_TIMEOUT_SECONDS = (
                                        previous_timeout
                                    )

                                if not got_followup:
                                    print(
                                        "Conversation timeout. "
                                        "Returning to wake-word mode."
                                    )
                                    break

                                print("Transcribing follow-up...")

                                segments, info = whisper_model.transcribe(
                                    WAV_FILE,
                                    language="en",
                                )

                                followup_text = " ".join(
                                    segment.text.strip()
                                    for segment in segments
                                ).strip()

                                print(
                                    f"Follow-up: {followup_text}"
                                )

                                if not followup_text:
                                    continue

                                followup_kind = classify_utterance(
                                    followup_text,
                                    active_conversation=True,
                                )

                                print(
                                    f"[CONVERSATION] "
                                    f"classification={followup_kind}"
                                )

                                if followup_kind == CASUAL:
                                    print(
                                        "[CONVERSATION] "
                                        "Casual speech ignored."
                                    )
                                    continue

                                if (
                                    followup_kind
                                    == ROOM_QUESTION
                                ):
                                    human_answered = (
                                        human_speaks_during_room_delay(
                                            settings[
                                                "room_answer_delay"
                                            ]
                                        )
                                    )

                                    if human_answered:
                                        continue

                                followup_answer = (
                                    answer_time_question(
                                        followup_text
                                    )
                                )

                                if followup_answer is None:
                                    followup_answer = (
                                        answer_climate_question(
                                            followup_text
                                        )
                                    )

                                if followup_answer is None:
                                    followup_answer = (
                                        answer_weather_question(
                                            followup_text
                                        )
                                    )

                                if followup_answer is None:
                                    followup_answer = (
                                        ask_anythingllm(
                                            followup_text
                                        )
                                    )

                                print(
                                    f"Assistant: {followup_answer}"
                                )
                                speak_home_assistant(
                                    followup_answer
                                )

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
