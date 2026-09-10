import sys
import tempfile
import subprocess

from kokoro_mlx import KokoroTTS

tts = KokoroTTS.from_pretrained()

text = " ".join(sys.argv[1:]).strip()

if not text:
    raise SystemExit("Usage: python speak.py 'text to speak'")

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    wav_file = f.name

tts.save(
    text,
    wav_file,
    voice="af_heart",
    speed=1.0,
)

subprocess.run(["afplay", wav_file], check=True)