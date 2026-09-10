from kokoro_mlx import KokoroTTS

tts = KokoroTTS.from_pretrained()

tts.save(
    "Hello. I am Jarvis. Your local home assistant is working.",
    "jarvis_test.wav",
    voice="af_heart",
    speed=1.0,
)

print("Created jarvis_test.wav")