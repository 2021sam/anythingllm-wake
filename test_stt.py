import sounddevice as sd
import numpy as np
import wave
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
DEVICE = 1
RECORD_SECONDS = 5
WAV_FILE = "test_question.wav"

print("Loading Whisper model...")
model = WhisperModel("base.en", device="cpu", compute_type="int8")

print("Speak now for 5 seconds...")

audio = sd.rec(
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
    wf.writeframes(audio.tobytes())

print("Transcribing...")

segments, info = model.transcribe(
    WAV_FILE,
    language="en",
)

text = " ".join(segment.text.strip() for segment in segments)

print(f"You said: {text}")