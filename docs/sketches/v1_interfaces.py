"""V1 interface sketch (v2) — design only, not implemented.

Pure Python, no I/O. Unit-testable without a GPU or network.
Python 3.11+.

Target package layout::

    search/
      domain/    types.py  fusion.py  deadline.py
      services/  ports.py   pipeline.py
      api/       models.py  routes.py
      transport/ http.py    mcp.py  gpu_worker.py

Import rule: ``domain`` (stdlib only) <- ``services`` <- ``api`` <- ``transport``.
Enforce with ``import-linter``.

This file is a sketch: it exists to review the seams, not to ship.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Literal, NewType, Protocol, runtime_checkable

Stage = Literal["bm25", "dense", "rrf", "rerank"]

# ---------------------------------------------------------------------------
# domain/types.py
# ---------------------------------------------------------------------------

DocId = NewType("DocId", str)
ChunkId = NewType("ChunkId", str)
Vector = tuple[float, ...]


class Tier(StrEnum):
    LITE = "lite"
    AUTO = "auto"
    DEEP = "deep"


@dataclass(frozen=True, slots=True)
class Filters:
    """Pre-retrieval constraints.

    Every Retriever must apply these fully or raise UnsupportedFilter.
    Silent dropping is a bug.
    """

    include_domains: frozenset[str] = frozenset()
    exclude_domains: frozenset[str] = frozenset()
    published_after: datetime | None = None
    published_before: datetime | None = None
    categories: frozenset[str] = frozenset()

    def is_empty(self) -> bool:
        return self == Filters()


@dataclass(frozen=True, slots=True)
class Passage:
    """An indexed unit of text: one chunk of one document.

    If ``text`` is not stored inline, the stage that needs it must define how
    many hits it fetches and what happens when a fetch fails.
    """

    chunk_id: ChunkId
    doc_id: DocId
    url: str
    text: str
    char_start: int
    char_end: int
    index_version: str


@dataclass(frozen=True, slots=True)
class Hit:
    """A passage plus its scores, one entry per stage that touched it.

    Stages never mutate a Hit; they return a new one via with_score().
    """

    passage: Passage
    scores: Mapping[Stage, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "scores", MappingProxyType(dict(self.scores)))

    def with_score(self, stage: Stage, value: float) -> "Hit":
        return replace(self, scores={**self.scores, stage: value})

    def __hash__(self) -> int:
        return hash(self.passage.chunk_id)


@dataclass(frozen=True, slots=True)
class Query:
    text: str
    objective: str = ""  # required by web_search_exa; must be consumed, not ignored
    filters: Filters = Filters()
    k: int = 10
    tier: Tier = Tier.AUTO


@dataclass(frozen=True, slots=True)
class ContentsSpec:
    text: bool = False
    highlights: bool = False
    summary: bool = False
    max_chars: int | None = None


@dataclass(frozen=True, slots=True)
class Contents:
    doc_id: DocId
    url: str
    text: str | None = None
    highlights: tuple[str, ...] = ()
    summary: str | None = None


@dataclass(frozen=True, slots=True)
class Document:
    doc_id: DocId
    url: str
    title: str
    text: str
    lang: str
    published_at: datetime | None
    crawled_at: datetime
    content_hash: str
    index_version: str


@dataclass(frozen=True, slots=True)
class Synthesis:
    output: Mapping[str, object]
    citations: tuple[DocId, ...]


@dataclass(frozen=True, slots=True)
class SearchResult:
    hits: tuple[Hit, ...]
    contents: Mapping[DocId, Contents] = field(default_factory=dict)
    synthesis: Synthesis | None = None
    degraded: tuple[str, ...] = ()  # stages skipped under deadline/error
    stage_seconds: Mapping[str, float] = field(default_factory=dict)
    index_version: str = ""


# ---------------------------------------------------------------------------
# domain/fusion.py
# ---------------------------------------------------------------------------


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[Hit]],
    *,
    stage: Stage = "rrf",
    k: int = 60,
) -> tuple[Hit, ...]:
    """Pure RRF. Merges results from several retrievers or query variants."""

    fused: dict[ChunkId, float] = {}
    best: dict[ChunkId, Hit] = {}
    for hits in ranked_lists:
        for rank, hit in enumerate(hits, start=1):
            cid = hit.passage.chunk_id
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank)
            best.setdefault(cid, hit)
    ordered = sorted(fused, key=fused.__getitem__, reverse=True)
    return tuple(best[c].with_score(stage, fused[c]) for c in ordered)


# ---------------------------------------------------------------------------
# domain/deadline.py
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Deadline:
    """Absolute monotonic deadline.

    Workers check ``expired()`` cooperatively between batches; asyncio
    cancellation does not stop a thread/process already running.
    """

    expires_at: float
    clock: Callable[[], float] = time.monotonic

    @classmethod
    def after(
        cls, seconds: float, clock: Callable[[], float] = time.monotonic
    ) -> "Deadline":
        return cls(expires_at=clock() + seconds, clock=clock)

    def remaining(self) -> float:
        return max(0.0, self.expires_at - self.clock())

    def expired(self) -> bool:
        return self.remaining() == 0.0


@dataclass(frozen=True, slots=True)
class JobContext:
    """What travels with a job to a worker (possibly another process).

    If workers may run off-host, replace ``deadline`` with a remaining
    budget in seconds and subtract queue time at dequeue.
    """

    trace_id: str
    deadline: Deadline
    index_version: str


# ---------------------------------------------------------------------------
# services/ports.py
# ---------------------------------------------------------------------------


class UnsupportedFilter(Exception):
    """Raised by a Retriever that cannot apply a requested Filters field."""


class SynthesisError(Exception):
    """Schema validation or model failure during synthesis."""


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    text: str
    vector: Vector | None  # None for lexical-only retrievers
    filters: Filters
    k: int


@runtime_checkable
class Embedder(Protocol):
    """Batch-first. Implementations batch internally for the GPU.

    Contract: max batch size is implementation-defined; per-item failure is
    reported, not raised for the whole batch; the deadline is checked between
    batches.
    """

    async def embed(self, texts: Sequence[str]) -> Sequence[Vector]: ...


@runtime_checkable
class Retriever(Protocol):
    name: str
    # Must be consistent with every TierPlan at startup, or derived from the
    # stages. Two sources of truth is a bug.
    needs_vector: bool

    async def search(self, q: RetrievalQuery, deadline: Deadline) -> Sequence[Hit]:
        """Must apply q.filters fully or raise UnsupportedFilter."""
        ...


@runtime_checkable
class Reranker(Protocol):
    async def rerank(
        self,
        query_text: str,
        hits: Sequence[Hit],
        k: int,
        deadline: Deadline,
    ) -> Sequence[Hit]: ...


@runtime_checkable
class ContentsProvider(Protocol):
    async def get(
        self,
        doc_ids: Sequence[DocId],
        spec: ContentsSpec,
        deadline: Deadline,
    ) -> Mapping[DocId, Contents]: ...


@runtime_checkable
class DocumentStore(Protocol):
    """Source of truth for documents. Postgres in v1; port so the core never imports a DB."""

    def get(self, doc_id: DocId) -> Document | None: ...
    def put(self, doc: Document) -> None: ...
    def delete(self, doc_id: DocId) -> None: ...


@runtime_checkable
class PassageStore(Protocol):
    """Source of truth for passages/chunks. Postgres in v1; port so the core never imports a DB."""

    def get(self, chunk_id: ChunkId) -> Passage | None: ...
    def put(self, passage: Passage) -> None: ...
    def delete(self, chunk_id: ChunkId) -> None: ...
    def by_doc(self, doc_id: DocId) -> Sequence[Passage]: ...


@runtime_checkable
class Synthesizer(Protocol):
    async def synthesize(
        self,
        query_text: str,
        hits: Sequence[Hit],
        output_schema: Mapping[str, object] | None,
        deadline: Deadline,
    ) -> Synthesis:
        """Raises SynthesisError; the pipeline decides to degrade or fail."""
        ...


@runtime_checkable
class QueryUnderstanding(Protocol):
    async def expand(self, q: Query, deadline: Deadline) -> Sequence[Query]:
        """Returns query variants; the original query must be first."""
        ...


class Tracer(Protocol):
    def record(
        self, stage: str, seconds: float, tier: str, ok: bool, trace_id: str
    ) -> None: ...


# ---------------------------------------------------------------------------
# services/pipeline.py
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TierPlan:
    """Which stages a tier runs. The tier is configuration, not code."""

    expand: bool
    rerank: bool
    synthesize: bool
    rerank_pool: int = 50


@dataclass(frozen=True, slots=True)
class SearchPipeline:
    embedder: Embedder
    retrievers: Sequence[Retriever]
    reranker: Reranker
    understanding: QueryUnderstanding
    synthesizer: Synthesizer
    tracer: Tracer
    plans: Mapping[Tier, TierPlan] = field(
        default_factory=lambda: {
            Tier.LITE: TierPlan(expand=False, rerank=False, synthesize=False),
            Tier.AUTO: TierPlan(expand=False, rerank=True, synthesize=False),
            Tier.DEEP: TierPlan(expand=True, rerank=True, synthesize=True),
        }
    )

    async def run(
        self,
        q: Query,
        deadline: Deadline,
        index_version: str,
        output_schema: Mapping[str, object] | None = None,
        trace_id: str = "",
    ) -> SearchResult:
        # Pin the index version for the whole request: a swap mid-request would
        # otherwise resolve IDs from one version against another.
        # Admission control: a dedicated, bounded executor per tier (not the
        # shared asyncio.to_thread default). Queue full -> 503 + Retry-After.
        # Dequeue-time check: if deadline.expired(), skip. A single
        # uninterruptible call must be bounded (max batch, max k) so the
        # deadline can be checked between batches.
        plan = self.plans[q.tier]
        degraded: list[str] = []
        timings: dict[str, float] = {}

        async def timed(stage: str, coro):
            t0 = time.monotonic()
            ok = True
            try:
                return await coro
            except Exception:
                ok = False
                raise
            finally:
                dt = time.monotonic() - t0
                timings[stage] = dt
                self.tracer.record(stage, dt, q.tier, ok, trace_id)

        # 1. Query variants (deep only; original first)
        variants: list[Query] = [q]
        if plan.expand and not deadline.expired():
            try:
                variants = list(
                    await timed("expand", self.understanding.expand(q, deadline))
                )
            except Exception:
                degraded.append("expand")

        # 2. Embed all variants in one batch
        vectors = list(
            await timed("embed", self.embedder.embed([v.text for v in variants]))
        )

        # 3. Retrieve: one task per (retriever, variant), run concurrently
        async def retrieve_one(
            retriever: Retriever, v: Query, vec: Vector | None
        ) -> Sequence[Hit]:
            rq = RetrievalQuery(
                text=v.text,
                vector=vec if retriever.needs_vector else None,
                filters=v.filters,
                k=q.k,
            )
            return await retriever.search(rq, deadline)

        tasks: list[tuple[str, asyncio.Task[Sequence[Hit]]]] = []
        for retriever in self.retrievers:
            for v, vec in zip(variants, vectors):
                tasks.append(
                    (
                        retriever.name,
                        asyncio.ensure_future(
                            timed(
                                f"retrieve:{retriever.name}",
                                retrieve_one(retriever, v, vec),
                            )
                        ),
                    )
                )

        results = await asyncio.gather(
            *(future for _, future in tasks), return_exceptions=True
        )

        ranked_lists: list[Sequence[Hit]] = []
        for (name, _), res in zip(tasks, results):
            if isinstance(res, UnsupportedFilter):
                raise res
            if isinstance(res, Exception):
                degraded.append(f"retrieve:{name}")
                continue
            ranked_lists.append(res)

        hits = reciprocal_rank_fusion(ranked_lists, stage="rrf")[: plan.rerank_pool]

        # 4. Rerank if the tier asks for it and time allows
        if plan.rerank and hits and not deadline.expired():
            try:
                hits = list(
                    await timed(
                        "rerank",
                        self.reranker.rerank(q.text, hits, q.k, deadline),
                    )
                )
            except Exception:
                degraded.append("rerank")

        hits = tuple(hits[: q.k])

        # 5. Synthesis (optional); failure degrades, does not fail /search
        synthesis = None
        if plan.synthesize and hits and not deadline.expired():
            try:
                synthesis = await timed(
                    "synthesize",
                    self.synthesizer.synthesize(
                        q.text, hits, output_schema, deadline
                    ),
                )
            except SynthesisError:
                degraded.append("synthesize")

        return SearchResult(
            hits=hits,
            synthesis=synthesis,
            degraded=tuple(degraded),
            stage_seconds=timings,
            index_version=index_version,
        )