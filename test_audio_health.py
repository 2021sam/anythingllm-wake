import time
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHUNK = 1600
DEVICE = 1
REPORT_SECONDS = 5

print("Audio health test")
print("Turn the headset ON/OFF while this runs.")
print("Press Ctrl+C to stop.\n")

with sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
    blocksize=CHUNK,
    device=DEVICE,
) as stream:

    rms_values = []
    peak_values = []
    last_report = time.monotonic()

    while True:
        try:
            audio, overflowed = stream.read(CHUNK)
        except Exception as exc:
            print(
                f"AUDIO READ ERROR: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            raise

        audio = np.squeeze(audio).astype(np.float32)

        rms = float(
            np.sqrt(np.mean(audio * audio))
        )
        peak = float(np.max(np.abs(audio)))

        rms_values.append(rms)
        peak_values.append(peak)

        now = time.monotonic()

        if now - last_report >= REPORT_SECONDS:
            avg_rms = sum(rms_values) / len(rms_values)
            max_rms = max(rms_values)
            max_peak = max(peak_values)

            print(
                f"avg_rms={avg_rms:8.2f}  "
                f"max_rms={max_rms:8.2f}  "
                f"peak={max_peak:8.2f}  "
                f"stream_active={stream.active}",
                flush=True,
            )

            rms_values.clear()
            peak_values.clear()
            last_report = now
