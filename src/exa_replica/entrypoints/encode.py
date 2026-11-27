"""GPU worker entrypoint (D89): query encode + R0 dense + rerank.

Runs a WorkerServer over a Unix socket (msgpack); the gateway connects via
WorkerClient. Blocks for the systemd unit. The pool handler is a stub in M5
(real encode/R0/rerank behind the port).
"""

from __future__ import annotations

import time

from exa_replica.bootstrap.ipc import WorkerServer


def main() -> None:
    server = WorkerServer(
        "/tmp/exa-replica-gpu.sock", handler=lambda req: {"pool": "gpu", "echo": req}
    )
    server.start()
    try:
        while True:
            time.sleep(3600)
    finally:
        server.stop()


if __name__ == "__main__":
    main()