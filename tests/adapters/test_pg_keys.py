from exa_replica.adapters.outbound.pg.keys import ApiKeyService, KeyRecord


class _MemRepo:
    def __init__(self):
        self._d: dict[str, KeyRecord] = {}

    def put(self, rec: KeyRecord) -> None:
        self._d[rec.key_id] = rec

    def get(self, key_id: str):
        return self._d.get(key_id)

    def list_by_account(self, account_id: str):
        return [r for r in self._d.values() if r.account_id == account_id]


def _svc(clock=lambda: 1000.0):
    return ApiKeyService(_MemRepo(), pepper=b"pepper", clock=clock)


def test_key_format():
    key, rec = _svc().generate("acc1", ("search:lite",))
    assert key.startswith("exa_")
    secret = key[len("exa_"):]
    assert len(secret) == 64
    int(secret, 16)  # hex
    assert rec.expires_at is not None  # 1-year default (D5)


def test_hash_hmac():
    svc = _svc()
    key, rec = svc.generate("acc1", ("search:lite",))
    assert svc.verify(key) is not None
    assert svc.verify("exa_" + "0" * 64) is None  # wrong key -> uniform failure
    assert key[len("exa_"):] not in str(rec)  # secret not stored in plaintext


def test_expiry():
    now = [1000.0]
    svc = _svc(clock=lambda: now[0])
    key, rec = svc.generate("acc1", ("search:lite",), ttl_days=1)
    now[0] = rec.expires_at + 1
    assert svc.verify(key) is None  # expired (D5)


def test_rotation_grace():
    now = [1000.0]
    svc = _svc(clock=lambda: now[0])
    key, rec = svc.generate("acc1", ("search:lite",))
    _new_key, new_rec = svc.rotate(rec.key_id)
    assert new_rec.rotated_from == rec.key_id
    # old key still valid during grace (D6)
    assert svc.verify(key) is not None
    # rotating again during grace is refused
    try:
        svc.rotate(rec.key_id)
        raise AssertionError("rotation during grace must be refused")
    except ValueError:
        pass