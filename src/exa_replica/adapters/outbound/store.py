"""Content store + docstore (D48–D50).

Documents are stored as Parquet shards (zstd) selected by `hash(url) mod N`.
Passages are stored **offsets-only** — text is reconstructed from the document
text + `[start, end)` byte offsets (D78). A docstore maps `url_canonical` to its
shard.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from exa_replica.domain.document import Document
from exa_replica.domain.models import Passage

_DOC_SCHEMA = pa.schema(
    [
        ("url_canonical", pa.string()),
        ("text", pa.string()),
        ("lang", pa.string()),
        ("content_hash", pa.string()),
    ]
)
_PASS_SCHEMA = pa.schema(
    [
        ("passage_id", pa.string()),
        ("url_canonical", pa.string()),
        ("start", pa.int64()),
        ("end", pa.int64()),
        ("lang", pa.string()),
    ]
)


class ContentStore:
    def __init__(self, root: Path | str, n_shards: int = 8) -> None:
        self.root = Path(root)
        self.n_shards = n_shards
        self.root.mkdir(parents=True, exist_ok=True)
        self._docstore_path = self.root / "docstore.json"

    def shard_of(self, url_canonical: str) -> int:
        h = hashlib.sha1(url_canonical.encode("utf-8")).digest()
        return int.from_bytes(h[:4], "big") % self.n_shards

    def _shard_file(self, shard: int) -> Path:
        return self.root / f"docs-{shard:03d}.parquet"

    def _pass_file(self) -> Path:
        return self.root / "passages.parquet"

    def _append(self, path: Path, schema: pa.Schema, rows: list[dict[str, object]]) -> None:
        table = pa.Table.from_pylist(rows, schema=schema)
        if path.exists():
            table = pa.concat_tables([pq.read_table(path), table])
        pq.write_table(table, path, compression="zstd")

    def _docstore(self) -> dict[str, int]:
        if self._docstore_path.exists():
            data: dict[str, int] = json.loads(self._docstore_path.read_text())
            return data
        return {}

    def put(self, doc: Document, passages: Sequence[Passage]) -> None:
        shard = self.shard_of(doc.url_canonical)
        self._append(
            self._shard_file(shard),
            _DOC_SCHEMA,
            [
                {
                    "url_canonical": doc.url_canonical,
                    "text": doc.text_canonical,
                    "lang": doc.lang,
                    "content_hash": doc.content_hash,
                }
            ],
        )
        if passages:
            self._append(
                self._pass_file(),
                _PASS_SCHEMA,
                [
                    {
                        "passage_id": p.passage_id,
                        "url_canonical": doc.url_canonical,
                        "start": p.start,
                        "end": p.end,
                        "lang": p.lang,
                    }
                    for p in passages
                ],
            )
        mapping = self._docstore()
        mapping[doc.url_canonical] = shard
        self._docstore_path.write_text(json.dumps(mapping))

    def get_text(self, url_canonical: str) -> str | None:
        shard = self._docstore().get(url_canonical)
        if shard is None:
            return None
        f = self._shard_file(shard)
        if not f.exists():
            return None
        for row in pq.read_table(f).to_pylist():
            if row["url_canonical"] == url_canonical:
                return str(row["text"])
        return None

    def get_passages(self, url_canonical: str) -> list[tuple[Passage, str]]:
        if not self._pass_file().exists():
            return []
        text = self.get_text(url_canonical) or ""
        raw = text.encode("utf-8")
        out: list[tuple[Passage, str]] = []
        for row in pq.read_table(self._pass_file()).to_pylist():
            if row["url_canonical"] != url_canonical:
                continue
            ptext = raw[row["start"] : row["end"]].decode("utf-8")
            passage = Passage(
                passage_id=row["passage_id"],
                doc_id="",
                text="",
                start=row["start"],
                end=row["end"],
                lang=row["lang"],
            )
            out.append((passage, ptext))
        return out