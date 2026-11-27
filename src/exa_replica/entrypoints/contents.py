"""CPU worker entrypoint (D89): BM25 + contents store read + highlights.

Runs a WorkerServer over a Unix socket (msgpack); the gateway connects via
WorkerClient. Blocks for the systemd unit.
"""

from __future__ import annotations

import time

from exa_replica.bootstrap.ipc import WorkerServer


def main() -> None:
    server = WorkerServer(
        "/tmp/exa-replica-cpu.sock", handler=lambda req: {"pool": "cpu", "echo": req}
    )
    server.start()
    try:
        while True:
            time.sleep(3600)
    finally:
        server.stop()


if __name__ == "__main__":
    main()