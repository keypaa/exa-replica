"""Local IPC over a Unix socket + msgpack (D89). No external broker in v1.

The socket is created 0600 (D91). `WorkerServer` handles one request per
connection; `WorkerClient` sends a request and reads the reply.
"""

from __future__ import annotations

import os
import socket
import threading
from collections.abc import Callable

import msgpack


class WorkerServer:
    def __init__(self, socket_path: str, handler: Callable[[dict[str, object]], dict[str, object]]) -> None:
        self._path = socket_path
        self._handler = handler
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = False

    def start(self) -> None:
        if os.path.exists(self._path):
            os.remove(self._path)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(self._path)
        os.chmod(self._path, 0o600)  # D91
        self._sock.listen(4)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        assert self._sock is not None
        while not self._stop:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break
            with conn:
                chunks = []
                while True:
                    buf = conn.recv(4096)
                    if not buf:
                        break
                    chunks.append(buf)
                if not chunks:
                    continue
                req = msgpack.unpackb(b"".join(chunks))
                conn.sendall(msgpack.packb(self._handler(req)))

    def stop(self) -> None:
        self._stop = True
        if self._sock is not None:
            self._sock.close()
        if self._thread is not None:
            self._thread.join(timeout=1)


class WorkerClient:
    def __init__(self, socket_path: str) -> None:
        self._path = socket_path

    def request(self, req: dict[str, object]) -> dict[str, object]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(self._path)
            s.sendall(msgpack.packb(req))
            s.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                buf = s.recv(4096)
                if not buf:
                    break
                chunks.append(buf)
        result: dict[str, object] = msgpack.unpackb(b"".join(chunks))
        return result