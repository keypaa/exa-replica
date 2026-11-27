-- Exa Replica identity schema (Postgres v1) — D2 accounts, D3–D7 api_keys.
-- Applied at deploy; the M3 tests use an in-memory repository (no Docker).

CREATE TABLE IF NOT EXISTS accounts (
    account_id  TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'active',   -- active | suspended | banned
    reason      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id         TEXT PRIMARY KEY,
    account_id     TEXT NOT NULL REFERENCES accounts(account_id),
    scopes         TEXT[] NOT NULL,
    hash_version   INT  NOT NULL,
    pepper_version INT  NOT NULL,
    key_hash       TEXT NOT NULL,                 -- HMAC(pepper, secret), never plaintext
    expires_at     TIMESTAMPTZ,
    rotated_from   TEXT,
    revoked        BOOLEAN NOT NULL DEFAULT FALSE,
    revoke_reason  TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_account ON api_keys(account_id);