import os
import stat

from exa_replica.bootstrap.ipc import WorkerClient, WorkerServer


def test_ipc_socket_0600(tmp_path):
    sock = str(tmp_path / "w.sock")
    server = WorkerServer(sock, handler=lambda req: {"echo": req})
    server.start()
    try:
        client = WorkerClient(sock)
        assert client.request({"x": 1}) == {"echo": {"x": 1}}
        mode = stat.S_IMODE(os.stat(sock).st_mode)
        assert mode == 0o600  # IPC 0600 (D91)
    finally:
        server.stop()


def test_gateway_workers(tmp_path):
    sock = str(tmp_path / "gw.sock")
    server = WorkerServer(sock, handler=lambda req: {"results": [req["q"]]})
    server.start()
    try:
        assert WorkerClient(sock).request({"q": "hello"}) == {"results": ["hello"]}
    finally:
        server.stop()


def test_build_id_mismatch_refused():
    from exa_replica.bootstrap.topology import build_id_consistent

    assert build_id_consistent(["b1", "b1", "b1"])
    assert not build_id_consistent(["b1", "b2"])  # gateway refuses mixed builds (D89)