import socket
import threading
from collections import deque

import numpy as np


class NetworkMicrophone:
    """
    Receive 16 kHz, mono, signed 16-bit little-endian PCM audio
    from a remote microphone endpoint over TCP.
    """

    def __init__(
        self,
        host="0.0.0.0",
        port=5001,
        sample_rate=16000,
        max_buffer_seconds=5,
    ):
        self.host = host
        self.port = port
        self.sample_rate = sample_rate

        self._max_samples = sample_rate * max_buffer_seconds

        self._buffer = deque()
        self._buffered_samples = 0

        self._condition = threading.Condition()

        self._running = False
        self._connected = False

        self._server_socket = None
        self._client_socket = None
        self._client_address = None
        self._thread = None

    @property
    def connected(self):
        return self._connected

    @property
    def client_address(self):
        return self._client_address

    def start(self):
        if self._running:
            return

        self._running = True

        self._thread = threading.Thread(
            target=self._server_loop,
            name="network-microphone",
            daemon=True,
        )

        self._thread.start()

    def stop(self):
        self._running = False

        if self._client_socket is not None:
            try:
                self._client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                self._client_socket.close()
            except OSError:
                pass

        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:
                pass

        with self._condition:
            self._condition.notify_all()

    def _server_loop(self):
        while self._running:
            try:
                with socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                ) as server:
                    self._server_socket = server

                    server.setsockopt(
                        socket.SOL_SOCKET,
                        socket.SO_REUSEADDR,
                        1,
                    )

                    server.bind((self.host, self.port))
                    server.listen(1)
                    server.settimeout(1.0)

                    print(
                        f"[NETWORK MIC] Listening on "
                        f"{self.host}:{self.port}",
                        flush=True,
                    )

                    while self._running:
                        try:
                            client, address = server.accept()
                        except socket.timeout:
                            continue

                        self._handle_client(client, address)

            except OSError as exc:
                if self._running:
                    print(
                        f"[NETWORK MIC] Server error: {exc}",
                        flush=True,
                    )

            finally:
                self._server_socket = None

    def _handle_client(self, client, address):
        self._client_socket = client
        self._client_address = address
        self._connected = True

        print(
            f"[NETWORK MIC] Connected: "
            f"{address[0]}:{address[1]}",
            flush=True,
        )

        pending = b""

        try:
            with client:
                while self._running:
                    chunk = client.recv(65536)

                    if not chunk:
                        break

                    pending += chunk

                    usable_bytes = len(pending) - (len(pending) % 2)

                    if usable_bytes == 0:
                        continue

                    samples = np.frombuffer(
                        pending[:usable_bytes],
                        dtype="<i2",
                    ).copy()

                    pending = pending[usable_bytes:]

                    self._append_samples(samples)

        except OSError as exc:
            if self._running:
                print(
                    f"[NETWORK MIC] Client error: {exc}",
                    flush=True,
                )

        finally:
            self._client_socket = None
            self._client_address = None
            self._connected = False

            with self._condition:
                self._condition.notify_all()

            print(
                "[NETWORK MIC] Disconnected",
                flush=True,
            )

    def _append_samples(self, samples):
        with self._condition:
            self._buffer.append(samples)
            self._buffered_samples += len(samples)

            while (
                self._buffer
                and self._buffered_samples > self._max_samples
            ):
                removed = self._buffer.popleft()
                self._buffered_samples -= len(removed)

            self._condition.notify_all()

    def read(self, frame_count, timeout=None):
        """
        Return exactly frame_count NumPy int16 samples.
        """

        with self._condition:
            ready = self._condition.wait_for(
                lambda: (
                    self._buffered_samples >= frame_count
                    or not self._running
                ),
                timeout=timeout,
            )

            if not ready or self._buffered_samples < frame_count:
                raise TimeoutError(
                    "Timed out waiting for network microphone audio"
                )

            output = np.empty(
                frame_count,
                dtype=np.int16,
            )

            written = 0

            while written < frame_count:
                chunk = self._buffer[0]
                needed = frame_count - written

                if len(chunk) <= needed:
                    count = len(chunk)

                    output[
                        written:written + count
                    ] = chunk

                    written += count

                    self._buffer.popleft()
                    self._buffered_samples -= count

                else:
                    output[written:] = chunk[:needed]

                    self._buffer[0] = chunk[needed:]
                    self._buffered_samples -= needed

                    written += needed

            return output


if __name__ == "__main__":
    import time

    microphone = NetworkMicrophone()
    microphone.start()

    print()
    print("========== NETWORK MICROPHONE TEST ==========")
    print("Waiting for Raspberry Pi audio...")
    print()

    deadline = time.monotonic() + 30

    try:
        while time.monotonic() < deadline:
            try:
                audio = microphone.read(
                    16000,
                    timeout=2,
                )

            except TimeoutError:
                print(
                    "Waiting for audio...",
                    flush=True,
                )
                continue

            audio_float = (
                audio.astype(np.float32) / 32768.0
            )

            rms = float(
                np.sqrt(
                    np.mean(audio_float * audio_float)
                )
            )

            peak = int(
                np.max(
                    np.abs(
                        audio.astype(np.int32)
                    )
                )
            )

            print(
                f"Received 1 second: "
                f"RMS={rms:.6f} "
                f"PEAK={peak}",
                flush=True,
            )

    except KeyboardInterrupt:
        pass

    finally:
        microphone.stop()

    print()
    print("========== TEST FINISHED ==========")
