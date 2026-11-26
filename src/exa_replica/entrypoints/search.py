"""Search pool entrypoint (D89). Single-process fallback for M0; real pools in M5."""

from __future__ import annotations

import uvicorn

from exa_replica.bootstrap.composition import build_default_gateway


def main() -> None:
    app = build_default_gateway()
    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()