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


with sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
    blocksize=WAKE_CHUNK,
    device=DEVICE,
) as stream:

    shutdown_requested = False

    while True:
        audio, overflowed = stream.read(WAKE_CHUNK)
        audio = np.squeeze(audio)

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

        # Close the wake-word microphone stream while
        # record_question() opens its VAD microphone stream.
        stream.stop()

        # Audible acknowledgement so the user knows Jarvis
        # heard the wake word before listening for the question.
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

                if text.lower().strip(" .!?") in {
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
                stream.start()
                print("\nListening for: HEY JARVIS")

    print("Jarvis stopped.")
