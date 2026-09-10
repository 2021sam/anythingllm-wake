import sounddevice as sd
import numpy as np
import wave
import subprocess
from openwakeword.model import Model
from faster_whisper import WhisperModel
from anythingllm_client import ask_anythingllm
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TTS_PYTHON = BASE_DIR / ".venv-tts" / "bin" / "python"
SPEAK_SCRIPT = BASE_DIR / "speak.py"

SAMPLE_RATE = 16000
CHUNK = 1280
DEVICE = 1
THRESHOLD = 0.5

RECORD_SECONDS = 7
WAV_FILE = "wake_question.wav"

wake_model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx"
)

print("Loading Whisper model...")
whisper_model = WhisperModel(
    "base.en",
    device="cpu",
    compute_type="int8"
)

print("Listening for: HEY JARVIS")
print("Press Ctrl+C to stop.")

with sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
    blocksize=CHUNK,
    device=DEVICE,
) as stream:
    while True:
        audio, overflowed = stream.read(CHUNK)
        audio = np.squeeze(audio)

        scores = wake_model.predict(audio)

        for name, score in scores.items():
            if score >= THRESHOLD:
                print(f"\nWAKE WORD DETECTED: {name} score={score:.2f}")
                print("Speak your question...")

                recorded = sd.rec(
                    int(RECORD_SECONDS * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="int16",
                    device=DEVICE,
                )

                sd.wait()

                with wave.open(WAV_FILE, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(recorded.tobytes())

                print("Transcribing...")

                segments, info = whisper_model.transcribe(
                    WAV_FILE,
                    language="en",
                )

                text = " ".join(
                    segment.text.strip()
                    for segment in segments
                )

                print(f"You said: {text}")

                if text:
                    answer = ask_anythingllm(text)
                    print(f"Assistant: {answer}")

                    subprocess.run(
                        [
                            str(TTS_PYTHON),
                            str(SPEAK_SCRIPT),
                            answer,
                        ],
                        check=True,
                    )


                wake_model.reset()