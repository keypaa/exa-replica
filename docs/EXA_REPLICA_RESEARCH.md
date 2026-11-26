# Exa-Style Search Server — Research & Decision Log

**Status:** Living document. Started 2026-11-22.
**Rule:** Nothing here is final. Every `[DECISION]` needs a baseline measurement behind it.
**Companion:** This is the research/decision log. The eventual design spec will live in `zenno/specs/` and the implementation plan in `zenno/plans/` (per repo convention).

---

## 0. How to use this document

- `[OPEN]` = a question we have not answered.
- `[MEASURE]` = needs a baseline measurement before we can decide.
- `[DECISION]` = decided, with evidence and rationale recorded.
- `[PROP]` = a proposal, not yet accepted.

Update this file as we go. Never delete a point; mark it resolved and link the decision.

**Working rules (from the project owner):**

1. **Measure before you change or decide.** No knob is set by intuition.
2. **One knob at a time.** If one change needs a code change, scale leaked into the logic.
3. **Scale-invariance.** The code and contracts must not know whether there are 1M or 1B documents. Scaling = adding GPUs/nodes + re-partitioning, never rewriting.
4. **Idempotence.** Every stage re-runnable with identical output; no stale artifacts.
5. **Reproducibility.** Every number carries provenance (corpus hash, config, K, model version, git SHA, timestamp).
6. **No single dependency.** No vendor lock-in, no single point of failure.
7. **Modularity.** Swappable seams: data source, embedder, index backend, reranker, generator.
8. **API-first.** The core is an HTTP API (`/search`, `/contents`, ...). MCP is a thin transport adapter over it, not the product. A plain `curl` must work before any MCP code exists.

---

## 1. Thesis: scale-invariance

The product is a **server**, not a lab. Benchmarking is a capability the server must have, not its identity.

What "reproduce Exa MCP" proves is that **the architecture holds its shape while the resource envelope changes**. Exa serves ~100B pages from 2T+ tracked URLs; its 2.0 embedding model was trained on a 144×H200 cluster, and serving details are not public. We will not match that scale on one GPU. The goal is:

> A self-hosted, open-source search engine that behaves like Exa on the surface, and whose **code does not change** from a few million to billions of documents — only the number of shards, GPUs, and nodes does.

That is the bar. If a scale-up requires a rewrite, the design failed.

### 1.1 Definition of done (→ D1/D18)

**"Done" = an agent can swap Exa's MCP URL for ours and behave the same, at our scale, on our hardware — measured, not asserted.**

Because "replace Exa" is a spectrum, not a binary, here is the maturity ladder:

| Level | Meaning | Test |
|-------|---------|------|
| L0 | Same tool names exist | `tools/list` matches |
| L1 | Same inputs/outputs | schema diff = empty for the supported subset |
| L2 | Same semantics (modes, filters, contents, errors) | behavioral conformance suite |
| L3 | Same quality within tolerance | recall@N / answer eval on a shared query set |
| L4 | Same latency/throughput class | p50/p95 budget per tier on our hardware |
| L5 | Same scale trajectory (1M→1B, code unchanged) | scaling test at 2–3 sizes |

**"100% complete" = L5.** v1 architecture-complete = **L0–L2**; v1 releasable = **L0–L2 + L3 + L4 on the reference box**; L5 = scale proof, not v1. (D1, 2026-11-23.) **Release v1 = Gates 0–4 + the v1 subset of Gate 5, on the S3 reference profile. No 1–2B minimum. `deep` is out of the gates. L5 reports the size actually demonstrated. (D18, 2026-11-24.)**

**The core API comes first.** MCP is a thin adapter; `curl POST /search` must work before any MCP code exists.

**Layer model (D18):** **C0** = S1 + S2 contract; **C1** = Gate 0 on the toy index (after S2, without waiting for S3–S9); **C2** = S3–S6 iterations (measure → decide → version, each with an exit criterion); **C3** = S7–S9. Feedback (S8→S1) = versioned contract revisions, not blocking dependencies.

**Six acceptance gates (the DoD):**

0. **Core API gate** — `POST /search` **and** `POST /contents` work via `curl`/CLI with no MCP in the path; results are correct and the response shape is stable. This is the "simply uses the API" step.
1. **Drop-in gate** — an unmodified Exa-using agent works by changing only the URL. Same tool names, input schemas, output fields, transports (HTTP MCP + stdio), auth (optional key), error envelope. *(Confirmed for the keyless MCP surface.)*
2. **Behavior gate** — v1 = keyless MCP + API exactly (modes `lite`/`auto`, contents text/highlights, errors). **Plus keyed mode:** API key issuance, secure storage, rotation, revocation, rate limits, bans, user management, and the database behind them.
3. **Quality gate** — recall@N / nDCG within a pre-registered tolerance on the **S3 reference corpus** (no fixed minimum); coverage vs Exa reported **separately** from ranking quality.
4. **Performance gate** — **p50/p90/p95/p99 per tier** (lite/auto; `deep` out of v1) within budget on the target hardware; throughput (RPM/QPS); RAM/VRAM utilization; fits the envelope.
5. **Scale & ops gate** — 1M→10B by config/placement only; **byte-exact idempotence**; reproducible with provenance; observable; CI/CD; predictable failure.

**Cross-cutting pillars (apply to every gate):**

- **P0 Agent governance** — `CLAUDE.md` ↔ `AGENTS.md`, versioned; every task maps to a pillar; the plan/spec references the pillars; no work outside them without an ADR; anti-drift checks (§1.6).
- **P1 Security** — secure development; API key generation/storage/rotation/revocation; auth; rate limits; bans; user management; input validation; path containment; redaction; dependency/supply chain; secrets.
- **P2 Observability** — structured logs, metrics, traces per stage, per-tier QPS/latency, resource usage. The "predictable failure" requirement depends on it.
- **P3 Resource observability** — GPU-seconds per request, VRAM/RAM/CPU utilization, throughput; dollars secondary. Capacity planning, not billing.

**Hardware-agnostic scaling** — the architecture must run on a 5090 (32 GB), RTX Pro 6000 (96 GB), B200 (180 GB), B300 (288 GB), or a multi-node rack; scale by adding hardware + re-partitioning, never by code changes. The memory budget is an adaptive parameter. **v1 measurement is pinned to the D36 profile only** (1× RTX Pro 6000); any other GPU is a new profile and a new decision (D62).

**What to pin first:** the **drop-in gate**, because it is the literal definition and it forces the contract (S2) to become real. The first *action* is a measurement: capture the real Exa MCP `tools/list` + OpenAPI schema + a corpus of real agent queries, so the contract is evidence, not guesswork.

**A caution on "same speeds/latency":** Exa's numbers come from 144 H200s and a 100B index. We can match *per-tier latency budgets* on our hardware, not Exa's absolute numbers. So the performance gate is "within budget on our envelope," not "equal to Exa's ms."

**Terminology:** `tier` = search tier (`lite`/`auto`/`deep`); `palier` = corpus tier (T0/T1/T2); **pool** = work type (encode, search, contents). Do not use "tier" for corpus size or pools.

### 1.1.1 Throughput rules (D64)

**Offline (build):** options = token budget per batch, length sort, precision, model size; measure stable passages/s, GPU utilization, VRAM peak, padding rate on T0; project `T1_time = N_docs(T1) × r ÷ throughput × (1 + margin)`; criterion `≤ budget_embeddings`; default = length sort on, largest token budget under 85–90% VRAM without OOM; if fail: batching → fp8 → smaller model → tiers.

**Online (serving):** options = max micro-batch, max wait (few ms), workers; measure p50/p95 encode latency and QPS at saturation; criterion p95 encode ≤ its share of D15/D16 at target QPS; default = short wait, small micro-batches.

**Open before freeze:** all closed — build budget (D65), latency split (D66), GPU sharing (D68), BM25-only fallback (D69); `503` in S2 (D9/D11, D68).

### 1.1.2 Latency split (D66)

**Gate 4 = end-to-end p95 per tier only.** Stage budgets are diagnostic, not gates.

| Stage | `lite` (p95 600 ms) | `auto` (p95 2 500 ms) |
|---|---|---|
| Overhead (auth, quota, network, serialization) | 50 | 50 |
| Query embedding | 50 | 50 |
| BM25 | 50 | 80 |
| ANN | 100 | 150 |
| Fusion | 10 | 20 |
| Rerank | 0 | 800 |
| Contents (store read, incl. highlights) | 150 | 400 |
| ↳ Store read (within Contents) | 50 | 100 |
| ↳ Highlights (within Contents, D84/R2) | 100 | 300 |
| Margin (queue, dispatch) | 190 | 950 |

- Measure on D36 **without a build running**; `/search` with contents; `/contents` separately.
- **Reranker filter:** p95 > 800 ms on D36 → excluded, unless a new decision.
- Query encoder precision = build precision (or validated under D63).
- **Deep:** out of D66; budget defined with the plan/synthesis LLM.

### 1.1.3 Resource sharing (D68)

- **v1:** exclusion — build and serving never run simultaneously on D36 (GPU, VRAM, CPU).
- **Rebuild:** maintenance window; API 503 + `Retry-After`; atomic generation switch (D45).
- **Takedown:** serving filter if possible, no rebuild.
- **Gates:** no measurement with a build running.
- **CPU build:** extraction + BM25 only; embeddings on GPU.
- **GPU sharing/MIG:** later, only if maintenance windows become unacceptable; new decision with caps + D66 re-measure.
- **Multi-GPU:** LATER (dedicated pools).
- **Disk:** two generations coexist during rebuild → 500 GB split.

### 1.2 Additive extensibility (the anti-rewrite rule)

**Rule:** new endpoints are **thin routes over shared services**, never new pipelines. If an endpoint needs a capability that does not exist, we add a *service behind an interface* — we do not fork the API.

**Shared services (define the interfaces now; implement only what v1 needs):**

| Service | Interface (sketch) | Used by |
|---------|--------------------|---------|
| Query understanding | `understand(query, context) -> {normalized, expansions, intent, filters}` | all search endpoints |
| Retriever | `search(query, filters, k)`; `search_by_vector(vec, filters, k)`; `search_by_url(url, k)` | /search, /findSimilar, deep, agent |
| Reranker | `rerank(query, candidates, budget) -> ranked` | /search, deep, agent |
| Contents provider | `get(target, options) -> {text, highlights, summary}` | /contents, /search contents, agent |
| Synthesizer | `answer(query, evidence, schema) -> {text, citations}` | /answer, deep, outputSchema, websets |
| Filter | `apply(candidates, {domains, dates, category}) -> candidates` | all |
| Cache | `get/set` for queries, embeddings, contents | all |
| Telemetry | `trace(request_id, stage, timing, provenance)` | all |
| Index backend | `search`, `add`, `delete`, `stats` | retriever |
| Embedder / Reranker / Generator | model seams | services |

**Endpoint = route + composition:**

| Endpoint | Composition |
|----------|-------------|
| `/search` | understand → retrieve → filter → rerank → optional contents → optional synthesize |
| `/contents` | resolve → contents.get |
| `/answer` | understand → retrieve → rerank → synthesize |
| `/findSimilar` | resolve url → search_by_vector → rerank |
| `/context` | understand → code-retrieve → rerank → contents |
| `deep*` | plan → multi-round (retrieve + rerank) → synthesize |
| Agent | orchestrate (search + contents + synthesize) + run store |
| Monitors | schedule → search → webhook |
| Websets | search → synthesize(schema) → dataset store |

**Consequence:** when `/answer` arrives, we add a `Synthesizer` implementation and a route. The API, retriever, contents, filters, and telemetry are unchanged. That is the test for "additive": a new endpoint should touch **one new service + one route**, not the core.

### 1.3 v1 service interfaces (concrete — first pass, superseded by §1.3.1)

> **Superseded (v2):** this first pass is kept for history. The v2 design — single `Hit`, `Passage` vs `Contents`, async/batch protocols, tier-as-pipeline, `Deadline`, `Tracer`, Pydantic only in `api` — is in **§1.3.1** and `docs/sketches/v1_interfaces.py`. Build against v2.

**Dependency direction (enforced; superseded by D96 — `entrypoints → bootstrap → adapters → application → ports → domain`):** `domain ← services (protocols) ← api (routes) ← transport (http / mcp)`. The core must never import the transport.

**Immutable domain types** (`exa/domain.py`, no I/O):

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias
import numpy as np

DocId: TypeAlias = str          # content-addressed id
Url: TypeAlias = str
Vec: TypeAlias = np.ndarray     # shape (dim,), float32

@dataclass(frozen=True, slots=True)
class Candidate:
    doc_id: DocId
    score: float

@dataclass(frozen=True, slots=True)
class Ranked:
    doc_id: DocId
    score: float
    rank: int

@dataclass(frozen=True, slots=True)
class Filters:
    include_domains: tuple[str, ...] = ()
    exclude_domains: tuple[str, ...] = ()
    start_published: datetime | None = None
    end_published: datetime | None = None
    category: str | None = None

@dataclass(frozen=True, slots=True)
class Passage:
    doc_id: DocId
    text: str
    score: float

@dataclass(frozen=True, slots=True)
class Contents:
    doc_id: DocId
    url: Url
    title: str
    text: str | None = None
    highlights: tuple[str, ...] = ()
    summary: str | None = None
    published_at: datetime | None = None
    author: str | None = None
```

**Service protocols** (`exa/services.py`, interfaces only):

```python
from typing import Protocol, Sequence
from .domain import Candidate, Contents, DocId, Filters, Passage, Ranked, Url, Vec

class Embedder(Protocol):
    def encode_queries(self, texts: Sequence[str]) -> np.ndarray: ...
    def encode_docs(self, texts: Sequence[str]) -> np.ndarray: ...

class Retriever(Protocol):
    def search(self, query: str, filters: Filters, k: int) -> list[Candidate]: ...
    def search_by_vector(self, vec: Vec, filters: Filters, k: int) -> list[Candidate]: ...
    def search_by_url(self, url: Url, k: int) -> list[Candidate]: ...

class Reranker(Protocol):
    def rerank(self, query: str, candidates: Sequence[Candidate], budget_ms: float) -> list[Ranked]: ...

class ContentsProvider(Protocol):
    def get(self, target: Url | DocId, options: ContentsOptions) -> Contents: ...
    def get_many(self, targets: Sequence[Url | DocId], options: ContentsOptions) -> list[Contents]: ...

class Synthesizer(Protocol):
    def answer(self, query: str, evidence: Sequence[Passage], schema: JsonSchema | None) -> Answer: ...

class QueryUnderstanding(Protocol):
    def understand(self, query: str, context: QueryContext | None) -> ParsedQuery: ...
```

**API boundary models** (`exa/api/models.py`, Pydantic — validation + OpenAPI):

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class ContentsOptions(BaseModel):
    text: bool | TextOptions = False
    highlights: bool | HighlightOptions = False
    summary: bool | SummaryOptions = False
    max_age_hours: int | None = None

class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    type: Literal["lite", "auto"] = "auto"
    num_results: int = Field(default=10, ge=1, le=100)
    include_domains: list[str] | None = Field(default=None, max_length=1200)
    exclude_domains: list[str] | None = Field(default=None, max_length=1200)
    start_published_date: datetime | None = None
    end_published_date: datetime | None = None
    category: str | None = None
    contents: ContentsOptions | None = None
    output_schema: dict | None = None

class SearchResult(BaseModel):
    title: str
    url: str
    published_date: datetime | None = None
    author: str | None = None
    text: str | None = None
    highlights: list[str] | None = None
    summary: str | None = None
    score: float | None = None

class SearchResponse(BaseModel):
    request_id: str
    results: list[SearchResult]
    search_time_ms: float
    warnings: list[str] = Field(default_factory=list)
    notices: list[str] = Field(default_factory=list)
```

**Route = thin composition** (`exa/api/search.py` — no retrieval logic here):

```python
class SearchService:
    def __init__(self, retriever: Retriever, reranker: Reranker,
                 contents: ContentsProvider, synth: Synthesizer | None):
        self._retriever = retriever
        self._reranker = reranker
        self._contents = contents
        self._synth = synth

    def search(self, req: SearchRequest) -> SearchResponse:
        filters = _to_filters(req)
        candidates = self._retriever.search(req.query, filters, k=req.num_results * 4)
        ranked = self._reranker.rerank(req.query, candidates, budget_ms=_budget(req))
        results = [self._to_result(r) for r in ranked[: req.num_results]]
        return SearchResponse(request_id=new_id(), results=results, search_time_ms=_elapsed())
```

**The rule:** a route imports interfaces and domain types only. If it needs a new capability, add a protocol + one implementation; do not add logic to the route.

### 1.3.1 v2 design (after review)

**Review corrections (all accepted):**

1. **One `Hit` type, not `Candidate` + `Ranked`.** A `Hit` is a `Passage` plus an immutable `scores: Mapping[str, float]` keyed by stage (`"bm25"`, `"dense"`, `"rrf"`, `"rerank"`). Stages return new `Hit`s via `with_score()`. The pipeline becomes a sequence of pure transforms, and per-stage contribution is visible in the response.
2. **`Passage` vs `Contents`:** `Passage` = an indexed chunk of a document (`chunk_id`, `doc_id`, `char_start/end`, `index_version`); `Contents` = fetched text/highlights for a doc/URL. Retrieval operates on passages; the response maps passages back to documents.
3. **Async + batch from day one:** `Embedder.embed(texts)`, `Retriever.search(RetrievalQuery, Deadline)`, `ContentsProvider.get(doc_ids, ...)`, `Synthesizer.synthesize(...)`. Batching is a GPU requirement; retrofitting it changes every signature. **Async is for I/O concurrency only** — CPU/GPU work (embed, ANN, rerank) runs in the Rust extension or a worker process, never on the event loop.
4. **`Filters` semantics:** pre-retrieval constraints; every `Retriever` must apply them fully or raise `UnsupportedFilter`. Silent dropping is a bug. `lite` rejects unsupported filters with 400. **(superseded by D70/D99(4): lite and auto share the same filters; unsupported → 400 `unsupported_field` + `filter`+`tier`)**
5. **Tier = pipeline selection:** `TierPlan` selects which stages run (`expand`, `rerank`, `synthesize`); `SearchPipeline.run(query, deadline)` composes the services. The route calls `pipeline.run(...)`, nothing else.
6. **Synthesizer failure contract:** endpoint-specific — `/search` with `outputSchema` degrades (hits + `degraded=("synthesize",)`); `/answer` fails (no answer is the product).
7. **Deadlines & cancellation:** a `Deadline` (injectable clock) is threaded through every stage; a stage is skipped when time runs out, recorded in `degraded`.
8. **Pydantic only in `api`:** domain types stay frozen dataclasses; map to/from Pydantic at the boundary.
9. **Observability as a protocol:** `Tracer.record(stage, seconds, tier, ok)`; per-stage latency and QPS per tier.
10. **Idempotent `doc_id`s + versioned indexes:** `chunk_id`/`doc_id` are content-addressed; `index_version` on `Passage` and `SearchResult`.

**v2.1 corrections (second review — the two that fail silently):**

1. **Cancellation must reach CPU/GPU work.** Async deadlines only cancel the awaiting task; the thread/worker keeps burning. Fix: an **absolute monotonic** `Deadline.expires_at` (not a remaining duration) that workers check cooperatively between batches; a **bounded queue** in front of each worker pool with a fast **503** when full (admission control); and a **dequeue-time check** — if the deadline has passed, skip the item. *(v2.2 refines: convert the gateway deadline at ingress; if workers may leave the host, pass a remaining budget.)*
2. **No CPU-bound call on the event loop, ever.** A Rust call from `async def` still blocks unless it releases the GIL (`py.allow_threads` in PyO3) **and** is called via `asyncio.to_thread`/executor or exposes its own future. The loop thread only awaits; all CPU/GPU work runs in a worker.
3. **Pin `index_version` per request.** Resolve the version once at `run` start and thread it through; `Passage.index_version` must match. Otherwise an index swap mid-request returns IDs from version A and contents from version B — wrong text, no error.
4. **`needs_vector` is a second source of truth.** Derive it from the tier's stages, or validate every `TierPlan` against retriever capabilities at startup. (Recommendation: derive.)

**Other checks folded in:**
- `Hit.scores`: use `MappingProxyType` (done) and an enum/`Literal` for stage keys, not free strings.
- **Score comparability:** scores from different stages are not comparable (cosine vs BM25 vs reranker logit). Fusion must use **ranks** (RRF), never raw scores.
- **Passage vs Contents:** decide which stage fetches text and for how many hits; a reranker that needs text may force a fetch of all N candidates. Define fetch-failure policy (drop / degrade / fail).
- **Batch protocols:** specify max batch size, per-item vs whole-batch failure, and how the deadline applies when a batch is split.
- **Tracer across processes:** the correlation ID must travel with the job, or spans are orphaned.

**v2.2 corrections (third review — design vs verification):**

> Status: the sketch is a **design artifact**, not implementation. "Captured" means written down, not tested. The tests below are specified but not written.

1. **Deadline boundary.** `time.monotonic()` is only comparable within a process/host; do not rely on it across machines. Convert the upstream gateway/wall-clock deadline to a monotonic value **once at ingress**. If workers may run off-host, pass a **remaining budget** with each job and subtract queue time at dequeue.
2. **Index-version lifecycle.** Pinning is incomplete without a rule: the old version must stay readable until in-flight requests drain (refcount/grace period), **or** the swap is a deployment-level drain. The content store must be keyed by `(index_version, doc_id)` or content-addressed, or the "IDs from A, text from B" hole reopens at fetch time. On mismatch: **fail explicitly**, never silently.
3. **Dedicated bounded executor.** `asyncio.to_thread` uses the shared default executor; it does not give you the bounded queue. Use a **dedicated, bounded executor per tier** (or worker pool) so "bounded queue + fast 503" is real. Threads can't be cancelled; cooperative checks only help if batches are small. **Define the max size of a single uninterruptible call** (max batch, max k) so a deadline can interrupt between batches.
4. **Per-tier isolation.** `lite` and heavy tiers must not share one unbounded pool, or a burst of `deep` starves `lite`. 503 (queue full, with `Retry-After`) ≠ 504 (deadline exceeded).
5. **Propagate the job context.** `trace_id`, deadline/budget, and `index_version` travel in the **job payload** to the worker; worker spans flow back. `Tracer.record(..., trace_id)` alone is only the local half.
6. **Verification, not documentation.** Each rule becomes a test (see §1.3.2).

**Where I push back:**
- **Refcount/grace period for v1:** the invariant "index is immutable while serving; a swap is a drained deployment" is enough for v1. Build versioned content keys + fail-fast now; add refcounting only if we support live swaps. (The content-store keying is non-negotiable; the refcount is deferrable.)
- **Separate queues:** the requirement is **no starvation of lite**. A per-tier limit alone is not enough: if tiers share one FIFO GPU worker, `lite` still waits behind a heavy batch. The actual requirement is **bounded waiters + priority or reserved capacity**, not just a semaphore. Separate queues are one implementation.
- **"Flaws 1 and 3 are the hardest":** I wouldn't rank them. All four (deadline, index lifecycle, executor, isolation) are cheap now and expensive later; treat them as a set.

### 1.3.2 Verification contract (tests, not docs)

These are **required tests**, not documentation:

| Test | Asserts |
|------|---------|
| `test_gate0_core_api` | `curl POST /search` (lite+auto) + `/contents` return 200 with the v1 shape, no MCP; invalid input → 400 `invalid_request` |
| `test_cancel_mid_rerank` | cancelling a request stops the worker before the next batch |
| `test_index_swap_consistency` | swapping the index mid-request yields a consistent response or an explicit error |
| `test_loop_not_blocked` | a heartbeat task runs during `pipeline.run` (no CPU work on the loop) |
| `test_tier_plan_consistency` | every `TierPlan` is valid for the wired retrievers at startup |
| `test_deadline_between_batches` | a stage checks the deadline between batches and skips when expired |
| `test_queue_full_503` | a full bounded queue returns 503 + `Retry-After` |
| `test_versioned_content_key` | content fetched for a hit uses the pinned `index_version` |

### 1.3.3 Gate 0 acceptance (D12)

| Test | Criterion |
|------|-----------|
| `POST /search` lite + auto | Two HTTP calls, no auth, deterministic fixture. Each: 200, JSON, non-empty `requestId`, numeric non-negative `searchTime`, non-empty `results[]` with `title`+`url`; an expected URL present; `len(results) <= numResults`; no order/relevance threshold. |
| `POST /contents` on a result | Take the expected URL **from the `/search` response**; request `text: true` and `highlights: true`. Verify 200, same URL, identifiable fixture text, `highlights: string[]`; if the fixture produces an excerpt, it is non-empty. |
| Invalid inputs | Malformed JSON; valid JSON with an out-of-v1 `type`; `urls` not an array. Expect 400, `tag: "invalid_request"`, D11 envelope, same id in `requestId` and `X-Request-Id`. Do not freeze the message text. |
| MCP independence | Start the HTTP server **without initializing MCP**; run tests against it. `import-linter` is a complement, not a replacement. |
| `Content-Type` | All requests use `-H 'Content-Type: application/json'`; the test must not mix body validation with content-type handling. |
| `type` routing | If we want to lock routing at Gate 0, assert the selected plan for `lite` vs `auto`; do **not** require different results on the toy index. |
| Unknown URLs | No global 404 in Gate 0. Capture in S2: a mixed batch (known + unknown) and an all-unknown batch; decide per-URL status semantics. |
| Keyless | Specify "test instance configured keyless" — Exa's HTTP API requires a key; keyless is our replica's choice. |

**Revised layout (superseded by D95/D96 — see §1.3.1/D95):**

```
search/
  domain/    types.py  fusion.py  deadline.py
  services/  ports.py   pipeline.py
  adapters/  index/ store/ embed/ rerank/ synth/ workers/
  api/       models.py  routes.py
  transport/ http.py    mcp.py
```

Import rule: `domain` (stdlib only) ← `services` ← `api` ← `transport`. `adapters` implement the service ports; `workers/` is an adapter used by services, not transport. Enforce with `import-linter`.

**Code sketch:** `docs/sketches/v1_interfaces.py` — pure Python, no I/O, unit-testable without a GPU or network. It fixes the rough edges in the first pass: `needs_vector` replaces the name check, `output_schema` comes from the request, and per-variant retrieval is `asyncio.gather`'d.

**Decisions confirmed → D99 (with recommendation; D99 adds: `/answer` LATER, clamp + effective-value header, `unsupported_field`+`filter`+`tier`, `X-Index-Version` + 409 `index_version_mismatch`):**

| # | Decision | Recommendation |
|---|----------|----------------|
| 1 | Synthesis failure | **Endpoint-specific:** `/search` degrades with machine-readable `degraded: true` + reasons; `/answer` fails, distinguishing timeout vs error; optionally include retrieved hits alongside the error. |
| 2 | Deadline | **Per-tier only for v1.** Overrides may only **lower** the budget; honor an upstream gateway deadline if present. |
| 3 | `needs_vector` | **Derive from the tier's stages** (or validate all `TierPlan`s at startup). |
| 4 | `lite` unsupported filters | **400**, naming the filter and the tier; expose per-tier capabilities. Approximate filters (post-filter returning < k) → **degradation**, not silence. **(superseded by D70/D99(4))** |
| 5 | `index_version` | **Pinned per request**; content store keyed by `(index_version, doc_id)` or content-addressed; old version readable until drain (or deployment-level drain); mismatch → explicit error. Refcount deferrable for v1. |

### 1.4 Development rules (frozen → D102)

**Structure**
- **≤ 500 lines per file** (hard); > 400 lines → split by responsibility.
- **≤ 50 lines per function; ≤ 3 nesting levels; cyclomatic complexity ≤ 10.**
- One responsibility per module; implementation private; public API explicit.
- No circular imports; dependency direction: `domain ← services ← api ← transport` (superseded by D96).
- No mutable global state; config is immutable and injected at startup.

**Typing**
- Full type hints on public functions; `mypy --strict` on `src/<pkg>/`.
- No `Any` outside FFI/JSON boundaries.
- Pydantic at the API boundary; frozen dataclasses internally.
- Every public function documents its invariants.

**Errors & robustness (the endpoint is the product)**
- Every endpoint validates input at the boundary (Pydantic), returns the standard error envelope, never leaks internals.
- Every endpoint has a timeout budget and degrades explicitly.
- No bare `except Exception` except at process boundaries, with a written policy.
- Typed errors; fail fast at startup (config/index/model); never silently return wrong results.
- Retries with backoff + jitter on transient I/O; no retry on 4xx.

**Pipelines**
- Every stage idempotent + resumable; state derived from artifacts.
- Atomic writes; manifests with provenance; no stale artifacts.
- One knob per experiment; record it in the run ledger.

**Testing**
- Every module has tests; core coverage ≥ 80%.
- Tier-0 tests < 10s, no network/GPU.
- Contract tests for every endpoint (schema + behavior).
- Golden tests for the retrieval pipeline; property tests for parsers/filters where cheap.

**Observability & security**
- Structured JSON logs, no `print`.
- Metrics at every stage boundary; trace per request.
- Input validation at every boundary; path containment; no `eval`/`exec`/`pickle`.
- Constant-time auth; rate limits; secret redaction.

**Dependencies**
- Pin versions; commit the lockfile.
- Justify each new dependency; prefer stdlib.
- No vendor SDK in the core; adapters only.

**Process**
- Small PRs; conventional commits; CI green before merge.
- ADR for significant decisions; update this doc.
- No dead code; delete unused.
- Measure before optimizing.

**Enforcement**
- `ruff` (line length 100, complexity ≤ 10, import/bug/simplify rules), `mypy`, `pytest`, `cargo fmt` + `clippy`, `pre-commit`, CI.
- One command (`make check`) runs all; CI blocks on failure.

### 1.4.1 Additional rules (review pass)

**Dependencies & supply chain**
- Lockfiles committed; versions pinned; new dependencies need a short justification.
- Vulnerability audits in CI (`pip-audit`, `cargo audit`, `npm audit`); SBOM for releases if we ship containers.
- Container hygiene: pinned base-image digests, non-root user, no secrets in layers.

**Secrets**
- Secret scanner (`gitleaks` or `detect-secrets`) in pre-commit and CI.
- Config loaded from env into a typed settings object, validated at startup (fail fast).

**Architecture**
- **Functional core, imperative shell:** pure logic in the core; all I/O (network, disk, clock, randomness) at the edges and injected. This is what makes Tier-0 <10s realistic.
- Import-layer rules enforced by `import-linter` (not just no-cycles: `core` must not import `api`).
- Ban direct `datetime.now()` and unseeded `random` in core code; inject the clock and seed for reproducibility.

**Testing**
- Mutation testing (`mutmut`) on the core — 80% coverage can hide tests that assert nothing.
- Property-based tests (`hypothesis`) for parsers, serializers, pipeline steps.
- Define "core" as an explicit list of paths so the 80% gate is unambiguous.
- Define tiers: Tier-0 = unit tests, no I/O; slower tiers have their own budgets.

**Endpoints**
- Request size limits **and** rate limiting, not just timeouts (a timeout doesn't stop a 2 GB body being read).
- Correlation IDs propagated through logs, traces, and the error envelope.
- Error envelope follows **RFC 9457 (Problem Details)** so clients can rely on its shape. **(superseded by D11 — Exa envelope `{requestId,error,tag}`, not RFC 9457)**
- Versioned API contracts, so contract tests have something stable to check.

**Pipelines**
- Schema versioning for manifests, so old outputs stay readable.
- Every pipeline has a dry-run mode and a documented rollback path.
- Atomic writes: temp file → `fsync` → `os.replace` (write it down so nobody regresses to `open(..., "w")`).

**Process**
- ADR for any rule exception, so exceptions are visible and reviewable.
- PR size guideline (< ~400 changed lines) + a short review checklist mirroring these rules.
- Conventional commits (enables changelog generation).

**Enforcement mapping**
- Complexity: ruff `C901`, `PLR0911`, `PLR0912`, `PLR0915`.
- Nesting: pylint `R1702` (`too-many-nested-blocks`) — ruff has no nesting-depth rule.
- File/function length: a ~20-line CI script (no mainstream linter enforces it).
- Security: ruff `S` (bandit-style) + `B` (bugbear).
- Rust: clippy `too_many_lines` (pedantic, opt-in).

**Encoding:** these rules go into `AGENTS.md` (and `CLAUDE.md` points at it) so both humans and agents follow the same defaults.

> These are starting defaults. We adjust thresholds after the first few modules, but the default exists so nobody has to relitigate it per PR.

### 1.5 Quality gate — decision-rule form (S1, Gate 3)

**The form is fixed now; constants are set on the dev split or by product reasoning — never after seeing test results.** The test split is touched **once per release candidate**; repeated gating turns it into a second dev set.

**Measurement harness exception:** the eval harness (brute-force recall, metric computation, load generator) is **measurement tooling**, not product code. It may be built before the design is final; product code may not. Boundary: the harness may import existing code, but **nothing in `search/` may import the harness**; the harness still runs under the same `make check`.

**(a) ANN operating point — a regression pin, not a quality gate.**
- **First measurement:** ANN recall vs brute force. Until it exists, `0.359` cannot be classified as an index problem or an embedding/ranking problem.
- **Sweep `nprobe` only** on the current Rust IVF; keep `nlist`, codes, centroids, corpus, queries fixed. `ef_search` only applies to an HNSW backend. **Replaced by D82** (R0/R1 scan the whole index; no IVF/nprobe).
- **Exhaustive reference:** score **all** codes with the **same function** as the ANN stage. If the query stays float and the score is via LUT, do not substitute Hamming distance. Freeze the tie-break rule at the top-k threshold.
- **Measure at `k=10` and at the production depth N** (dense branch depth before fusion). Report recall at both depths with p50/p95, under fixed and recorded conditions (hardware, threads, concurrency, cache, timing scope).
- **Selection rule (not "the knee"):** on dev, pick the best recall at the production depth among points that meet the **p95 sub-budget of the ANN stage**, with a stated tie-break. If a floor is also set and no point satisfies both, record "no admissible point." Pin the point **and the measurement conditions**.
- The budget blocks selection, not the first curve. A curve at 2.58M does not validate a larger `nprobe` at larger scale or another N.
- This is a **regression pin**, not evidence of quality. It depends on S3's latency budget.

**(a2) Quantization quality — three lists, not two ambiguous metrics.**

For each query, on the **same passages and same starting embeddings**:
- **F** — exhaustive **float** top-N (same dimension, reference preprocessing).
- **Q** — exhaustive **quantized** top-N (actual binary/PQ score).
- **A** — quantized top-N returned by the **ANN** at the measured point.
- `Q vs F` isolates quantization; `A vs Q` measures index approximation; `A vs F` measures what the dense stage delivers. **The gaps do not add up.**
- If comparing float 1024-dim to binary 256-dim, that also measures truncation — make it a **separate experiment**. Start with **binary vs float**; PQ can wait.
- `N` = dense branch depth **before fusion**, not necessarily the reranker candidate count after BM25/RRF/dedup.
- "Recall@10 after rerank" must name its reference: overlap with float top-10 = vector diagnostic; recall on human/calibrated judgments = search quality (3g). Otherwise `0.359` gets reread as ANN recall, when it is known-target recall.

**(b1) Coverage — three measures, same denominator.**
- Denominator: the relevant results of the Exa `auto` top-10 on the judged version (if the snapshot is authorized). Fix the relevance threshold before the run.
- "Passage-level" = the **useful evidence survived**, not that any chunk exists under the URL. The Exa pool is a reference population, not web coverage or a demonstrated upper bound.
- **1. URL in source corpus** — canonical match, versioned rules; distinguish confirmed from ambiguous (don't auto-merge http/https, trailing slash, params).
- **2. Relevant evidence in local text** — verify a supporting passage from the judged version (or equivalent per a fixed rule); an old version under the same URL is not enough.
- **3. Evidence in an actually indexed passage** — verify index-snapshot membership **without going through the search engine**. If indexed but never retrieved → retrieval/ranking problem, not coverage.
- Aggregate: **macro per query + micro over results**, with denominators, queries with no judged relevant result, and indeterminate cases. Break down losses: **absent from source / different version / extraction or chunking / not indexed**.
- **Order:** run F/Q/A on the existing corpus + dev **without waiting for S3 or Exa**; choose 3d after the budget is fixed; define 3f categories now; publish Exa coverage only once the snapshot is authorized and judged.

**(b2) Ranking quality.**
- Frozen, versioned pooled judgments (below), calibrated judge.
- **Primary:** paired difference `auto − Exa auto` on the **independent cohort**; **two-sided 95% CI**; pass if the lower bound ≥ `−δ`. Resample queries (or intent clusters if variants remain), keeping system scores paired. Fix the method, seed, and domain weighting.
- **`δ = 0.05` is a candidate, not a result** — a mean loss of 0.05 nDCG points on a 0–1 scale, not "5% less quality." Inspect top-3 regressions on dev; size the test on the independent cohort; **do not relax `δ`** to pass.
- **Freeze the score computation:** same pool + versioned judgments for all compared runs; explicit 0–3 gains; a rule for queries with no judged relevant doc. Gate-deciding runs require `judged@10 = 100%` of **returned** results. Call it **`recall@10 on the judged pool`**, not recall on the web.
- **Relative floor:** paired bootstrap of `(auto − BM25)`; pass if the lower bound is **> 0**. BM25 runs on our own index, frozen tokenizer/`k1`/`b`, in the pool. This is a **relative** floor, not an absolute one.
- **`lite`:** report `lite − BM25` and `lite − auto`; no `> 0` gate unless an explicit product requirement exists. If gated, state "**BM25 gate, no Exa gate**."
- **`success@3` (diagnostic):** URL = ≥1 relevant page in the top 3; highlight = ≥1 displayed excerpt in the top 3 that alone provides useful evidence for the objective. Missing highlight = **N/A** for BM25 (no excerpt generation), **failure** if the run is supposed to produce one.
- **Exa blocked:** `BM25 validated` and `Exa comparison blocked` are distinct states. Filters and `deep` stay outside this gate; OpenCode is a secondary cohort.
- **Highlights are judged in context**, with the same objective visible to the judge.

**Quality gate scope.** The primary gate applies to `auto` (the MCP default): **non-inferiority vs Exa + superiority vs BM25**. `lite` is **reported + BM25-floored** (relative), no Exa gate unless a product requirement says otherwise. Filters are HTTP-only; `deep` is later. The gate runs on the **independent primary cohort**. Constants (`δ`, `κ`) are fixed on dev before test.

**Objective ablation (diagnostic).** **Primary condition:** Exa and the replica receive `query + specific objective`; the reference BM25 receives `query` alone; all results are judged against the **same specific objective**. This is a valid between-products comparison, but the gain over BM25 alone does not prove the dense/reranker contribution. If that attribution matters, add a **BM25 `query + objective`** control on dev (frozen injection rule); do not replace the primary baseline after seeing scores. Ablation on dev: **three Exa conditions** (specific / generic / absent) on the same dev queries; the judge keeps the **same specific objective** in all three; common page-relevance pool; excerpts judged separately. Small dev → wide CIs; a null is not evidence.

**Judgment versioning.**
- **Freeze engine outputs first.** A new judgment version **never** triggers a new Exa search and never allows tuning the replica on the test.
- **Recompute all compared scores on the same version, from the frozen outputs** — replica, BM25, Exa (if authorized). A new relevant doc in the pool can change the nDCG denominator; rescore both releases on a common pool, don't subtract published v1/v2 scores.
- **Three change types:**
  - New results → **pool extension** (same protocol, reuse labels).
  - Model/prompt/grid change → **new protocol** (recalibrate, re-annotate the gate pool).
  - Query set change → **new benchmark version**.
- **Snapshot metadata:** hash of the query set, protocol, and label export; IDs of the outputs that fed the pool.
- **Keys:**
  - Page: `(task_id, canonical_url, hash_of_judged_text)`, `task_id` = query + **reference objective**.
  - Highlight: `(task_id, page_key, hash_of_displayed_excerpt)`.
  - In the ablation, the engine objective varies but the **reference objective is fixed**; the same page in the same version must not get three labels.
- **`judged@10`:** gate-deciding runs require **100% of returned top-10 results judged**; `<80%` is an exploratory alert, not a second threshold. Unjudged ≠ label 0; missing result ≠ unjudged. Report the returned count and queries with no results.
- **Test protection:** pool completion allowed **after candidate freeze and before scoring**, blind; no candidate changes after reading results.
- **Storage:** Postgres for working; official version = **immutable, hashed export**; human correction/arbitration → new snapshot with label provenance.

**Judge calibration.**
- Freeze judge model/version, prompt, temperature.
- Blind the judge to which system returned each result.
- Keep the judge model separate from any model used to generate queries or highlights (self-preference).
- **Two human annotators**, blind, with arbitration; separate the **prompt-tuning** examples from the **verification** examples.
- For the 0–3 ordinal scale, report **weighted κ** (specify the weights), the confusion matrix, and **serious errors (0↔3)**.
- On a small subset of queries where **the entire compared top-10 is human-judged**, verify the automatic judge does **not change the direction** of the gap between systems. A good global κ can mask bias that flips the gate.
- **Judge page and highlight separately** — don't reward a page because its excerpt is better.
- **Pool includes the top-10 of each run actually scored**, including `lite` if it must pass the BM25 floor.
- **Spot-check rule:** random + targeted (disagreements, single-system results) — not a flat 10%.
- **κ ≥ 0.6 is a provisional alert threshold, not a green light.**

**Golden set.**
- Start with **200 queries (100 dev + 100 test)**; the test split is provisional until a pilot measures the per-query SD. **The pilot runs on the dev split only.**
- **50/50 is a pilot weighting, not the final rule.** The two sources differ in **objective type** (generic vs specific), so do not mix their conclusions.
- **Primary population for the v1 gate: independent queries with specific objectives, written before any research.**
- **Secondary cohort: OpenCode traces with a generic objective** (realism check only).
- **Objective effect:** compare on the **same independent dev queries** — specific objective, generic objective, and (if 3i) absent field. A generic objective is neither the real objective nor absence.
- **Cross-source dedup:** cluster near-duplicates across **both** sources before the split.
- **Tags:** `source`, `objective_source`, `domain`, `intent`, `language`, `fresh`, `as_of`. `tier` is an **execution condition** — run `lite` and `auto` on the same queries to compare tiers.
- **Distribution:** recalculate after filtering the first query per session, privacy, and dedup. `79` is a **count**, not a percentage. Report strata sizes; if a stratum is too small, say so.
- **Every query carries an `objective`** — required by `web_search_exa`, and it drives highlights.
- **Judgments are keyed on canonical URL + the content hash of the text the judge saw**, not `doc_id`. Highlight judgments need their own key (highlight text + the objective it was judged under). Canonicalization rules are versioned.
- **Selection, fixed before any run:** random sample; cluster near-duplicates; hash the **cluster ID** for the dev/test split; check strata balance afterward.
- **Freeze:** queries, objectives, judgments (versioned), Exa snapshot (date, params, raw responses, fetched text), judge config.
- **Privacy:** scrub traces **before** they reach the judge LLM or Exa; check both providers' retention terms.

**Trace record (for capturing real calls):**

```json
{
  "ts": "2026-11-23T15:00:00Z",
  "source": "agent-trace | curated | synthetic",
  "tool": "web_search_exa | web_fetch_exa",
  "session_id": "...",
  "turn_index": 1,
  "query": "...",
  "objective": "...",
  "num_results": 10,
  "response_text": "...",
  "meta": {},
  "latency_ms": 182.7,
  "topic": "...",
  "fresh": false
}
```

**Capture paths (important):**
- OpenCode's `websearch` tool input is `{ query }` only, and the active provider is currently `parallel` (not Exa). Calls through it do **not** produce Exa `web_search_exa` traces and carry no `objective`.
- To capture real Exa calls with `objective`, log at the **Exa MCP layer** (the two tools). Direct keyless MCP calls work; the fixture set in `docs/fixtures/exa-mcp/` is the first sample.
- **Pilot first:** compute the per-query SD and CI; grow the test split only if the decision needs resolution smaller than the interval.

**Sample size.** At a success rate near 0.8: ±11 points at n=50, ±8 at n=100, ±4.5 at n=300. A paired comparison is tighter; if per-query nDCG differences have SD ≈ 0.25–0.3, the paired 95% interval is roughly ±0.05–0.06 (≈6 points). Treat that as an assumption until the pilot measures it.

**Anti-goals (blocking for v1):**
- **Integrity:** never silently serve a snapshot different from the one announced, or promise freshness we can't keep. An old but identified snapshot within the declared policy is OK; version B text with version A results is never OK.
- **Security:** anonymous access must never result from a config omission, auth failure, or invalid key. Keyless (D8) is explicit, limited, and distinct from authenticated mode. An invalid presented key is not "no key."
- **Promised compatibility:** no silent divergence on the promised subset. HTTP extensions or replica-specific error tags are OK if documented and tested — not proof of exact compatibility.
- **Reproducibility of evidence:** a number must be re-derivable from its manifest; a build must be reconstructible; **no release evidence depends on unauthorized data use** (OpenCode traces, Exa responses, third-party judge texts).
- **v1 recovery:** no failure may cause unexpected durable loss or improvised recovery. Single-node v1 is OK; a single-node assumption baked into contracts or the search path is not. Don't promise untested HA.
- **Idempotence:** canonical artifacts byte-exact in the declared profile; a re-run must not publish a partial state or reuse a stale artifact. A different run timestamp or shard placement is not an idempotence failure.
- **No gate by measurement shortcut:** no reusing the quality test to tune the candidate, no degraded results counted as complete success, no blocked Exa comparison presented as validated. Keep three states: **validated / failed / not demonstrated**.
- **No failure disguised as a valid result:** an empty 200 must not mask a lost required shard; an unsupported filter must not be ignored. A genuine "no results" remains a normal success.
- **Operability:** an operator can install, start, query, and restore the server from the docs.
- **Maintainability:** the failure is having to modify the search core to add a transport or change a backend, or introducing a distributed dependency without demonstrated need. Don't ban microservices/monolith by principle.
- **Cost:** don't claim an economic advantage without a comparison at equal quality, useful throughput, and scope. Cost is a diagnostic; self-hosting for autonomy/privacy can justify higher cost.
- **Scale:** changing scale requires a code change; hardcoded sizes; a 100M test presented as 10B proof.

**v1 failure is not failing to demonstrate 10B — it's claiming to have done it, or having to rewrite the core to test the next scale.**

### 1.6 Agent governance (P0)

**Goal:** agents (human or AI) follow the same rules, and the plan cannot drift.

- **`CLAUDE.md`** — **pointer/import to `AGENTS.md` only (D101)**; CI fails if it contains anything else.
- **`AGENTS.md`** — the agent contract: dev rules (§1.4), quality gates (§1.5), pillar mapping, anti-drift checklist, definition of done per task.
- **Pillar mapping** — every task/issue/PR names the pillar(s) it serves (P0–P3, S1–S9). No orphan work.
- **Plan discipline** — every milestone in `zenno/plans/` references the pillars and the gates; no milestone without a measurable DoD.
- **Anti-drift** — PR checklist: scope matches the pillar; no unrelated changes; tests/benchmarks updated; ADR for exceptions; file/complexity limits.
- **Definition of done per task** — code + tests + docs + observability + security checklist, as applicable.
- **Review** — a second agent/human checks the pillar mapping and the DoD before merge.
- **Owner + decision rule per item** — every open item names who decides and what evidence closes it. No item closes without both.

### 1.7 Gate 4 — Performance (D15)

**Principle:** a tier must meet its **latency, useful throughput, and resource budgets in the same run**, with the Gate 3 quality configuration. `deep` is out of v1 blocking criteria.

**4a — Latency (pilot targets, not release thresholds yet):**

| Tier | p50 | p95 | p99 | Useful throughput |
|------|-----|-----|-----|-------------------|
| `lite` | ≤ 300 ms | ≤ 600 ms | ≤ 1 s | ≥ 50 req/s |
| `auto` | ≤ 1.5 s | ≤ 2.5 s | ≤ 4 s | ≥ 10 req/s |

- The Exa baseline (n=10/tier, p95 = max observed, different queries, `numResults=5` + text/highlights) is a **reference, not a basis for release thresholds**.
- Report **p90**, but do not gate on it until a product requirement justifies it.
- **Primary scope:** end-to-end `/search` (client → last byte, queue wait + serialization included). Freeze `numResults`, `objective`, content options, cache state. For `auto`, use a representative MCP profile (specific objective + highlights).
- **Complementary scope:** `/contents` and MCP `search → fetch`, with batch size and text limit fixed. Measure at the pilot before deciding which block release.

**4b — Throughput (useful responses, not offered requests):**
- Report offered throughput, **successful complete responses**, 429, 503, timeouts, degraded responses. Fix an **error/degradation budget** before the test. A 200 that skipped rerank or required highlights is not a complete success.
- Use an **open arrival rate**; otherwise the generator slows with the server and masks saturation. Un-sent requests must be visible.
- **Capacity vs quotas:** separate the server capacity test from the quota test. A single keyless client/key cannot measure 50 QPS under D9; use multiple authorized test identities for production-limit validation. Don't confuse an expected 429 with a 503 saturation.
- **Isolation:** test `lite` and `auto` alone, then mixed load with `/contents`; add a scenario where `auto` saturates while `lite` stays at its target. Criterion = **"lite stays within its budget"**, not "two pools exist." Separately measured maxima are not assumed simultaneously achievable.

**4c — Resources (one reference box, one corpus, a measurable margin):**
- **One reference machine for v1**; other profiles measured without blocking release. Freeze GPU, CPU, RAM, storage, service placement, index snapshot. State **documents and passages** — "fits on a 5090" is meaningless without index size/structure. The 2.58M doc corpus is a starting point if reproducible; it does not validate another scale.
- **VRAM:** distinguish idle, startup peak, and peak under mixed load; note sampling interval and counters. **Allocated VRAM, GPU activity, and GPU-seconds/request are three different measures.** With batching, keep **aggregate GPU cost** in v1; don't attribute all batch time to each request.
- **RAM/CPU/disk:** separate service memory and file cache; track disk reads if content/index don't fit. Fix the memory margin **in GiB on the reference box**, from observed peaks + system reserve. "No OOM" is necessary but not sufficient if throughput collapses or the queue doesn't drain after a spike.

**Freeze now:** timed scopes, useful-throughput definition, isolated/mixed/saturation scenarios. **Confirm after the S3/4d pilot:** reference box + corpus, latency/throughput thresholds, error budget, memory margin. For 3d, the ANN p95 sub-budget must be verified **under target load**, not an isolated query.

**4d — Load test methodology (D16):**
- **Scenarios (release vs diagnostic):**
  - **Isolated `lite`, then `auto`** — each tier meets latency + useful throughput + errors + resources simultaneously.
  - **Mixed `lite + auto + /contents`** — freeze offered throughput **per route**, batch sizes, response sizes; do not sum isolated maxima into an obligation.
  - **Saturation → recovery** — keep `lite` at target; overload `auto` until real queue/admission pressure; return `auto` to nominal; verify `lite` holds **during** overload and `auto` recovers **within a fixed delay**, no restart. Expected `auto` 503s must not mask `lite` errors; 429s alone don't prove worker saturation.
  - **Cold / scale** — separate **cold start** (process, model, index) from **cold app cache on a ready server**; note OS cache state. 1M/10M/100M are study points, not v1 criteria.
- **Duration:** ramp-up → **~10 min plateau** → drain, with pre-declared windows. Thresholds on requests **launched during the plateau**, followed to response/timeout even if they finish during drain. Minimum observations per tier/route before p99; extend the plateau if needed; predefine a repetition rule; keep all runs.
- **Tooling:** **k6 `constant-arrival-rate`** (open, constant) for v1; Poisson/burst later. k6 schedules **iterations**, not HTTP requests — an iteration `search → fetch` measures path throughput, not per-route QPS.
- **Planned vs sent vs fully successful:** `dropped_iterations` is neither a 503 nor a timeout; it blocks declaring the target load met. Diagnose generator undersize vs VU exhaustion. Run the generator **outside the reference box**.
- **Freeze the request profile:** order/schedule per tier, repeat rate, warmup, content options, batch sizes, quotas, `index_version`. Use a load set **distinct from the quality set**.
- **Keep time series:** queue wait, useful throughput, errors, memory — a 10-min aggregate hides queue growth and drain time.
- **Cadence:** full suite at each RC on the reference config; short nightly at fixed load for regressions.

### 1.8 Gate 5 — Scale & ops (D17)

**Two commitments (D1):** v1 operational guarantees vs L5 scale proof. A 100M test doesn't validate 10B; L5 reporting doesn't excuse v1 from resuming a build, refusing an incoherent index, or returning to a healthy version.

| Block | v1 blocking | L5 |
|-------|-------------|-----|
| **5a** Scale | Same contract + search path with 1 then multiple local partitions on the same corpus; Gate 4 on the reference box | Real distributed deployment, new size points, repartition cost, node-loss behavior |
| **5b–5c** Artifacts/provenance | Deterministic build in a declared profile, resume without partial publication, published results recomputable | Same invariants on other profiles/placements, explicit equivalence criteria |
| **5d–5f** Ops | Useful telemetry, restorable release, targeted failure tests on the supported deployment | Node isolation, redundancy, failover, distributed recovery |

**5a — Scale invariance:**
- Contract: **same code revision + contracts**; only placement, resources, declared params change. 1→16 shards may need a rebuild — not a rewrite, but the **D82** index setting must be revalidated (for R1, revalidate `K_bin`).
- Distinguish **shard** (data partition), **replica** (copy), **node** (failure domain), **GPU** (execution resource).
- **Test A:** same corpus, 1 vs multiple shards; exact mode top-K reference with filters, ties, dedup, `/contents` on pinned version; ANN mode recall/ranking tolerance on dev; multi-passage doc dedup must not drop later candidates.
- **Test B:** growing corpus, real placement; report docs+passages, build throughput, disk, RAM/VRAM, fan-out, p95/p99; 1B simulated exercises shard count/late responses/merge, not real footprint/recall; sample **queries** scored exactly on the full available corpus — don't sample docs.
- Partitioning: stable hash of **page id** for the invariance test; keep a page's passages together; separate shard placement from index routing (D82); fix merge rules **per branch** before global RRF; BM25 needs global stats for 1/N equivalence.
- Record the index setting (D82), local depth, partition in provenance. In-memory rate limits (D9) don't validate multi-replica quotas.

**5b — Byte-exact:**
- Two objects: **canonical artifact manifest** (files + hashes) and **run manifest** (date, durations, host, run id). Same logical build → same artifact manifest; run manifest differs.
- **Byte-exact profile v1:** same inputs, resolved config, format versions, code, model/tokenizer, precision, declared hardware/runtime, batch rules; total order incl. ties; GPU determinism verified (seed alone insufficient); no bit-exact promise across GPUs/drivers — define numeric/retrieval tolerances there. If `vecs.npy` diverges on the reference profile, the test **fails**.
- **Idempotence key** = upstream hashes + stage config + code/model/format versions; output hash verifies. Cache hit only on a **published + verified** artifact. Concurrent same-key runs must conflict, not publish two versions.
- **Resume test:** clean build, second build in another dir, resumed build after interruption (mid-write + pre-activation); same hashes, no duplicates/invalid offsets; server sees old complete or new complete snapshot; test published artifact but ledger not yet updated.

**5c — Provenance:**
- Three proofs: **(1)** reconstruct the index from immutable inputs; **(2)** recompute scores without rerunning systems (frozen outputs, `index_version`, query set hash, judgment snapshot, scorer version/config; Exa outputs only if authorized); **(3)** replay performance (same 4d profile, cache/load, variability rule).
- Acceptance: another person starts from the manifest, no local cache or implicit machine knowledge, and finds the proofs. A hash doesn't give bytes — document location, access, retention. Inaccessible source → mark **"not reconstructible."**

**5d — Observability:**
- OpenTelemetry + metrics export + JSON logs; Grafana/Loki optional.
- Each stage exposes **duration, result, volumes, decision code** — not queries, objectives, full URLs, content, keys, or client IDs.
- Metrics: bounded labels (`route`, `tier`, `pool`, `stage`, `outcome`), queue time separate, distinct counters for 429/overload/deadline/degradation; `request_id`/`trace_id`/shard in traces/logs, not every series; histograms; **don't average worker p95**.
- Test: successful call + injected failure correlate with the correct `index_version`; collector down → service continues, telemetry queue bounded, export loss observable; supervision is not a dependency of `/search`.

**5e — CI/CD:**
- No undocumented artisanal steps; **same verified artifacts promoted by digest**.
- **PR:** CPU checks, Tier-0 budget excluding dependency install, wheel build + install smoke test with the Rust extension; GPU tests on **trusted code only**, isolated; never unapproved PR code on the GPU runner with release access; pin external actions; separate test/release permissions.
- **RC:** install built artifacts, HTTP/MCP smoke, open the real index, changelog/SBOM, link Gate 3/4 evidence to the RC digest; GPU runner unavailable = **missing evidence**, not success.
- **Rollback:** binary + index pair, Postgres schema compatibility; previous image isn't enough if a migration broke the old service; drained deployment → measure/announce acceptable interruption.

**5f — Failure semantics:**
- **No partial success** for an integrity defect or an unavailable required shard; `degraded` only for supported/tested functional fallbacks.
- **Queue full / GPU alloc refused** → 503 for unserved work, no retry loop, check worker state before readmission; `lite` holds budget in the isolation scenario.
- **Worker OOM-killed** → supervisor detects, removes, restarts; front survives → error contract; else test observed break + return to ready.
- **Manifest incomplete / checksum invalid / version inconsistent** → refuse activation; keep old snapshot if it exists, else not ready; in-service corruption → remove the affected version and fail explicitly.
- **Required shard lost** → failover only if a healthy replica of the **same version** responds within budget; else explicit unavailability; no failover guarantee in v1 single-node.
- **Slow dependency / cancelled worker** → separate immediate refusal, local deadline, upstream timeout; **504 = gateway timeout to upstream**; fix tags/headers in D11; cancelled work stops at the next batch boundary.
- **Recovery:** delay per scenario; distinguish **reconstructible index** vs **durable data** (accounts, keys, bans) — an index rebuild doesn't restore Postgres, and a rollback must not reactivate a revoked key.

**D17 freezes the invariants and tests, not the unknown numbers.** Open until the pilot: validated sizes, production partitioning, inter-profile tolerances, recovery delays. **Simulated / unexecuted / passed** must remain three distinct states in the release report.

---

## 2. The 17 points (stable IDs)

### 2.1 Subject tracks (9)

| ID | Subject | Status |
|----|---------|--------|
| S1 | Definition of done — protocol defined (Gates 0–5 + anti-goals); evidence pending | `[RESOLVED (planning)]` |
| S2 | Product contract — v1.0-gate0 frozen + v1.1 | `[RESOLVED (planning)]` |
| S3 | Scale envelope & hardware — defined (D28–D40, D72) | `[RESOLVED (planning)]` |
| S4 | Data plane — defined (D41–D56, D76–D79); passage spec freeze (D44) after B | `[RESOLVED (planning)]` |
| S5 | Models — resolved (planning): D57–D69 + D81 (choice rule); model choice = D81 execution (evidence pending) | `[RESOLVED (planning)]` |
| S6 | Index & retrieval — resolved (planning): D82 (R0/R1), D83 (BM25), D84 (highlights), D85–D88 (interface/orchestrator/sharding/recall) | `[RESOLVED (planning)]` |
| S7 | Serving & platform — resolved (planning): D89 (topology), D90 (caching), D91 (security), D92 (config) + refs; D89 amended 2026-11-26, only version pinning remains (M0) | `[RESOLVED (planning)]` |
| S8 | Evaluation & benchmarking — resolved (planning): D93 (golden set), D94 (highlight metric) + refs (D13/D14/D16/D19/D71/D75/D81) | `[RESOLVED (planning)]` |
| S9 | Repo structure, modularity & milestones — resolved (planning): D95 (repo/layout/naming), D96 (deps), D97 (milestones), D98 (CLA/versioning) | `[RESOLVED (planning)]` |

### 2.2 Blindspots (8)

| ID | Blindspot | Folds into | Status |
|----|-----------|------------|--------|
| B1 | Content acquisition reality — WET lacks metadata; need WARC/WAT | S4 | `[RESOLVED→D28/D56]` |
| B2 | Retrieval completeness — hybrid dense+sparse, passage-level highlights, query understanding | S6 | `[RESOLVED→D81–D84]` |
| B3 | Update / freshness lifecycle — no incremental insert/delete/re-embed today | S4/S6 | `[RESOLVED→D56]` |
| B4 | Answer / deep tiers need an LLM — local inference vs pluggable provider | S5 | `[LATER→§3.8]` |
| B5 | Failure & degradation semantics — OOM, node loss, corrupt shard, partial index | S7 | `[RESOLVED→D69/D17 5f/D89]` |
| B6 | Caching & cost model — query/embedding/content cache; $/query, GPU-hours | S3/S7 | `[RESOLVED→D90]` (cost LATER) |
| B7 | Evaluation at scale — how to measure recall@N for 1B docs without 1B docs | S8 | `[RESOLVED→D75/D87/§1.8]` |
| B8 | Ops, versioning, licensing — deployment, index/model/API migration, Common Crawl terms, PII | S9/S7 | `[RESOLVED→D53/D55/D98]` |

> 9 subjects + 8 blindspots = 17. The count is stable; IDs are what matter.

### 2.3 Data-layer follow-ups (added 2026-11-22)

| ID | Point | Folds into | Status |
|----|-------|------------|--------|
| B1a | `ingest.py` discards free WET metadata (`warc-date`, `warc-identified-content-language`); title is slug-derived | S4 | `[RESOLVED (planning)→D56]` (TODO `[V1]`) |
| B1b | WET lacks title, outbound links, HTTP `last-modified`, categories, HTML structure — need WAT/WARC or live fetch | S4 | `[RESOLVED (planning)→D56]` (TODO `[V1]`) |

### 2.4 Keep/cut inventory (→ D100)

| Keep (good bones) | Rewrite / cut | Undecided |
|-------------------|---------------|-----------|
| Rust `ann-core` (binary quant, LUT, IVF, roaring) — correct, fast, tested; **D82: optional R1 Hamming scan only (IVF/LUT excluded); created only if profiling shows the scan is the bottleneck and ≥2× gain at equal recall (K1)** | Config split (`config.py` + `config_loader.py` override) | WET/WAT/WARC → D28 |
| Measured operating points + `EXPERIMENTS.md` discipline (historical, D82) | MCP server (global state, dead manifest hook) | Custom Rust index vs library → D82 |
| Ingest/dedup (SQLite bounded dedup) | Pipeline scripts (`run_pipeline`, `build_index`) | Embedding model(s) → D81 |
| Content store (historical/concepts, D48–D50) | Docs (stale counts, contradictions) | Generator → LATER |
| Gate/bench harness concepts | Notebooks (discredited 0.027 baseline) | |
| Security hardening (constant-time auth, strict config, path containment) | Box-only ledgers (`runs.jsonl`) | |
| Tests (230) — salvage selectively | | |

### 2.5 Architecture decisions (→ A1/D8)

| ID | Decision | Status |
|----|----------|--------|
| A1 | **API-first.** The core is an HTTP API (`/search`, `/contents`, ...). MCP is a thin transport adapter over it, not the product. `curl POST /search` must work standalone. | `[RESOLVED→D8/D12/§3.3.1]` |

### 2.6 Definition status (reconciled 2026-11-24)

**Status model:** `protocol defined` (design written) vs `evidence` (`not executed` / `blocked` / `failed` / `validated`). A gate is not "complete" until its evidence is validated.

| Area | Protocol | Evidence |
|------|----------|----------|
| S1 Definition of done | defined (Gates 0–5 + anti-goals) | Gate 0 not executed; Gate 1 observed (one session); Gate 2 defined; Gate 3: planned, evidence not executed, Exa snapshot blocked (D19); Gate 4 defined; Gate 5 defined |
| S2 Product contract | **v1.0-gate0 frozen** | later fields explicitly 400; filter × type table before Gate 1 |
| S3 Scale & hardware | resolved (planning) (D34/D36) | reference box/corpus defined |
| S4 Data plane | resolved (planning) (D28/D41/D56) | passage spec freeze (D44) after run B |
| S5 Models | resolved (planning) (D57–D69, D81) | model choice (D81 exec) evidence pending |
| S6 Index & retrieval | resolved (planning) (D82–D88) | measurements pending (R0/R1, BM25, highlights) |
| S7 Serving & platform | resolved (planning) (D89–D92) | D89 amended 2026-11-26; only version pinning remains (M0) |
| S8 Evaluation | resolved (planning) (D93, D94) | golden set, judge, snapshot not executed/blocked |
| S9 Repo & milestones | resolved (planning) (D95–D98) | D89 amended 2026-11-26; only version pinning remains (M0) |
| Interfaces (v2.2) | resolved (planning) (D99) | confirmed with modifications (clamp, tag, 409, /answer LATER) |
| Dev rules | resolved (planning) (D102) | enforcement in CI |
| Data metadata (B1a/B1b) | resolved (planning) (D56) | tracked `[V1]` in TODO |
| Keep/cut (K1) | resolved (planning) (D100) | ann-core optional R1 (D82) |

**Read:** statuses above are **planning statuses**; evidence (gate runs, measurements) is tracked separately as **"evidence pending"**.

---

## 3. Research findings

### 3.1 Common Crawl data reality — what WET actually gives us

**This is the data-layer foundation. If the acquisition is wrong, everything downstream is wrong.**

Common Crawl ships three formats per crawl:

| Format | Contains | Use for |
|--------|----------|---------|
| **WARC** | Raw HTTP request/response + full HTML + all headers | Max fidelity; heaviest |
| **WAT** | Computed metadata: HTTP headers, `<title>`, links, metas, gzip offset into WARC | Title, outbound links, content-language, last-modified |
| **WET** | Extracted plaintext only, one `conversion` record per page | Cheap text corpus |

**A real WET record** (from `commoncrawl.org`, the Wikipedia Saturn page):

```
WARC/1.0
content-length: 80489
warc-record-id: urn:uuid:df74c49c-f297-48e2-96de-533fa5068b73
content-type: text/plain
warc-date: 2023-09-29T08:25:05Z
warc-type: conversion
warc-target-uri: https://en.wikipedia.org/wiki/Saturn
warc-refers-to: urn:uuid:8007e174-e1f3-4778-90b9-70a4b776c64c
warc-identified-content-language: eng
warc-block-digest: sha1:TPDGIBQ5NGM3333YFEHGT6K35P2OITTY

Saturn - Wikipedia

Jump to content
...
```

**What WET gives us per record:**

- `warc-target-uri` — the URL
- `warc-date` — **crawl date, not publication date** (the repo currently discards it; do not fill `published_at` from it)
- `warc-identified-content-language` — language (**repo discards this**)
- `warc-refers-to` — links to the WARC response record
- `warc-block-digest` — content hash
- `content-type`, `content-length`
- the extracted plaintext body

**What WET does NOT give us:**

- a structured `<title>` — the extracted text often begins with the page title, but it is not a reliable field (the repo synthesizes one from the URL slug — lossy)
- outbound links (needed for `/findSimilar`)
- HTTP headers such as `last-modified` (needed for real published dates)
- categories / site metadata
- HTML structure (needed for section-aware extraction, highlights)

**What the repo currently does:** `exa_home/ingest.py:read_wet()` reads only `WARC-Target-URI` + body, sets `title` from the URL slug, and hardcodes `date=""`. **It is leaving free metadata on the floor** — `warc-date` and `warc-identified-content-language` are right there in every WET record.

**What WAT adds** (same crawl, JSON per record):

```
Envelope
  WARC-Header-Metadata: WARC-Target-URI, WARC-Type, WARC-Date
  Payload-Metadata
    HTTP-Response-Metadata: Headers (Content-Language, Content-Encoding, Last-Modified, ...)
    HTML-Metadata:
      Head: Title, Link[], Metas[], Links[]
  Container: Gzip-Metadata (Compressed, Offset)  # byte offset into the WARC
```

**What WARC adds:** the raw HTML and the full HTTP response (status, `last-modified`, `content-language`, `content-type`, redirects). This is what you need for true published dates, section-aware extraction, and link extraction at fidelity.

**Implication for "behaves exactly like Exa":**

- `startPublishedDate` / `endPublishedDate` → need `last-modified` or page metadata → **WAT/WARC**, or a metadata extraction pass.
- `/findSimilar` → needs outbound links → **WAT/WARC**.
- `highlights` → needs passage-level structure → **WARC HTML** or a chunker over WET.
- `category` → needs classification/labels → not in CC; must be derived.
- `maxAgeHours` / freshness → needs crawl dates + refresh policy → **WET date + incremental refresh**.

**Options for S4 (to decide with measurement):**

| Option | Fidelity | Cost | Verdict |
|--------|----------|------|---------|
| WET only | text + URL + date + language | cheapest | viable for a first index; **must at least read date + language** |
| WET + WAT | + title, links, headers, WARC offset | ~1 extra pass | strong middle ground; unlocks findSimilar + dates |
| WARC only | everything | heaviest (HTML parsing) | highest fidelity, highest cost |
| Live crawl (Exa-style) | everything + freshness | very heavy | out of scope for v1; design the seam but don't build it |

`[RESOLVED→D28/D56]` S4-B1: Which acquisition tier for v1, and which Exa fields are non-negotiable vs "best effort / absent"?

---

### 3.2 How Exa gets its data (and what we can learn)

From Exa's own docs and blog (Nov 2026):

- **ExaSearchBot** crawls the public web, respects robots.txt, rate-limits per site, does not bypass logins/paywalls/CAPTCHA. Requests are cryptographically signed (Web Bot Auth, RFC 9421).
- **ExaConnect** fetches licensed partner data (not open-web crawl).
- **Vertical indexes:** people (1B+ profiles), companies (~70M), scholarly works (350M), podcasts (3.2M episodes), places (211M), code/docs/security advisories.
- **Scale:** 2T+ tracked URLs, 100B served pages, refreshed continuously (as of Oct 2026).
- **Pipeline:** Crawlers → Parse → Moderate/filter → Embed → in-house vector DB. They pretrained/finetuned their own embedding model on 144× H200 for a month; new clustering + lexical compression + assembly optimizations.
- **Passage retrieval:** the AI index stores full page text and returns the most useful passages (highlights).
- **Hybrid:** neural + keyword signals; `auto` chooses the approach.

**What we take from this:** the architecture is the product — crawl/parse/filter/embed/serve with passage-level retrieval and hybrid ranking. We can replicate the *shape* at our scale; we cannot replicate the *scale* or the *proprietary model*.

---

### 3.3 Exa API / MCP surface (the contract)

**HTTP base:** `https://api.exa.ai`. Auth: `x-api-key` or `Authorization: Bearer`.

**Endpoints (full inventory):**

| Endpoint | What it does | v1? | Notes |
|----------|--------------|-----|-------|
| `POST /search` | core search; `type` = `lite` / `auto` / `deep-lite` / `deep` / `deep-reasoning` (legacy: `instant`, `fast`) | **v1** (`lite`, `auto`) | deep tiers need synthesis → later |
| `POST /contents` | text / highlights / summary for URLs or doc IDs you already have | **v1** (text, highlights) | summary → later |
| `POST /answer` | synthesized answer with citations | later | needs an LLM |
| `/findSimilar` | pages similar to a given URL | later | needs outbound links (WAT/WARC) |
| `/context` | code-context alternative to category filters | later | needs a code index |
| Agent API (beta) | multi-step research; effort mode, `outputSchema`, input dataset; long-running | later | needs a run/poll model |
| Monitors | scheduled recurring searches, ≥1h interval, push by webhook | later | needs a scheduler + webhooks |
| Websets | structured dataset building from search | later | billing/credits |
| `/research` | deprecated → `/search` with `deep-reasoning` | n/a | do not build |

OpenAPI specs at `https://exa.ai/docs/exa-spec.yaml` — **fetch this as the source of truth for the contract**.

**v1 scope proposal:** `/search` (`lite` + `auto`) + `/contents` (text + highlights). That is exactly the default MCP path (`web_search_exa` + `web_fetch_exa`), so it is a genuine drop-in for the common agent case. Everything else is **designed for, not built** — the seams stay open (filters, synthesis, links, code, scheduling), but v1 does not implement them.

**Search types (tiers):**

| Type | Purpose | Latency (reported) |
|------|---------|--------------------|
| `lite` | cheap, low-latency, real-time; no live fetch; limited params | low |
| `auto` | default, balanced quality/speed | medium |
| `deep-lite` | lightweight synthesis | ~4s |
| `deep` | multi-step research + synthesis; `additionalQueries` | 4–15s |
| `deep-reasoning` | legacy → `deep` | 12–50s |
| `instant`, `fast` | legacy → `lite` | sub-150ms / sub-425ms |

**Key `/search` params:** `query`, `type`, `numResults` (1–100), `includeDomains`/`excludeDomains` (≤1200), `startPublishedDate`/`endPublishedDate`, `category` (company, publication, news, personal site, financial report, people), `contents` (`text`, `highlights`, `summary`, `extras`, `maxAgeHours`, `snapshotAsOf`, `subpages`), `outputSchema`, `additionalQueries` (≤10), `objective`, `userLocation`, `moderation`, `compliance`, `stream`.

**Response:** `requestId`, `results[]` (title, url, publishedDate, author, text/highlights/summary, score), `costDollars`, `searchTime`, `warnings`, `notices`.

**MCP tools (hosted):**

| Tool | Default | Use |
|------|---------|-----|
| `web_search_exa` | yes | standard search |
| `web_fetch_exa` | yes | read known URLs |
| `web_search_advanced_exa` | opt-in | filters, dates, highlights, freshness |
| `agent_run` | yes (OAuth/key) | multi-step research, structured output |

**Implication:** the product contract is large. We should decide **which subset is the v1 contract** (likely `/search` + `/contents` + the MCP search/fetch tools) and which are "designed for, not built" (answer/deep/agent/monitors/websets). Exact wire compatibility is a spectrum; "behaves like Exa" may mean *same tool semantics*, not byte-identical JSON.

`[RESOLVED→D8 (S2 frozen)]` S2: Which endpoints/tools are v1 vs later? Do we match the OpenAPI schema exactly or keep the same semantics with our own schema?

### 3.3.1 Observed keyless MCP contract (2026-11-23)

Called `https://mcp.exa.ai/mcp` keyless: `initialize` → `tools/list` → `tools/call`.

**Keyless surface:** exactly two tools — `web_search_exa` and `web_fetch_exa`. `web_search_advanced_exa` and `agent_run` require OAuth or an API key.

**`web_search_exa` input schema:**

```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string", "minLength": 1},
    "numResults": {"type": "number", "default": 10},
    "objective": {"type": "string", "minLength": 1, "maxLength": 4096}
  },
  "required": ["query", "objective"],
  "additionalProperties": false
}
```

**`web_search_exa` output:** one `content[].text` block with concatenated results:

```
Title: React vs Vue Performance Benchmark...
URL: https://...
Published: 2025-06-08T08:02:41.000Z
Author: N/A
Highlights:
<highlight text>
---
Title: ...
...
```

plus `_meta: {"searchTime": 182.7}`.

**`web_fetch_exa` input schema:**

```json
{
  "type": "object",
  "properties": {
    "urls": {"type": "array", "items": {"type": "string"}},
    "maxCharacters": {"type": "number", "minimum": 1, "default": 3000}
  },
  "required": ["urls"],
  "additionalProperties": false
}
```

**`web_fetch_exa` output:** one `content[].text` block:

```
# <Title>
URL: <url>
Published: 2025-06-08

<markdown body>
```

plus `_meta: {"searchTime": 12.9}`.

**Implications:**

- The MCP server is a **text formatter**, not a JSON API. The HTTP `/search` returns structured JSON; the MCP packs it into `Title / URL / Published / Author / Highlights` blocks.
- `objective` is **required** on `web_search_exa` — our v1 schema must match.
- `web_search_exa` always returns highlights; there is no `contents` object on the MCP tool.
- `web_fetch_exa` is batch-first and caps at `maxCharacters` (default 3000).
- `publishedDate` format differs between search (full ISO timestamp) and fetch (date only).
- The keyless MCP is the exact v1 drop-in target; the advanced/agent tools are later.

**v1 scope resolution (fixes the doc/TODO contradiction):**
- **MCP v1** = the keyless surface exactly: `web_search_exa` + `web_fetch_exa`; no `type`, filters, or `contents` object exposed.
- MCP and HTTP both call the same in-process `SearchService`; MCP does **not** make an HTTP call to itself. Auth/quota/deadline apply once at the transport boundary.
- **HTTP v1** = `/search` (`lite`, `auto`; filters + contents) + `/contents`; the MCP does not expose filters in v1.
- `/contents` accepts **`ids` or `urls`** (not both), with per-item statuses; `maxCharacters` is an MCP/replica extension, not an Exa HTTP top-level field.
- `web_fetch_exa` is **shape-compatible, snapshot-only** in v1 (no live fetch); don't promise every public URL is readable.
- `lite` unsupported filters → **400 documented difference**, not parity. **(superseded by D70/D99(4))**
- `objective` is required by the MCP and **must be consumed** by the pipeline (query understanding / rerank context), not ignored. Add `objective` to the domain `Query`.
- Decision 4 (`lite` unsupported filters → 400) applies to the HTTP API, not the MCP v1. **(superseded by D70/D99(4))**
- `/answer`, `/findSimilar`, `/context`, Agent, Monitors, Websets, and deep tiers are `[LATER]`.

**Tier selection (→ D8/D27).** The MCP tool has **no `type` parameter**, so it is a fixed-tier surface — Exa's `web_search_exa` is effectively the default (`auto`) tier. The HTTP `/search` is where `type` is explicit. For v1: MCP = `auto` (middle `TierPlan`: rerank, no synthesis); HTTP = explicit `lite`/`auto`/`deep`; `auto` is **not** a classifier in v1 — it is the middle plan. A query-complexity classifier can be added later behind the same `auto` contract. If we want lite/deep through the MCP, add an optional `type` field (backward-compatible superset) later.

---

### 3.4 Embedding models (2026 landscape)

> **Unverified:** the 2026 rankings and the `harrier-oss-v1` / MTEB figures come from blog aggregators, not the primary leaderboard. Treat them as leads to verify, not facts. `mxbai` / Qwen3 specs are consistent with their model cards.

The repo uses `mixedbread-ai/mxbai-embed-large-v1` (335M params, 1024 dims, 512 max tokens, MRL-256, Apache 2.0, English). It scores 66.3 on MTEB(eng v2) — mid-pack in 2026.

Current open-weight leaders (MTEB v2, Nov 2026):

| Model | Params | Dims | Max tokens | License | Notes |
|-------|--------|------|-----------|---------|-------|
| Qwen3-Embedding-8B | 7.6B | 4096 | 32k | Apache 2.0 | top MTEB/RTEB |
| Qwen3-Embedding-4B | 4.0B | 2560 | 32k | Apache 2.0 | strong quality/size |
| Qwen3-Embedding-0.6B | 0.6B | 1024 | 32k | Apache 2.0 | good small option |
| harrier-oss-v1-27b | 27B | 5376 | 32k | MIT | top multilingual (figures **unverified**) |
| harrier-oss-v1-0.6b | 0.6B | 1024 | 32k | MIT | small, strong (figures **unverified**) |
| EmbeddingGemma 2 | 0.27B (text) | 768 | 8k | Apache 2.0 + usage policy | small, multimodal; v1 was Gemma-licensed (rejected) |
| arctic-embed-l-v2.0 | 568M | 1024 | 8k | Apache 2.0 | strong multilingual |
| mxbai-embed-large-v1 | 335M | 1024 | 512 | Apache 2.0 | current repo |
| gemini-embedding-001 | — | 3072 | 2k | API | closed |

**Key tradeoffs for our system:**

- **Quality vs latency:** query embedding is on the critical path; doc embedding is offline/batch. We can afford a bigger doc model than query model, or the same model with different batching.
- **MRL (Matryoshka):** many models can truncate 4096→256/512 with small quality loss. This is the storage lever.
- **Quantization:** **D82 default = R0 exact GPU (bf16, no quantization)**; binary (R1) only as fallback; PQ/MRL excluded v1. (The old "256-bit binary" note is superseded by D82.)
- **Multilingual:** if the corpus is multilingual, use a multilingual model (Qwen3, arctic v2, EmbeddingGemma 2).
- **License:** Apache 2.0 / MIT preferred for an open-source server.

**The real test is not MTEB — it's recall@N on our corpus.** We must measure.

`[RESOLVED→D81]` S5: model choice rule (D81); dimension/quantization (D82); measured recall/latency/VRAM pending.

---

### 3.4.1 Model licensing & multilingual (D57/D58)

**License filter (D57):** accept Apache-2.0 / MIT / BSD-2/3-Clause (SPDX); reject non-commercial, RAIL/Gemma/Llama ToU, gated. Verify at the pinned HF revision (tag, LICENSE, model card); conflict → reject. Usage policy in addition → "accepted with reserve" if it doesn't restrict internal search. Tokenizer/base checked too.

**Multilingual (D58):** one common model for EN+FR, one index; English-only reference in the comparison; decision on the golden set (EN primary, FR secondary, BM25 floor); freeze `X` before the run; default = least costly if not significant.

**Candidates (licenses to re-verify at the pinned revision):**

| Model | License | Dims | MRL | Note |
|---|---|---|---|---|
| Qwen3-Embedding-0.6B | Apache 2.0 | up to 1024 | yes | query instruction; 32k ctx |
| Qwen3-Embedding-4B | Apache 2.0 | 2560 | yes | heavier; 32k ctx |
| arctic-embed-l-v2.0 | Apache 2.0 | 1024 | yes | EN/FR/ES/DE; 8k ctx |
| EmbeddingGemma 2 | Apache 2.0 + usage policy | 768 | TBD | 270M text params; 8k ctx |

**Note:** 32k context ≠ passage size (S4 D44); dims/quantization → S6.

### 3.4.2 PromptConfig (D61)

- **Location:** part of the `embeddings` stage spec (→ `stage_key`, `build_id`); **not** `chunker_version`.
- **Serving:** reads the `PromptConfig` from the `current` build manifest; refuses startup if the loaded model/config diverges; verifies **reference vectors** (fixed strings encoded at build, re-encoded at startup, compared with tolerance).
- **Exact templates** (verify at the pinned revision):

| Model | Query | Document | Note |
|---|---|---|---|
| Qwen3-Embedding | `Instruct: {task}\nQuery:{query}` | no prefix | instruction in English |
| arctic-embed-l-v2.0 | `query: ` | no prefix | |
| EmbeddingGemma v1 | `task: search result \| query: ` | `title: {title or none} \| text: ` | v2 may differ |
| mxbai-embed-large | `Represent this sentence for searching relevant passages: ` | no prefix | English only |

- **Title:** the doc template decides where the title goes; `title_prefix` only decides whether to fill it.
- **Objective:** not used as instruction in v1 (fixed instruction per build); dynamic instruction LATER.
- **Query budget:** `budget_query = max_tokens_effective − special tokens − query template`; truncate at embedding, no 400 (S2 frozen), count with threshold.
- **Ablation:** official prompt per model for comparison; only finalists, ≤3 variants; default official unless gain > Y EN without loss > Z FR.

### 3.4.3 Weight precision (D62/D63)

- **Default:** native checkpoint dtype (**bf16** for Qwen3, arctic v2, EmbeddingGemma); fp16 is a conversion, not the reference.
- **Memory is not the issue at our sizes:** 0.6B ≈ 1.2 GB, 4B ≈ 8 GB on 96 GB. Precision matters for **throughput**.
- **FP8 decision rule:** only if the T1 embedding-time projection in bf16 exceeds the embeddings budget; measure throughput, cosine similarity (mean/p1) vs bf16, top-k overlap, recall EN/FR; accept per **G/W/K** frozen before the run; default bf16.
- **INT4:** LATER (weight-only AWQ/GPTQ helps token-by-token generation, not prefill embedding; quality risk highest).
- **Same precision doc/query:** in the model config inside the `embeddings` spec; serving verifies at startup.
- **Determinism (D63):** exact stages bit-exact; floating stages idempotent by `stage_key`, output tolerance (cosine ≥ threshold), fixed batch/order/versions.

> **Unverified:** the "binary ~5% loss" and "PQ minimal loss" figures are uncited rules of thumb; measure them on our corpus.

### 3.5 ANN index landscape

| Index | Best for | Memory | Updates | Notes |
|-------|----------|--------|---------|-------|
| **HNSW** | <100–200M, lowest latency | high (graph in RAM) | hard | best recall if RAM allows |
| **IVF-PQ** | billion-scale, memory-constrained | very low | easy | fast, lower recall |
| **DiskANN / Vamana** | 100M–billions, SSD-backed | low (PQ in RAM) | via FreshDiskANN | 5–15ms at billion scale |
| **ScaNN** | hybrid setups | medium | medium | anisotropic quantization |
| **CAGRA (GPU)** | GPU-resident, fast build/search | VRAM | rebuild | NVIDIA cuVS/RAFT |
| **Custom Rust IVF + binary + LUT** | our current core | very low | easy | 33× over naive bit loop |

**What we have:** a custom Rust `ann-core` (PyO3) with sign-bit binarization, LSB packing, IVF routing, LUT nibble scoring, roaring filters. It is fast and correct (per the audit), and it is the seed of the index backend.

**What we need to decide:** the index *interface* must be pluggable so we can swap HNSW/IVF/DiskANN/CAGRA without touching the serving code. The choice is a function of (corpus size, RAM/VRAM, latency budget, recall target, update rate). That is exactly the "memory budget as an adaptive parameter" requirement.

`[RESOLVED→D82/D85]` S6: index = R0 exact GPU / R1 binary + int8 (D82); pluggable interface (D85).

---

### 3.6 Hardware envelope & memory math

| GPU | VRAM | Bandwidth | Notes |
|-----|------|-----------|-------|
| RTX 5090 | 32 GB GDDR7 | 1.79 TB/s | consumer, no MIG |
| RTX PRO 6000 Blackwell | 96 GB GDDR7 | 1.6–1.79 TB/s | ECC, MIG up to 4×24GB |
| H200 | 141 GB HBM3e | 4.8 TB/s | 900 GB/s NVLink |
| B300 (Blackwell Ultra) | 288 GB HBM3e | 8 TB/s | 1.8 TB/s NVLink, FP4 |

**Storage math for a 256-dim embedding:**

| Docs | Binary (32 B/doc) | Float32 (1 KB/doc) |
|------|-------------------|--------------------|
| 1M | 32 MB | 1 GB |
| 100M | 3.2 GB | 100 GB |
| 1B | 32 GB | 1 TB |
| 10B | 320 GB | 10 TB |
| 100B | 3.2 TB | 100 TB |

**Implication:** binary 256-dim codes for 1B docs (32 GB) fit in a 96 GB card alongside an IVF index. 10B needs multi-GPU or disk. 100B needs sharding. **The code path is identical; only the shard count and placement change.** That is the scale-invariance *design goal* — not a proof: IVF sizing, recall at fixed `nprobe`, and tail latency across shards all change with N. **Note (D82):** dimension = the D81 model; MRL excluded; the 256-bit figure is illustrative only (R0 bf16 / R1 binary).

**Passage indexing changes the math.** If passages are indexed at ~10 per document, 1B docs becomes ~10B passages → ~320 GB of binary codes, which no longer fits a single 96 GB card. The index unit must be chosen before the hardware envelope is fixed.

**Vector storage (D59):** `N_docs × r × bytes_per_vector` (dim/quantization in S6) [+ optional rescoring copy]. Multi-vector per-token (ColBERTv2 ~36 B/token) is ~hundreds× single-vector: 256 tokens ≈ 9 KB/passage → 1B passages ≈ 9 TB, incompatible with 500 GB. Single-vector in v1; multi-vector LATER behind `vector_kind`.

`[RESOLVED→D30/D36/D72]` S3: What corpus sizes are the design targets (1M / 10M / 100M / 1B)? What latency/throughput budgets per tier? What is the memory budget policy (VRAM-resident vs disk-backed vs sharded)?

---

### 3.7 Hybrid retrieval, passages, highlights

- **Dense-only fails on:** exact tokens (SKUs, error codes, IDs), rare terms, strict phrasing, multi-entity constraints.
- **Hybrid = dense + sparse (BM25 or SPLADE) fused with RRF** (`1/(k + rank)`, k≈60). RRF is rank-only, so it avoids the score-scale mismatch that breaks naive weighted sums.
- **Passage-level retrieval:** Exa stores full page text and returns the most useful *passages* (highlights). That means chunking documents, indexing passages (or storing passage offsets), and returning the best sentences.
- **Chunking:** fixed-size token chunks (~512 tokens, 10–20% overlap) is the standard baseline; hierarchical parent-child is the production default when precision + context matter.

**Implication:** the index is not just "one vector per URL." We likely need:
- document-level vectors (for coarse retrieval), and
- passage-level vectors or offsets (for highlights),
- a sparse/BM25 index (for exact/rare terms),
- a fusion step (RRF).

`[RESOLVED→D83/D84]` S6: index **passages** (D83/2); **BM25** (D83), SPLADE later; fusion **RRF k=60** (D81/D83); highlights **extractive** (D84).

---

### 3.8 Answer / deep tiers need an LLM

`/answer`, `deep`, `deep-lite`, `deep-reasoning`, and `outputSchema` synthesis all require generation with citations. Options:

| Option | Pros | Cons |
|--------|------|------|
| Local vLLM/SGLang | no per-call cost, full control, private | GPU budget, ops burden, model quality |
| Pluggable provider (OpenAI/Anthropic/local) | best quality, no GPU | cost, dependency, privacy |
| Hybrid (local small model default, provider optional) | flexible | complexity |

- **vLLM vs SGLang (2026):** close on throughput; SGLang slightly ahead on newest/hybrid models, vLLM has the larger ecosystem (~92k vs ~36k stars). Both support AWQ/GPTQ/FP8/FP4.
- **Grounding/citations:** generated text must map back to source passages. This is a real engineering problem (citation spans, attribution).

**Implication:** the answer/deep tiers are a separate subsystem with its own GPU budget and failure modes. It is in tension with "no single dependency" — so the generator must be a pluggable seam.

`[LATER→§3.8]` S5: Is the generator local, pluggable, or both? Which model(s)? How do we do citations?

---

### 3.9 Freshness / incremental updates

- **Today:** batch only. Common Crawl is monthly; the repo rebuilds from scratch.
- **Exa:** refreshes continuously; `maxAgeHours` controls cache age; `snapshotAsOf` returns historical versions.
- **Options:**
  - Periodic full rebuild (simple, expensive at scale).
  - Delta ingest + incremental index (FreshDiskANN, streaming HNSW, IVF append + periodic rebuild).
  - Live fetch on cache miss (Exa's `maxAgeHours: 0`).
- **Deletes:** robots/noindex removal; hard deletes vs tombstones.

`[RESOLVED→D56]` S4-B3: What is the update model for v1? Full rebuild vs delta? How do deletes propagate? What freshness can we honestly claim?

---

### 3.10 Licensing / compliance

- **Common Crawl:** free to access, but terms apply; respect robots.txt and noindex; PII and copyright are real concerns; no warranty.
- **Model licenses (D57):** accept Apache-2.0 / MIT / BSD-2/3-Clause (Qwen3, arctic v2, mxbai, harrier); reject non-commercial and RAIL/Gemma/Llama ToU and gated models. **EmbeddingGemma 2 is Apache 2.0 + usage policy** (v1 was Gemma-licensed → rejected); verify each at the pinned HF revision.
- **Content storage:** store the minimum needed (URL, text, hashes); honor takedowns.

`[RESOLVED→D51–D55]` S9-B8: What is our data/licensing posture? What do we store, for how long, and how do we honor removals?

### 3.11 Future endpoint contracts (designed-for, not built)

Every endpoint below is **out of v1 scope but must not be forgotten**. The contract is written now so its spot is prepared and the core does not change when it arrives. "Needs" = services it requires; "Adds" = the only new pieces it should introduce.

| Endpoint | Request (key fields) | Response (key fields) | Needs | Reuses | Adds / seam |
|----------|----------------------|-----------------------|-------|--------|-------------|
| `POST /search` | `query`, `type` (`lite`/`auto`/`deep-lite`/`deep`/`deep-reasoning`), `numResults`, `includeDomains`, `excludeDomains`, `startPublishedDate`, `endPublishedDate`, `category`, `contents{text,highlights,summary}`, `outputSchema`, `additionalQueries`, `objective`, `userLocation`, `moderation`, `stream` | `requestId`, `results[]{title,url,publishedDate,author,text,highlights,summary,score}`, `costDollars`, `searchTime`, `warnings`, `notices`, `output` | understand, retrieve, filter, rerank, contents, synthesize(optional) | all core | baseline; `type` is open |
| `POST /contents` | `urls`/`ids`, `text{...}`, `highlights{...}`, `summary{...}`, `extras{links,imageLinks}`, `maxAgeHours`, `snapshotAsOf`, `livecrawl`, `subpages` | `results[]{url,title,text,highlights,summary,links,...}` | resolve, contents.get, cache, livefetch(optional) | contents provider | livefetch seam (`maxAgeHours: 0`) |
| `POST /answer` | `query`, `text?`, `outputSchema?` | `requestId`, `answer`, `citations[]{url,title,...}` | understand, retrieve, rerank, synthesize | retriever, reranker | `Synthesizer` + citation model |
| `/findSimilar` | `url`, `numResults`, filters | `results[]` (same shape as /search) | resolve, search_by_vector, rerank | retriever | URL→vector + reverse lookup |
| `/context` | `query`, filters | code snippets / context | code-retrieve, rerank, contents | retriever | code index + language detection |
| Agent API (beta) | `query`, `effort`, `outputSchema`, `input{data,exclusion}`, `dataSources`, `previousRunId`, `systemPrompt` | `{id, status: running|completed, output, sources, usage, cost}` | orchestrate, all services, run store | all | `AgentRunner` + `RunStore` (poll with `runId`) |
| Monitors | `query`, schedule (≥1h), `webhook`, filters | monitor id, status | scheduler, search, webhook | search | `Scheduler` + `Webhook` + `MonitorStore` |
| Websets | `query`, `schema`, filters | dataset rows | search, synthesize(schema), dataset store | search, synthesizer | `DatasetBuilder` |
| `deep` / `deep-lite` / `deep-reasoning` | `query`, `type`, `additionalQueries` (≤10), `outputSchema` | results + `output` | plan, multi-round retrieve+rerank, synthesize | retriever, reranker | `QueryPlanner` + multi-round orchestration |

**Notes:**
- `/research` is deprecated → do not build; it is `/search` with `type: deep-reasoning`.
- Monitors push by **webhook** (not polling), with a one-hour minimum interval.
- `/context` is Exa's recommended alternative to category filters for coding queries.
- `/findSimilar` needs outbound links, so it depends on the WAT/WARC acquisition tier (B1b).

### 3.12 Observed agent search traces (OpenCode DB, 2026-11-23)

Mined `~/.local/share/opencode/opencode.db` read-only:

- **205** `websearch` tool calls, **179 unique** queries.
- **0** calls carry an `objective` field. The tool input is `{query, type?, numResults?, contextMaxCharacters?}`.
- Types: 112 default, 30 `auto`, 35 `deep`, 28 `fast`.
- Outputs are **Exa-shaped** (`Title / URL / Published / Author / Highlights`), but the `websearch` tool is the user's **selected search integration** (mixed engines), **not confirmed Exa traces**; treat the shape as Exa-like, not as an Exa capture.
- Topic skew (multi-label): openrouter/LLM 79, infra/ops 29, data/ML 25, python 21, web/search 8. This is a coding/ML assistant's trace, not a representative web sample.

**Implications:**
- The traces are a **real query corpus**, but **not objective-grounded**. They cannot directly populate the golden set's `objective` field.
- Golden set v1: **specific independent objectives are the primary gate** (D14/D33); the deduped real queries + a **fixed generic objective** are the secondary/dev cohort for the objective ablation only. Do not reconstruct per-query objectives for the test split.
- Future capture: instrument the search tool / MCP layer to log `objective` (or require it), so new traces are objective-grounded.
- Privacy: the raw queries are local (`/tmp/opencode/websearch_queries.txt`); do not commit them without approval. Export only a deduped, topic-tagged, anonymized set.

### 3.13 Exa engineering blog — what to steal (2026-11-23)

**Exa 3.0 (Oct 2026):**
- Larger embedding model (more compute/data); **Dynamic Highlights GA** — selects tokens *across all results*, 95% fewer tokens than full page text, better answer quality.
- Index expanded: 1.27B ecommerce listings, 211M local businesses, real-time news/sports/weather/markets, flights/events/transit/podcasts.
- **Lite = same index as Auto, less compute** (candidate generation, highlights, ranking). Auto uses more compute. This is the tier model: same index, different compute.

**Web-scale vector DB (Dec 2024):**
- 4096-dim → MRL truncate to 256 (20×) → binary quantization (16×); **query stays float, docs binary**, dot product via 4/8-bit LUT in CPU registers.
- 100k clusters (IVF), search nearest clusters (~1000× throughput).
- Rerank with uncompressed data to recover recall.
- Filters via inverted indexes; clustering fits filters better than HNSW; sharding by cluster.
- Custom query language for multi-stage pipelines.
- **Note:** the LUT hot loop was written in **C++** for performance, not Rust. Benchmark our Rust LUT against this. **(superseded by D82 — IVF/LUT excluded)**

**Exacluster (May 2025):**
- 144 H200, 20 TB HBM3, 36 TB DDR5, 270 TB NVMe, 100 kW; plus 80 A100s.
- Infra: Pulumi, Kubespray, NVIDIA operators, Alluxio (350 TB NVMe cache over S3), Flyte (scheduler, lineage, checkpointing, reproducibility).
- Lesson: reproducibility, lineage, and caching are first-class.

**BM25 optimization (May 2025):**
- **Hybrid is the most powerful architecture** (BM25 + embeddings).
- 1.8 TB per 1B docs; 50% memory reduction via frequency grouping, delta+varint doc IDs (4 B → 1.3 B), zstd, consolidated buffers, singleton optimization.
- WAND-style pruning, impact-ordered indices.
- **Implication:** BM25 is **not optional** and not "later" — it is v1.

**Canon / Composing a Search Engine (Apr 2026):**
- Search pipeline as a **DAG**: retrieve (dense/sparse) → fuse (RRF k=60) → fetch → rerank.
- Pull-based runtime: nodes run when downstream demands; **cancellation, memoization, automatic parallelism**.
- Observability: trace every node's timing/inputs/outputs/decisions; "why did X drop this URL".
- Totality: every node handles every outcome; the type checker rejects missing branches.
- **Implication:** our orchestrator should be a **DAG/plan**, not hardcoded stages. The Tracer should record per-node decisions. This raises the bar for S6/S7.

**exa-d (Jan 2026):**
- Typed columns + declarative dependencies; **Lance on S3**.
- Surgical updates: patch a single column for a fragment without rewriting the rest.
- Query planning = diff between ideal and actual state; compute only missing/invalid columns; **idempotent/convergent**.
- Ray Data + Ray Actors; pipeline parallelism.
- **Implication:** our data plane should be **columnar + incremental + idempotent** (Lance-like); manifests track derived-field validity.

**What this changes for us:**
- **BM25 moves to v1** (hybrid is the core, not a later add-on).
- Highlights should be **dynamic** (cross-result token selection), not per-page.
- Orchestrator should be a **DAG/plan** with cancellation, memoization, tracing.
- Data plane should be **columnar + incremental + idempotent**.
- Benchmark the Rust LUT against Exa's C++ note. **(superseded by D82 — IVF/LUT excluded)**
- Exa 3.0's larger embedding model suggests we should measure quality vs cost, not assume small models are enough.

**Full digest:** `docs/research/exa-blog-digest.md` — 35 sources, 484 lines, every claim tagged `[S]` sourced / `[I]` inference / `[?]` uncertain.

**Key numbers to remember:**

| Metric | Value | Source |
|--------|-------|--------|
| Base embedding dim | 4096 float | web-scale vector DB |
| Indexed dim | 256 (MRL truncation) | web-scale vector DB |
| Binary code | 256 bits = 32 B/doc | derived |
| Clusters | ~100,000 (IVF) | web-scale vector DB |
| Vector search latency | <100 ms | web-scale vector DB |
| Serving target | ~250 ms | Canon |
| Highlights | <100 ms, uncached | highlights-for-agents |
| BM25 | >1.8 TB / 1B docs; sub-500 ms | BM25 optimization |
| Exacluster | 144×H200, 20 TB HBM3, 36 TB DDR5, 270 TB NVMe, 100 kW | Exacluster |
| Index scale | >2T URLs tracked, ~100B pages served | Exa 3.0 |
| Verticals | 1.27B products, 211M places, 350M publications, 3.2M podcasts, 1B people, 70M companies | various |
| Snapshots | 400B+ page versions over 20 years | Exa Snapshot |

**Contradictions to note (do not resolve by guessing):** 100B vs 130B pages; 350M vs 500M publications; Exa 3.0 embedding dims undisclosed; reranker and highlights architecture undisclosed; fusion weights beyond RRF k=60 undisclosed.

### 3.14 Exa data acquisition — what the digest confirms

- **ExaSearchBot** (own crawl; robots.txt; rate-limited per site; Web Bot Auth signatures). **ExaConnect** (licensed partner APIs). Vertical indexes. Customer-supplied data.
- **Scale:** >2T URLs tracked, ~100B pages served, refreshed continuously.
- **Verticals:** 1.27B product listings, 211M places, ~350M publications, 3.2M podcast episodes, 1B+ people, 70M+ companies.
- **Snapshot:** 400B+ page versions over 20 years, addressable by date (`snapshotAsOf`).
- **Acquisition is a quality problem:** URL selection/ranking is itself a model ("most documents are low quality").
- **Parsing:** custom HTML parser; PDFs via OCR + document-parsing models; code via specialized extraction.
- **Derived artifacts per page:** text, metadata, embeddings, structured extractions — each with its own update schedule and dependency surface.

### 3.15 What to steal — blueprint options (not decisions)

These are options to evaluate against our constraints, not choices we have made.

| Subject | Option from the digest |
|---------|------------------------|
| **Data plane** | Lance/Parquet on S3/MinIO; typed column DAG; per-fragment per-column patching; Ray Data + resident embedding actors; snapshot-by-date |
| **Models** | MRL-trained embedder (1024–4096 base, truncate to 256–512); binary doc quantization; small cross-encoder reranker; highlights model; link-prediction pretraining if the crawl supports it |
| **Index** | Clustered binary-ANN + register LUT (C++/Rust); sharded by cluster; BM25 with freq-grouped delta+varint+zstd; RRF k≈60; inverted filter indexes |
| **Serving** | Typed-DAG orchestrator with pull runtime + tracing + cancellation; Lite/Auto on one index; highlights uncached; `maxAgeHours`; region replication |
| **Eval** | WebCode-style extraction + groundedness; ATLAS-style wide/deep F1 with cost/latency; open harness |

**Open questions this raises (answered → refs):**
- Do we build a real crawl, or stay on Common Crawl? → **D28** (CC-MAIN-2026-43).
- Do we need vertical indexes in v1? → **LATER** (D70 `category`→400; S4).
- Do we version snapshots from day one? → **D56/LATER** (single crawl; rebuild).
- Is a highlights model in v1, or a cheaper extractive baseline? → **D84** (extractive S0).
- Do we need a local LLM for answer/deep in v1? → **§3.8 LATER**.
- What are the latency budgets per tier? → **D66**.
- What is the memory budget for BM25 at our scale? → **D73/D83**.

### 3.16 Measured Exa latency by tier (2026-11-23)

Captured 30 queries (10 per tier, 10 domains) against `https://api.exa.ai/search` with `numResults=5`, `contents={text, highlights}`, and a per-query `objective`. **0 errors.** Snapshot: `/tmp/opencode/exa-snapshots/20261123T201821Z/`; metadata copied to `docs/fixtures/exa-mcp/snapshots/`.

| Tier | n | min (ms) | p50 (ms) | p95 (ms) | max (ms) | mean (ms) |
|------|---|----------|----------|----------|----------|-----------|
| lite | 10 | 173.5 | **195.9** | 459.8 | 459.8 | 240.9 |
| auto | 10 | 234.9 | **1056.6** | 1809.8 | 1809.8 | 1078.7 |
| deep | 10 | 5973.6 | **7837.1** | 10682.9 | 10682.9 | 8052.7 |

All times in ms. Small sample (n=10/tier); p95 is the max of 10, so treat as indicative, not a confidence interval. Conditions: one API key, one region, `numResults=5`, text+highlights, objective provided. Deep times are consistent with Exa's published 4–15 s range.

**Implication for Gate 4:** these are the Exa reference points. Our targets are "within budget on our envelope," not "equal to these ms." But they give us the shape: lite ~200 ms, auto ~1 s, deep ~8 s.

**ToS blocker (2026-11-24):** Exa's public terms §4.2(f) restrict use of the service **and its results** to develop a competing product. The Exa comparison is **blocked** until written confirmation covers the benchmark, retention, and third-party judging. Proceed with **replica vs BM25** on authorized data. Use private durable storage (not `/tmp`), freeze the text shown to the judge with its hash, and note: 400 calls = 200×2 excluding ablations/retries; 10/5 QPS is plan-specific; "2–3 min" is an estimate.

### 3.17 Observed HTTP response shape (2026-11-23)

Top-level: `requestId`, `resolvedSearchType`, `results`, `searchTime`, `costDollars`.

Result fields vary by tier:
- **lite:** `id, title, url, author, text, highlights, image` (no `publishedDate`).
- **auto:** `id, title, url, publishedDate, author, text, highlights, image`.
- **deep:** `id, title, url, publishedDate, text, highlights` (no `author`, no `image`).

Cost: `CostDollarsOutput` (OpenAPI):
- `total` — estimated total dollar cost for the completed request (not an invoice).
- `search` — estimated search cost by retrieval mode; some search types report only in `total`.
  - `search.neural` — cost of neural (vector) search operations.
  - `search.keyword` — cost of keyword search operations (absent in our sample).
- `summary` — cost of per-result summaries (`contents.summary`).
- `contents` — breakdown for `/contents` requests (`text`, `highlights`, `summary`).

Measured: lite `{total: 0.004, search:{neural: 0.004}}`, auto `{total: 0.007, search:{neural: 0.007}}`, deep `{total: 0.012}` (no breakdown). Use `total` for cost accounting; the `search` split tells you the neural/keyword mix.

Quirks to note (do not blindly replicate):
- `publishedDate` may be absent/null.
- `author` can be a relative-time string (e.g. `"[deltaMinutes] mins ago Now 1248"`) for some sources.
- `highlights` is a list (1 item in this sample).
- `text` is full page text (up to ~23k chars).
- `resolvedSearchType` is deprecated but present.

**Implication:** the HTTP contract is not perfectly uniform across tiers. Our replica should normalize (always include `publishedDate`/`author`, nullable) while keeping the superset of fields. Document the differences.

---

### 3.18 Content policy, takedown & retention (D51)

**Policy:** `contents_policy ∈ {full, excerpt, none}` per deployment. v1 internal = `full`. Public exposure = separate gate (legal opinion, S2 v1.1 for `excerpt`, takedown). Highlights follow `text`.

**Takedown procedure (D52):**
- Channel: operator CLI; **append-only `exclusions` in Postgres** (outside builds).
- Effect: filter at serving on **all** paths (`/search`, `/contents`, MCP, **after cache**); max propagation delay (e.g., 60 s refresh); next build.
- Scopes: `url`, `url_variants` (default), `host`, `host_suffix`, `content_hash`.
- Build: snapshot of exclusions, hash in the spec.
- Excluded doc → `not_found`; no reason leaked.
- Purge: physical deletion for privacy/legal, only exception to D40.
- Schema: `exclusion_id, scope, value_raw, value_canonical, canon_version, reason, source, request_ref, requested_at, added_at, added_by, note, revoked_at, revoked_by, revoke_reason, purge_required, purged_at`.
- Tests: rollback, cache, variants, duplicates, all paths.

**Retention:**
- Raw WARC: 90 days (D35), deleted after T2.
- Extracted text/passages: index generation lifetime (D45); keep current + previous + gate-referenced builds.
- Query logs: TBD (hot/cold).
- Snapshots: 3j retention.

**Licenses:** code Apache 2.0; models Apache 2.0/MIT (reject non-commercial); data Common Crawl ToS, no public exposure.

**PII:** exclusion table now; detection later (decision rule: types, detector, action).

## 4. Candidate data structures (proposals, not decisions)

### 4.1 Document record (JSONL, one per page)

```jsonc
{
  "doc_id": "<generation>:<url_canonical_hash>",  // stable per (generation, URL)
  "url": "https://...",            // canonicalized
  "url_hash": "<hex>",             // for dedup/lookup
  "domain": "example.com",         // registrable domain
  "title": "…",                    // from WAT/WARC, or slug-derived (lossy)
  "text": "…",                     // extracted plaintext
  "lang": "eng",                   // WET warc-identified-content-language
  "published_at": "2026-01-01T…Z", // from HTTP last-modified / metadata, nullable
  "crawled_at": "2026-11-01T…Z",   // WET warc-date
  "crawl_id": "CC-MAIN-2026-34",
  "content_hash": "<sha256>",       // attribute: dedup + idempotence
  "links": ["https://…"],          // from WAT, optional
  "categories": ["news"],          // derived, optional
  "source": "warc|wet|live"        // provenance
}
```

**Identity model (D18/D20/D29):** `doc_id` = (`generation`, `url_canonical`). `content_hash` is an **attribute** for dedup/idempotence, not the identity. A `url_registry` maps canonical URL → latest `doc_id` (plus version history), so `/contents` by URL resolves the current version. Re-crawling a changed page creates a new `doc_id` but updates the registry.

### 4.1.1 Minimal document schema (S4 step 1)

| Field | Source | Nullable | Exposed | Note |
|---|---|---|---|---|
| `url_canonical` | source URL + canonicalization vN | no | `id`, `url` | key with `generation` |
| `generation` | `CC-MAIN-2026-43` | no | no | |
| `url_original` | `WARC-Target-URI` | no | no | traceability |
| `warc_ref` | file, offset, length (columnar index) | no | no | provenance, range re-read |
| `crawled_at` | `WARC-Date` | no | TBD | **≠ publication date** |
| `title` | `<title>`, then `og:title` (versioned rule) | yes | `title` | |
| `published_date` | meta / JSON-LD `datePublished` | yes | `publishedDate` | never `WARC-Date`, never `Last-Modified` |
| `author` | meta / JSON-LD | yes | `author` |
| `lang` | detector vN (columnar index as hint) | no (`und`) | filter? | document attribute |
| `text_canonical` | extractor vN + normalization | no | `text` | **reference for all offsets** |
| `content_hash` | sha256(`text_canonical`) | no | no | exact dedup, idempotence |
| `extractor_version` | — | no | no | |
| `exclusion` | takedown, opt-out, PII | no (default: none) | no | **plan now** |
| `robots_directives` | `<meta name="robots">`, `X-Robots-Tag` | no | no | `noindex`, `nosnippet`, `max-snippet`, `noarchive` |
| `tdm_reserved` | TDMRep meta/header | no | no | site-level `/.well-known/tdmrep.json` not read in v1 |

### 4.1.2 Passage spec (S4 step 3, open)

- **Size unit:** **model-independent reference unit** (default **UAX #29 words**, versioned in `chunker_version`). The model tokenizer is a **constraint only**: `budget_passage = max_tokens_effective − special tokens − doc prefix − title`. Target size must fit p99 for the hungriest candidate (T0). Residual overflow truncated at embedding, no re-chunk, threshold.
- **Boundaries:** paragraph → sentence → hard cut as last resort.
- **Title:** not stored in the passage text; added at index time (embedding/BM25) via a parameter. Offsets stay clean.
- **Min length:** short passage merged with previous, not dropped; short document excluded with a reason code.
- **`passage_id`:** (`url_canonical`, `generation`, `content_hash`, `chunker_version`, ordinal) + `[start, end)` on `text_canonical`.
- **`chunker_version`:** reference unit + version + sentence splitter version + parameters; **not** the model tokenizer (D60).
- **BM25 floor (D19):** computed on the **same unit** as the system.

> Skeleton: `docs/s4_passage_spec_skeleton.md` — all numeric values `TBD-B`; frozen as **D44** after the B measurements.

### 4.1.3 Extractor & canonicalization (S4 step 2)

**Extractor (D42):** trafilatura default; version + config frozen (charset: HTTP header → `<meta charset>` → auto; normalization: NFC, LF, whitespace, `\n\n` paragraphs; `favor_precision` vs `favor_recall` after manual review). Fallback: resiliparse for text + separate metadata. Validate on T0: throughput, 50 docs/lang manual review, golden-set docs not emptied.

**Canonicalization (D43):** `canon-v1`, syntactic, conservative, shared by pipeline and API, frozen per generation. Steps: WHATWG parse → lowercase scheme/host → punycode → default port → fragment → dot segments → percent encoding → closed tracking-param list. **Not** identity: http/https, `www`, trailing `/`, query sort, path lowercase, `rel=canonical` (stored as `canonical_hint` for dedup only). Collisions: latest `WARC-Date`, tie-break (file, offset), log `canon_collision`.

**UTF-8 offsets:** store **byte** offsets; Python indexes code points → one tested conversion; highlights must not shift on non-ASCII (critical for French).

**Dedup:** exact by `content_hash`; keep all docs, index **one representative**; others get `dup_of` + API status `not_in_index` (D20). Near-dup (MinHash) later, measured on T0.

**Language:** **GlotLID (D76)** default, threshold, `und` below; columnar index as hint/cross-check. (fastText `lid.176` only if D57 is extended to tool models.)

**Quality filters:** min length, short-line ratio, versioned; reason codes, never silent.

**Exclusion/PII/takedown:** `exclusions(url_canonical|host, reason, added_at)` applied at build and serving; PII detection later; robots.txt at crawl ≠ opt-out.

**Per-page signals (D51):** `noindex` → not indexed; `nosnippet`/`max-snippet:N` → no text or truncated; `noarchive` → no full text; TDM reservation → excluded. Site-level `/.well-known/tdmrep.json` not read in v1 (network outside WARC); noted limit.

### 4.2 Index record (binary, what the ANN core stores)

> **Historical — replaced by D82** (R0 exact GPU bf16 / R1 binary + int8 rescoring; no IVF/centroids). Kept for reference.

```text
doc_id:      u64
centroid_id: u32
codes:       [u8; 32]   // 256-bit binary embedding
```

8 + 4 + 32 = **44 B per record**, before list/offset overhead.

Plus sidecars: centroids (`f32`), IVF lists (`u32`), doc_ids (`json`), filter bitmaps (roaring).

### 4.3 Content store record (byte-offset index)

```text
doc_id -> (shard_id, offset, length)
```

### 4.3.1 Content store design (D48–D50)

- **Build form:** immutable columnar shards `docs/<stage_key>/shard-NNNNN.<ext>`; metadata columns (`url_canonical`, `title`, `lang`, `content_hash`, `dup_of`, `exclusion`) separate from `text_canonical`. A stage that needs only metadata does not read text.
- **Serving form:** derived `docstore` stage mapping `id → (shard, row group, row)`; texts **not** in Postgres.
- **Passages:** offsets only, same shard as their document; no text duplication.
- **Sharding:** `hash(url_canonical) mod N`, `N` in the build spec; passages co-located with their document.
- **Format:** Parquet + mapping table default; decision rule measures p95 id read, sequential throughput, size (D50).
- **Compression:** zstd per column; level chosen on T0; dictionary encoding for low-cardinality columns.
- **Dedup:** `dup_of` docs stay for `/contents` (`not_in_index`); if exact-dup rate > threshold, store text once per `content_hash`.
- **Budget formula:** `store ≈ N_docs × (compressed text + metadata) + N_docs × r × passage entry + docstore table`; allocate the 500 GB across stages in S5/S6.
- **`/contents` read path:** canon-v1 → hash → shard → mapping → row → `text_canonical` → exclusions at serving → `maxCharacters` → per-item status.

### 4.4 Manifest / provenance (per index)

```jsonc
{
  "index_version": "1",
  "n_docs": 0,
  "n_centroids": 0,
  "dim": 256,
  "quantization": "binary",
  "embedder": {"model": "…", "revision": "…", "dim": 256},
  "corpus": {"crawl_id": "…", "docs_sha256": "…", "n_docs": 0},
  "git_sha": "…",
  "created_at": "…",
  "files": {"<path>": "<sha256>"}
}
```

### 4.5 Identity & API key schema (v1, → D2–D7)

**Engine:** Postgres for **identity, keys, usage, bans, and metadata**, including dev. SQLite only for pure unit tests that need no Docker. The **dense** and **lexical** backends are separate, open choices (S6) — do not prescribe `pgvector` or `ts_rank` here.

**Tables:**

```sql
-- v1: single operator, but the table exists for B/C
CREATE TABLE accounts (
    id              UUID PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    display_name    TEXT,
    status          TEXT NOT NULL DEFAULT 'active',   -- active | suspended | banned
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ,
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY,
    account_id      UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    org_id          UUID,                            -- NULL in v1; B/C extension
    project_id      UUID,                            -- NULL in v1
    name            TEXT NOT NULL,                    -- human label
    prefix          TEXT NOT NULL UNIQUE,             -- first chars, for lookup
    hash            BYTEA NOT NULL,                   -- HMAC-SHA256(pepper) of the full key, never plaintext (D3)
    hash_version    SMALLINT NOT NULL DEFAULT 1,      -- pepper/keyed-hash version (D3, D6)
    scopes          TEXT[] NOT NULL DEFAULT '{search:lite,search:auto,contents:read}',
    status          TEXT NOT NULL DEFAULT 'active',   -- active | revoked | expired
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,                      -- default 1 year (D5)
    rotated_from    UUID REFERENCES api_keys(id),     -- unidirectional (D6)
    revoked_at      TIMESTAMPTZ,
    revoked_reason  TEXT                             -- mandatory enum (D7)
);
CREATE INDEX ON api_keys (account_id);
CREATE INDEX ON api_keys (prefix);

-- append-only ledger: observability, quotas, cost/resource attribution
CREATE TABLE usage (
    id              BIGSERIAL PRIMARY KEY,
    account_id      UUID NOT NULL,
    key_id          UUID NOT NULL,
    request_id      TEXT NOT NULL,
    endpoint        TEXT NOT NULL,                    -- /search | /contents | mcp:web_search_exa
    tier            TEXT,                             -- lite | auto | deep | NULL
    status_code     INT NOT NULL,
    error_tag       TEXT,
    latency_ms      INT,
    gpu_ms          INT,                              -- resource observability
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON usage (key_id, created_at);
CREATE INDEX ON usage (account_id, created_at);

CREATE TABLE bans (
    id              UUID PRIMARY KEY,
    account_id      UUID REFERENCES accounts(id) ON DELETE CASCADE,
    key_id          UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    reason          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ,
    active          BOOLEAN NOT NULL DEFAULT true,
    CHECK (account_id IS NOT NULL OR key_id IS NOT NULL)
);

CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    actor_id        UUID,
    action          TEXT NOT NULL,                    -- key.create | key.revoke | account.ban | ...
    target_type     TEXT,
    target_id       UUID,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Key format:** `exa1_<prefix>_<secret>`; store `prefix` (lookup) + **HMAC-SHA256(pepper)** hash + `hash_version` (never plaintext, D3); scopes `search:lite`, `search:auto`, `contents:read` (no `admin` in v1, D4); optional expiry (D5); rotation = new key + revoke old (D6); revocation immediate (D7).

**Rate limit state:** in-memory per process in v1 (token bucket per key/tier/IP); `RateLimitStore` seam for Redis/DB later. Note: in-memory resets on restart — acceptable for a single node, not for multi-node.

**B/C extension points (no v1 code):** `orgs`, `memberships`, `projects`, `quotas`; `api_keys.org_id` already nullable; accounts remain, orgs reference them; org-scoped keys, per-org quotas, roles.

**Justification:**
- Relational integrity (keys→accounts), audit, usage queries.
- Hashed keys — no plaintext leak.
- Usage ledger for observability, quotas, and cost/resource attribution.
- Bans + audit for admin/compliance.
- Nullable `org_id`/`project_id` make B/C additive, not a rewrite.

**Storage architecture (placement):**
- `DocumentStore` and `PassageStore` are **ports** in `ports/` (D85/D95; superseded `services/ports.py`); the domain never imports Postgres.
- The Postgres implementation lives in `adapters/outbound/store/` (D95; superseded `adapters/store/`).
- **Source of truth:** Postgres — page identity, documents, passages, metadata, `index_version`; later monitors and API keys.
- **Lexical:** **BM25** baseline (own implementation or a backend that actually produces BM25). If we use `ts_rank`, name it `ts_rank` — it is not BM25.
- **Dense:** **R0 exact GPU / R1 binary + int8 rescoring (D82)**; `pgvector`/HNSW/FAISS/DiskANN/CAGRA are **not** v1 options (MRL/HNSW/PQ excluded, D82).
- **Tests:** testcontainers or docker compose with real Postgres; domain tests stay pure.
- **Limit:** the dense backend's memory/latency curve is measured in S6; do not assume pgvector's limits.

### 4.6 Key lifecycle (Gate 2b, → D6/D7)

**Breakdown:** 2b.1 generation & storage · 2b.2 scopes · 2b.3 expiration · 2b.4 rotation · 2b.5 revocation.

**2b.1 Generation & storage (D3):**
- Format: `exa1_<prefix>_<secret>`.
- `prefix`: 12 alphanumeric chars, unique, indexed.
- `secret`: `secrets.token_hex(32)` → 64 hex chars (no `_`, unambiguous).
- Validate lengths before any DB lookup: prefix 12, secret 64.
- DB: `key_id` (UUID), `account_id`, `prefix` (unique), `hash` (HMAC-SHA256(pepper, secret), `BYTEA`), `hash_version` (smallint), `name`, `scopes`, `status`, `created_at`, `last_used_at`, `expires_at`, `revoked_at`.
- Lookup: parse prefix → fetch key row → HMAC the full key → constant-time compare.
- Pepper from a secret manager; `hash_version` supports rotation.
- Auth failure: uniform response for unknown prefix vs invalid secret (same code, similar timing); never log the full key, only the prefix.
- `last_used_at`: update only if older than 1 minute, or async/batched.
- Key cap (20): transactional (`SELECT ... FOR UPDATE` on the account) or a DB constraint.
- Display: `exa1_<prefix>_…` + name + last used; the full key is shown **once** at creation.

**2b.2 Scopes (D4):**
- v1: `search:lite`, `search:auto`, `contents:read`.
- Later: `search:deep`, `answer`, `monitors:write`.
- **Explicit, no hierarchy:** `search:auto` does **not** imply `search:lite`; the check is `scope in key.scopes`.
- **Route-level check:** a dependency takes the required scope as an argument; the service does not know about scopes.
- **Domain type:** `Scope` as a `StrEnum`; DB stores the string. Adding `search:deep` later is an enum change, not a data migration.
- **Key management:** local CLI (`search-admin keys create|list|revoke`) as an adapter calling `ApiKeyService`; **no `admin` scope in v1**. Remote admin later, with a real authenticated identity + role.

**2b.3 Expiration (D5):**
- Default: `expires_at = now + 1 year` for new keys; `--no-expiry` to disable; shorter expiry allowed at creation.
- **Auth rule:** `status == 'active' AND (expires_at IS NULL OR expires_at > now())`. The cron/job only updates `status` for display/audit — it is **not** the source of truth.
- Expired key → 401 with stable tag `key_expired`; "unknown prefix" stays uniform.
- `expires_at` stored/compared in **UTC**.
- **Inject the clock** (like `Deadline`) so expiry is testable without sleeping.
- CLI `keys list` shows keys expiring within **14 days** with a marker — otherwise the 1-year default only produces surprise 401s.

**2b.4 Rotation (D6):**
- Default: **grace 24h** (both keys valid during overlap); `--no-grace` for immediate revocation.
- **Max grace: 7 days**, server-configurable; reject larger at `rotate`.
- **Refuse rotation if the old key is still in grace** — no chains of active keys.
- Schema: `rotated_from` (UUID, nullable, **no cascade**), `grace_until` (timestamptz, nullable).
- Auth rule: `status == 'active' AND (grace_until IS NULL OR grace_until > now())`; cron updates status for display/metrics, auth is authoritative.
- Audit: `key.rotate` records `old_key_id`, `new_key_id`, `mode` (grace|immediate), `grace_until`.
- **Pepper rotation:** add a version, lazy/batch rehash; before retiring a version, query remaining keys per `hash_version` (one-line count) — do not retire while count > 0.
- No auto-rotation in v1; the 14-day warning (2b.3) is the reminder.

**2b.5 Revocation (D7):**
- Immediate, **soft**: `status='revoked'`, `revoked_at`, `reason`.
- `reason` is **mandatory and enumerated**: `compromised`, `departed`, `abuse`, `rotated`, `other` (free text required if `other`). CLI refuses without `--reason`.
- **Idempotent:** if already revoked, do not change `revoked_at` or `reason`; return the existing state, no error.
- **Cache invalidation:** short auth-cache TTL (≤30s) **and** explicit invalidation on `revoke` (pub/sub or versioned cache key). Document the residual window.
- CLI: `search-admin keys revoke <key_id> --reason <enum> [--note "..."]`.
- Bulk: `revoke --account <account_id> --yes [--dry-run]`; `--dry-run` lists affected keys; `--yes` required.
- Audit: `key.revoke` with `key_id`, `reason`, `note`, `actor`.
- No cascade delete; usage/audit remain.
- **A revoked key never becomes active again**, even if referenced by `rotated_from` (informative only).
- **Account ban (2d):** blocking the account also blocks new key creation — check in `ApiKeyService.create`, not just the CLI.

### 4.7 Surface matrix (Gate 2a, D8)

| Surface | Keyless | Keyed | Params | Defaults |
|---------|---------|-------|--------|----------|
| MCP `web_search_exa` | yes | yes | `query`, `objective`, `numResults` | `numResults=10` |
| MCP `web_fetch_exa` | yes | yes | `urls[]`, `maxCharacters` | `maxCharacters=3000` |
| HTTP `POST /search` | yes (low limits) | yes | `query`, `type`, `numResults`, `contents`, `objective`, filters | `type=auto`, `numResults=10` |
| HTTP `POST /contents` | yes (low limits) | yes | `urls`/`ids`, `text`, `highlights`, `maxCharacters` | `maxCharacters=3000` |

**v1 subset:**
- `/search`: `type` = `lite` | `auto` (`deep` → 400 `unsupported_value`, D27); `contents` = `text` | `highlights`; filters `includeDomains`, `excludeDomains`, `startPublishedDate`, `endPublishedDate`, `category`, `numResults`; `objective` optional.
- `/contents`: `urls`, `text`, `highlights`, `maxCharacters`.
- MCP: exactly the two keyless tools; `objective` **required** on `web_search_exa`.
- **S2 v1.1 (backward-compatible, D67/D69):** `score` normalized via sigmoid in [0, 1]; single `degraded` field (reasons `bm25_only`, `rerank_skipped`, …), absent/empty when nominal. Gate 0 unchanged.
- **Designed for, not built:** `deep`/`deep-lite`/`deep-reasoning`, `outputSchema`, `additionalQueries`, `summary`, `maxAgeHours`, `subpages`, `/answer`, `/findSimilar`, `/context`, Agent, Monitors, Websets. Contracts in §3.11.

### 4.8 Rate limits & quotas (Gate 2c, D9)

**Model:** two **independent** limits per key (and per IP for keyless):
- **Token bucket** per `(key_id, tier)` for short-term rate.
- **Windowed counter** per `(key_id, day)` for the daily cap.
- Both must pass; `RateLimit-*` headers reflect the **most restrictive**.

**Values:**

| Scope | Endpoint / tier | Rate | Burst | Daily |
|-------|-----------------|------|-------|-------|
| Keyless (per IP) | any | 3 QPS | 3 | 150/day |
| Keyed | `/search` lite/auto | 10 QPS | 10 | — |
| Keyed | `/search` deep | **5 QPS** | 5 | — |
| Keyed | `/contents` | 100 QPS | 100 | — |
| Keyed | MCP | 10 QPS | 10 | — |

**Design:**
- **Keyless IP:** per-IP quota; read `X-Forwarded-For` **only behind a trusted proxy**; never trust raw XFF (spoofable); document the NAT/CGNAT tradeoff.
- **Separate buckets** per endpoint and per tier: `/contents` separate from `/search`; `deep` separate from `lite`/`auto`.
- **Headers:** `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` for the **tier of the current request**; don't mix tiers.
- **429** = this client exceeded its limit (+`Retry-After`); **503** = system saturated regardless of client (+`Retry-After`). Keep separate in metrics.
- **Store:** in-memory in v1; `RateLimitStore` seam for Redis/Postgres. **Note:** multi-replica in-memory gives N× the limit; v1 single-instance is the only valid limit measurement. Add Redis/Postgres before the horizontal load demo.
- **Isolation:** limit isolation is not enough if tiers share a GPU worker pool — `deep` saturation raises `lite` latency. Need separate queues per tier, dedicated workers, or a concurrency cap per tier. This is a transport/2d concern, not the rate limiter.

### 4.9 User management & bans (Gate 2d, D10)

**Accounts:** created by the operator via CLI; status `active | suspended | banned`.

**Suspend (reversible):**
- Blocks new key creation.
- All existing keys return 401 `account_suspended` — keys remain `active` in DB, **not** revoked.
- Unsuspend → keys valid again.
- Requires an **account status check at auth**, not just at key creation.
- Cache: account status cached with the same TTL as keys; suspend/unsuspend invalidates key + account cache entries.

**Ban (terminal in v1):**
- Revokes all keys (`status='revoked'`).
- Blocks new key creation.
- **Auth check `account.status == 'banned'` is the real guarantee** — even if a key was recreated by a race.
- **No `ban_expires_at` in v1**; a ban is lifted by the operator.
- Unban does **not** recreate keys; the operator must reissue.
- Cache invalidation on ban/unban.
- CLI `accounts ban --yes [--dry-run]`; `--dry-run` lists the keys that will be revoked.

**Reason enum (shared with key revocation):** `compromised`, `departed`, `abuse`, `fraud`, `payment`, `legal`, `rotated`, `other` (free text required if `other`). One enum for revocations and bans.

**Audit:** `account.create`, `account.suspend`, `account.suspend.end`/`account.unsuspend`, `account.ban`, `account.unban` (with reason).

**CLI:** `search-admin accounts create|list|show|suspend|unsuspend|ban|unban`.

**B/C:** orgs/teams later; `accounts` remains, `orgs` reference accounts.

### 4.10 Error semantics (Gate 2f, D11)

**HTTP envelope:** Exa's `{requestId, error, tag}` (drop-in), **not** RFC 9457. Add `X-Request-Id` header (same value as body). Accept a client `X-Request-Id` only after format validation.

**Status codes / tags:**

| Status | Tag | Meaning |
|--------|-----|---------|
| 400 | `invalid_request` | bad param/type/JSON; generic `detail`, no internal schema |
| 413 | `payload_too_large` | body/result exceeds the size limit (D91); check before parsing |
| 415 | `unsupported_media_type` | wrong/absent `Content-Type` (D21) |
| 409 | `index_version_mismatch` | pinned `X-Index-Version` ≠ served build (D99) |
| 401 | `unauthorized` | missing/invalid key; **uniform for unknown prefix and wrong secret** (same code, similar timing; dummy hash if no row) |
| 401 | `key_expired` | valid key, expired (only revealed after secret validation) |
| 403 | `forbidden` | valid key, missing scope |
| 403 | `account_suspended` / `account_banned` | valid key, account status (only after secret validation) |
| 404 | `not_found` | public resource (doc/url); admin is CLI-only, no 404 leak |
| 429 | `rate_limited` | client limit; `Retry-After` |
| 503 | `service_unavailable` | system saturated; `Retry-After` |

**Auth order (strict):**
1. Parse prefix; if no row → dummy hash → `unauthorized` (same timing).
2. Verify secret; if invalid → `unauthorized`.
3. Only after secret validation: check expiry → `key_expired`; check account status → `account_suspended`/`account_banned`; check scope → `forbidden`.
4. Never reveal account status for an unauthenticated key.

**Compatibility note:** the envelope + HTTP codes are drop-in; the tags `key_expired`, `account_suspended`, `account_banned` are **our own** (not verified against Exa). Document compatibility at the envelope/code level; mark custom tags.

**MCP errors:**
- Protocol errors (unknown method, invalid JSON-RPC params) → JSON-RPC error.
- Tool/business errors (key refused, rate limit, timeout) → tool result with `isError: true` + text. **Never** a JSON-RPC error, or the agent misinterprets the failure.

**No leak:** generic messages; details in logs with `request_id`; never echo the key or stack.

---

## 5. Baseline to measure first (before any change)

These are the current repo's measured numbers. We do not change anything until we can reproduce/extend them.

| Metric | Current | Source |
|--------|---------|--------|
| Tier-0 tests | 230 passed, 1 skipped, 7 deselected | `pytest` |
| Rust tests | 29 passed | `cargo test` |
| Toy **target** recall@10 (50 known-target questions, reranked) | 0.740 | `EXPERIMENTS.md` |
| 2.58M **target** recall@10 (exact-id, reranked) | 0.359 | `EXPERIMENTS.md` — **box-only, unverified** |
| 2.58M p50 / p99 | 75.562 ms / 131.151 ms | `EXPERIMENTS.md` — **box-only, unverified** |
| Corpus | 2,576,778 docs / 130 WET (not "1M") | `EXPERIMENTS.md` |
| Rerank cost | 0.59 ms/pair (MiniLM-L6) | `EXPERIMENTS.md` |

**These are not ANN recall.** They are target recall on known-target sets. ANN recall vs brute force and quantization recall are **unmeasured**. The box-only rows are not gate evidence until reproduced.

**Known defects to fix structurally (from `AUDIT_REPORT.md`):** H1 query OOB read; H2 query prompt omitted; H3 index reuse ignores K; H4 stale filter bitmaps; H5 config override; H6 example config fails; H7 tests at wrong operating point; H8 stale doc counts.

---

## 6. Decision log

| ID | Decision | Evidence | Date |
|----|----------|----------|------|
| D0 | Use a living research/decision doc; measure before decide | project owner | 2026-11-22 |
| D1 | v1 architecture-complete = L0–L2; v1 releasable = L0–L2 + L3 + L4 on the reference box; L5 = scale proof, not v1 | project owner | 2026-11-23 |
| D2 | v1 tenancy = A (single operator) + a real accounts/keys/usage/bans DB; B/C (orgs/teams) designed as later extensions | project owner | 2026-11-24 |
| D3 | Key format `exa1_<12-char prefix>_<64-hex secret>`; HMAC-SHA256(pepper) with `hash_version`; fixed-length validation; uniform auth failure; throttled `last_used_at`; transactional key cap | project owner | 2026-11-24 |
| D4 | Scopes explicit, no hierarchy (`scope in key.scopes`), checked at the route; `Scope` StrEnum in domain; key management via local CLI adapter (no admin scope in v1) | project owner | 2026-11-24 |
| D5 | Key expiry default 1 year (`--no-expiry` to disable); auth checks `status=active AND expires_at > now()`; cron is not the source of truth; UTC; injected clock; CLI warns at 14 days | project owner | 2026-11-24 |
| D6 | Key rotation: 24h grace default, max 7 days, refuse if old key in grace, unidirectional `rotated_from` (no cascade), audit both ids; pepper retirement gated by a per-`hash_version` key count | project owner | 2026-11-24 |
| D7 | Key revocation: mandatory enum reason, idempotent (no overwrite), short auth-cache TTL + explicit invalidation, bulk requires `--yes`/`--dry-run`, account ban blocks key creation, revoked never reactivates | project owner | 2026-11-24 |
| D8 | v1 surface matrix: MCP `web_search_exa`/`web_fetch_exa` + HTTP `/search` (lite/auto, contents text/highlights, filters) + `/contents`; keyless allowed; later endpoints designed-for | project owner | 2026-11-24 |
| D9 | Rate limits: token bucket + windowed daily counter (both must pass); keyless 3 QPS/150/day per trusted IP; keyed 10 QPS search, 5 QPS deep, 100 QPS contents; separate buckets per tier/endpoint; 429 vs 503 distinct; in-memory v1 with Redis/Postgres before horizontal demo | project owner | 2026-11-24 |
| D10 | Accounts: suspend blocks key usage + creation (reversible, keys kept); ban revokes all + blocks creation (no expiry, unban does not recreate); both checked at auth and invalidate cache; shared reason enum | project owner | 2026-11-24 |
| D11 | Errors: Exa envelope `{requestId,error,tag}` + `X-Request-Id`; strict auth order (uniform unauthorized, status only after secret validation); 429 vs 503 with Retry-After; MCP protocol errors = JSON-RPC, tool errors = `isError:true`; custom tags marked non-Exa. **Amendment (D91):** 413 `payload_too_large` added (size limits). **Amendment (D99/D21):** 409 `index_version_mismatch` (D99) + 415 `unsupported_media_type` (D21) added. | project owner | 2026-11-24 |
| D12 | Gate 0: `/search` (lite+auto) + `/contents` on a real toy index; `/search`→`/contents` path; 400 on both routes; no MCP startup; no filters/404 in Gate 0; keyless is our test config | project owner | 2026-11-24 |
| D13 | Quality protocol: 3d sweep `nprobe` only, exact reference uses the same LUT score, select by p95 sub-budget not the knee; 3e three lists F/Q/A (gaps don't add); 3f three coverage measures (URL / evidence / indexed passage) with loss breakdown. **Amendment:** the `nprobe`/IVF operating point is **replaced by D82** (R0/R1 scan the whole index, no IVF); history kept. | project owner | 2026-11-24 |
| D14 | Ranking gate: `auto` non-inferiority vs Exa (two-sided 95% CI, δ=0.05 candidate) + superiority vs BM25 (relative floor); `lite` reported + BM25-floored, no Exa gate; `success@3` diagnostic; ablation primary = query+objective vs BM25 query-only, 3 Exa conditions on dev | project owner | 2026-11-24 |
| D15 | Gate 4: lite/auto budgets are pilot targets; tier must meet latency + useful throughput + resources in the same run; deep out of v1; open arrival rate; capacity vs quota tests; per-tier isolation; one reference box + corpus; memory margin in GiB | project owner | 2026-11-24 |
| D16 | Load test: k6 constant-arrival-rate; ~10 min plateau + drain; isolated/mixed/saturation→recovery/cold; per-route offered load; planned vs sent vs successful; frozen request profile; time series; full suite per RC + nightly | project owner | 2026-11-24 |
| D17 | Gate 5: v1 ops guarantees vs L5 scale proof; same code/contracts, only placement/resources/params change; shard/replica/node/GPU distinct; byte-exact artifact manifest + run manifest; 3 provenance proofs; OTel+metrics+JSON logs; digest-promoted CI/CD; no partial success on integrity/shard loss; simulated/unexecuted/passed distinct. **Amended: per-pool metrics (D89: encode/search/contents) added to 5d.** | project owner | 2026-11-24 |
| D18 | Reconciliation: release v1 = Gates 0–4 + v1 subset of Gate 5 on the S3 reference profile; no 1–2B minimum; deep out of gates; gate status = protocol vs evidence (not executed/blocked/failed/validated); Exa comparison blocked → a release may publish without a parity claim; Postgres = identity, dense/lexical backends open; **page identity = (generation, url_canonical); content_hash is an attribute** | project owner | 2026-11-24 |
| D19 | Release v1 does not wait for Exa parity: Exa comparison is diagnostic/LATER until ToS clearance; quality gate rests on the BM25 floor + an absolute threshold; release may state "compatibility on the documented subset; Exa ranking parity not demonstrated" | project owner | 2026-11-24 |
| D20 | `/contents` exactly one of `ids`/`urls` (XOR); `id` = canonical URL, `ids` deprecated alias; per-item statuses; all fail → 200 | project owner | 2026-11-24 |
| D21 | `Content-Type` wrong/absent → 415 `unsupported_media_type` | project owner | 2026-11-24 |
| D22 | MCP stdio: env credentials; absent/invalid → refuse start; expiry/suspension → `isError` | project owner | 2026-11-24 |
| D23 | MCP HTTP: 401 transport + `WWW-Authenticate`; scope → 403 transport; invalid args → `isError`; unknown tool → JSON-RPC; spec 2025-11-25 | project owner | 2026-11-24 |
| D24 | Auth v1: `x-api-key` + Bearer HTTP; keyless by config; MCP HTTP bearer; stdio env; OAuth LATER | project owner | 2026-11-24 |
| D25 | Versioning: no `/v1` prefix; contract version + response header | project owner | 2026-11-24 |
| D26 | MCP `numResults` integer 1–100; `objective` required (CHOICE) | project owner | 2026-11-24 |
| D27 | Unsupported → 400 `unsupported_field`; default-valued fields accepted; `type: deep` → 400 `unsupported_value` | project owner | 2026-11-24 |
| D28 | Source: **CC-MAIN-2026-43** (hash of `warc.paths.gz`, consultation date); selection via the **columnar index** (status 200, HTML, lang ∈ {eng, fra}); **range requests**; internal measurement only, no public exposure; CC ToS cited with date. Close: T0 selection manifest produced + hashed. | project owner | 2026-11-24 |
| D29 | Document = canonical URL in an index generation; passage spec frozen (extractor+version, tokenizer, target size, overlap, title handling, min length); passage id = (url_canonical, generation, content_hash, chunker_version, ordinal); **language = attribute of doc and passage**; ratio r **measured** on T0. Close: passage spec frozen + r measured. | project owner | 2026-11-24 |
| D30 | Nested tiers: filter (lang, dedup, quality) **before** permutation; one permutation **per language** (hash of URL + fixed salt); tier = EN prefix + FR prefix at a frozen ratio (**80/20 proposed**); duplicates keep first in permutation order; T0 ~10k, T1 ~1M (800k EN + 200k FR), T2 ~10–25M (new decision). Close: T0 ⊂ T1 verified by manifest. | project owner | 2026-11-24 |
| D31 | Coverage 3f per tier and per language cohort; recall interpreted only on covered queries; no injection of relevant docs in the primary condition; D19 absolute threshold states its tier (T1 proposed) and applies to **EN only**; FR cohort diagnostic in v1. Close: threshold quantified and frozen before first run. | project owner | 2026-11-24 |
| D32 | Artifact reuse = diff(ideal, actual); map stages per element; global stages (centroids, PQ codebooks, BM25 stats) content-addressed, grouped in builds; idempotence key excludes resources (GPU/batch/node/Modal), with a tested numerical tolerance; manifest committed last; GC of unreferenced artifacts | project owner | 2026-11-24 |
| D33 | Golden-set language: **English primary** (gate, D93); **French = fixed diagnostic cohort `N_FR = 100`, not gated** (D93); flip if the target users are French. **Amendment (D93):** FR = fixed diagnostic cohort 100, not gated. | project owner | 2026-11-24 |
| D34 | Reference hardware profile (measurement, not architecture): RTX Pro 6000 96 GB VRAM, 128 GB RAM, 16 vCPU; the system must also run on 5090 / B300 / multi-node | project owner | 2026-11-24 |
| D35 | Phase constraint: during planning, allowed = reference-corpus acquisition (**CC-MAIN-2026-43**, **≤500 GB total** incl. columnar index + records + T0/T1 artifacts, internal measurement only, no public exposure; raw WARC retention 90 days; extracted text/passages/frozen outputs retained for the index generation; deletion per manifest + GC), T0/T1 build (ingest/embed/index) + measurement harness. This code is the **candidate pipeline**, respects D32, **not throwaway**. Serving/API only for Gate 0 on T0 once S2 is frozen `v1.0-gate0`. T2+ new decision. Modal off for T0/T1; re-evaluate for T2 if embedding >48 h. | project owner | 2026-11-24 |
| D36 | Reference measurement profile: 1× RTX Pro 6000 (96 GB), 128 GB RAM, 16 vCPU, **500 GB NVMe ephemeral scratch**; Gate 4 with build stopped; Modal off T0/T1; profile is a parameter, not an architecture constraint. **The Thinkpad (Ryzen 5 4500U, 24 GB RAM) is NOT a build machine** — docs/code only. | project owner | 2026-11-25 |
| D37 | Language ratio **80/20 EN/FR**, applied per tier as prefixes of two separate permutations (D30); the corpus is deliberately non-representative; the FR share in EN top-10 is measured in diagnostic; changing the ratio breaks tier nesting and requires a new decision. | project owner | 2026-11-25 |
| D38 | Corpus cache & reuse: acquisition is **one-time**; durable store = **HF bucket** (`exa-replica`, S3-like), content-addressed; manifest = (file, offset, length, digest); pipeline runs read from the cache, **never re-download**; cloud tests use derived artifacts (docs/vecs/index) or the HF bucket; **HF budget ≤2.5 TB of the 2–3 TB free**; T0/T1 ≤500 GB; **Modal persistent <1 TB** (working only); RTX local 500 GB = scratch/cache; quota guard before download; raw WARC retention 90 days; derived artifacts for the index generation; deletion per manifest + GC; T2+ new decision. | project owner | 2026-11-25 |
| D39 | Execution & data locality: heavy work (ingest/embed/index) runs **only** on the RTX PRO 6000 machine or Modal; the Thinkpad never builds. HF bucket is durable; Modal persistent is working-only and synced back; RTX scratch is ephemeral and rebuildable from HF. No repeated downloads. | project owner | 2026-11-25 |
| D40 | Storage layout **Option B**: two private HF buckets — `exa-replica-corpus` (write once, then read-only) and `exa-replica-artifacts` (builds write, no overwrite, content-addressed paths `<stage>/<hash>/`); manifests in a versioned private repo `exa-replica-manifests` (commits/tags per generation), **not** in a bucket; T2 raw WARC streamed to scratch and deleted, not stored in HF. | project owner | 2026-11-25 |
| D41 | S4 order: **minimal document schema + canonical text as offset reference** → extractor + cleaning → passage spec parameterized and measured on T0. v1 **rebuilds everything per generation**, no incremental. Content store and freshness deferred until after T0 measurements. | project owner | 2026-11-25 |
| D42 | Extractor: **trafilatura** default, version + config frozen (charset, normalization, `favor_precision`/`favor_recall` after review); fallback resiliparse for text + separate metadata. Validate on T0: throughput, 50 docs/lang manual review, golden-set docs not emptied. | project owner | 2026-11-25 |
| D43 | URL canonicalization **canon-v1**: syntactic, conservative, shared by pipeline and API, frozen per generation. WHATWG parse, lowercase scheme/host, punycode, default port, fragment, dot segments, percent encoding, closed tracking-param list. No http/https merge, no `www`, no trailing slash, no query sort, no path lowercase, no `rel=canonical` (stored as `canonical_hint` for dedup only). Collisions: latest WARC-Date, tie-break (file, offset), log `canon_collision`. | project owner | 2026-11-25 |
| D44 | Passage spec frozen after the **B** measurements: all numeric values `TBD-B` in `docs/s4_passage_spec_skeleton.md`. `chunker_version` = reference unit + version + sentence-splitter version + parameters; **excludes the model tokenizer** (amended by D60). Changing `chunker_version` changes every `passage_id`. **Frozen 2026-11-26 (Run B, RTX Pro 6000, `bench/results/run_b.json`):** tokens/word = **2.4755** (e5-small), 1899 docs → 6704 passages; `target_size`=**128 words**, `max_size`=**192 words** (400 words → 1.7% overflow > 0.5% threshold), `overlap`=**1 sentence**; `chunker_version`=`uax29-1.0;target=128;max=192;overlap=1`. | project owner | 2026-11-25 (frozen 2026-11-26) |
| D45 | **Generation vs build:** `generation` = frozen corpus (crawl, sampling, canonicalization); any other change creates a `build_id` (hash of the build manifest) under that generation. Serving points to a `build_id`. `passage_id` = (`url_canonical`, `generation`, `content_hash`, `chunker_version`, ordinal). | project owner | 2026-11-25 |
| D46 | Manifest v0: build manifest split into **spec** (input hashes, config, stage `impl_version`, model/tokenizer) and **result** (outputs, counts, timestamps, written last). `build_id` = sha256(JCS(spec)); `code_sha` is trace-only; stage keys = hash(spec + input keys); determinism test catches missed `impl_version` bumps. | project owner | 2026-11-25 |
| D47 | **Planning completeness (meta):** S4–S9 planning is complete when every open point has either a frozen decision or a decision rule (options, measurement, criterion, default). No execution before that. | project owner | 2026-11-25 |
| D48 | Content store: **two forms** — build form = immutable columnar shards (`docs/<stage_key>/shard-NNNNN.<ext>`, metadata columns separate from `text_canonical`); serving form = derived `docstore` stage mapping `id → (shard, row group, row)`. Texts **not** in Postgres. | project owner | 2026-11-25 |
| D49 | Passages stored as **offsets only** (`passage_id`, doc_id, `[start,end)`, ordinal), in the **same shard** as their document. Sharding = `hash(url_canonical) mod N`; `N` fixed in the build spec. | project owner | 2026-11-25 |
| D50 | Content-store decision rules: format **Parquet + mapping table** default (vs Lance-like; measure p95 id read, sequential throughput, size); dedup text once per `content_hash` if exact-dup rate > threshold; zstd level (measure size vs read/write throughput); `N = max(k × vCPU, compressed size / target shard size)` with target size measured on T0. | project owner | 2026-11-25 |
| D51 | Content policy `contents_policy ∈ {full, excerpt, none}`, set per deployment in serving config (not in `build_id`). v1 = internal only, `full`. Per-page signals (`noindex`, `nosnippet`, `max-snippet`, `noarchive`, TDM reservation) + `exclusions` applied in all modes; highlights follow `text`. Public exposure = separate gate (legal opinion, S2 v1.1 amendment for `excerpt`, takedown procedure); default `excerpt` then. | project owner | 2026-11-25 |
| D52 | Takedown: operator CLI; **append-only `exclusions` in Postgres** (outside builds); filter at serving on **all** output paths (`/search`, `/contents`, MCP, **after cache**), max propagation delay; build applies a snapshot (hash in spec); scopes `url`, `url_variants` (default), `host`, `host_suffix`, `content_hash`; excluded doc → `not_found`; physical **purge** for privacy/legal (only exception to D40); tests: rollback, cache, variants, duplicates, all paths. | project owner | 2026-11-25 |
| D53 | Retention: raw WARC 90 days (deleted after T2); extracted text/passages for the index generation (keep current + previous + gate-referenced builds); query logs TBD (hot/cold); snapshots per 3j. | project owner | 2026-11-25 |
| D54 | PII: exclusion table now; detection later with a decision rule (types, detector, action: mask or exclude). | project owner | 2026-11-25 |
| D55 | Licenses: code Apache 2.0; models Apache 2.0/MIT only (reject non-commercial; verify each model card); data Common Crawl ToS, no public exposure. | project owner | 2026-11-25 |
| D56 | S4 steps 6/8: v1 = full rebuild per build/generation (no incremental); live fetch LATER, with an interface seam. B1a/B1b classified in S4 (ingest metadata; WAT/WARC acquisition). | project owner | 2026-11-25 |
| D57 | Model licenses: accept **Apache-2.0 / MIT / BSD-2/3-Clause** (SPDX); reject non-commercial, RAIL/Gemma/Llama ToU, gated models. Verify at the **pinned HF revision** (repo tag, LICENSE, model card); conflicting sources → reject. Usage policy in addition to license → "accepted with reserve" if it doesn't restrict internal search; log. Tokenizer/base model checked too. Manifest: `model_id`, `revision`, weights hash, `license_spdx`, `checked_at`, usage note. | project owner | 2026-11-25 |
| D58 | Multilingual: **one common model for EN+FR, one index**; English-only reference in the comparison; decision on the golden set (EN primary, FR secondary, BM25 floor); freeze `X` (max loss vs EN reference) before the run; default = least costly candidate if not significant. | project owner | 2026-11-25 |
| D59 | **Single-vector in v1** (one vector per passage). Vector storage = `N_docs × r × bytes_per_vector` (dim/quantization in S6) [+ optional rescoring copy]. **Multi-vector (per-token) rejected in v1**: ~hundreds× single-vector (ColBERTv2 ~36 B/token → 256 tokens ≈ 9 KB/passage → 1B passages ≈ 9 TB), incompatible with D35. LATER behind `vector_kind ∈ {single}`. On-the-fly late interaction remains a reranker candidate. | project owner | 2026-11-25 |
| D60 | Passages chunked in a **model-independent reference unit** (default **UAX #29 words**, versioned in `chunker_version`). Model tokenizer is a **constraint only**: `budget_passage = max_tokens_effective − special tokens − doc prefix − title`. Target size must fit p99 for the hungriest candidate (T0). Residual overflow truncated at embedding, no re-chunk, threshold. Model change does not change `passage_id`. **Amends D44** (`chunker_version` excludes the model tokenizer). | project owner | 2026-11-25 |
| D61 | `PromptConfig` per model (query template, doc template with title slot, fixed instruction per build). Exact hashed strings from the model card / sentence-transformers config at the pinned revision. Part of the `embeddings` stage spec, **not** `chunker_version`. Serving reads it from the build manifest, refuses startup on divergence, verifies reference vectors. Query cache key includes its hash. Model comparison uses official prompts; ablation only on finalists (≤3 variants), default official unless gain > Y EN without loss > Z FR. `objective` as instruction = LATER. | project owner | 2026-11-25 |
| D62 | Weight precision = **native checkpoint dtype (bf16)** by default. Part of the model config in the `embeddings` stage spec (not `chunker_version`); identical at build and serving, verified at startup. **FP8** only if the T1 throughput projection exceeds the embeddings budget; accept per G/W/K frozen before the run. **INT4 LATER** (large reranker/generator only). Other GPUs out of D36 profile. | project owner | 2026-11-25 |
| D63 | Determinism: **exact stages** (docs, passages, BM25) bit-exact; **floating stages** (embeddings, PQ, index) idempotent by `stage_key` (spec), output comparison with tolerance (cosine ≥ threshold on a fixed sample); fix batch size, sorted passage order, library/CUDA/driver versions in the run record; reference vectors use the same tolerance. **Amends D46.** | project owner | 2026-11-25 |
| D64 | Two throughput rules. **Offline:** options (token budget per batch, length sort, precision, model size), T1 projection with `r` + margin, criterion `≤ budget_embeddings`, levers batching → fp8 → smaller model → tiers; token budget + sort in the embeddings spec. **Online:** dynamic micro-batching, criterion p95 ≤ its share of D15/D16 at target QPS. | project owner | 2026-11-25 |
| D65 | Build budget T1: scope = HF cache read → servable index + result manifest; excludes CC acquisition, evals, model-comparison runs; one embedding run (retained model). Caps: extraction ≤12 h (= B), embeddings ≤8 h bf16 (fp8 trigger), rest ≤4 h (soft), total ≤24 h. fp8: T0 tokens/s → estimate after T1 extraction/chunks → decide before the run; T1 actual decides. Model filter: >8 h on T1 (fp8 included) excluded unless new decision. CPU+GPU concurrent LATER. T2: embeddings likely >48 h → Modal re-evaluation. | project owner | 2026-11-25 |
| D66 | Online latency split (lite/auto): **Gate 4 = end-to-end p95 per tier only**; stage budgets are diagnostic, not gates. Indicative p95 caps (ms) lite/auto: overhead 50/50, query embed 50/50, BM25 50/80, ANN 100/150, fusion 10/20, rerank 0/800, contents 150/400, margin 190/950; adjustable after measurement if end-to-end passes. Measure on D36 **without a build running**; `/search` with contents; `/contents` separately. **Reranker filter: p95 >800 ms excluded.** Query encoder precision = build precision (or validated under D63). Deep: out of D66. **Amendment:** Contents split into store read (50/100) + highlights (100/300), sum ≤ Contents (D84). | project owner | 2026-11-25 |
| D67 | Reranker v1: **cross-encoder** behind an interchangeable interface; LLM listwise for deep later; late interaction LATER (D59). Tiers: auto (deep later), no rerank for lite. Input: query + top-50 from fusion, one pass; batch size perf-only (D63 tolerance). `max_pair_tokens ≥ query max + passage max`; truncated passages ≤1% on T0. Filters: EN+FR; license verified (D57, incl. training-data provenance, e.g. MS MARCO); p95 ≤800 ms at N=50 on D36 without build. Choice: best nDCG gain vs fusion without rerank, EN and FR separately; tie → smallest; no gain → auto without rerank. Candidates: bge-reranker-v2-m3, Qwen3-Reranker-0.6B, mMiniLM-L12 (if license OK); EN-only reference ms-marco-MiniLM-L-6-v2. Robustness: NaN/inf or 800 ms timeout → fusion order, flagged. Score: sigmoid [0,1], align with S2. | project owner | 2026-11-25 |
| D68 | Resource sharing build/serving v1: **exclusion** — build and serving never run simultaneously on D36 (GPU, VRAM, CPU). Initial T1 build before serving. Rebuild = maintenance window, API **503 + Retry-After** (D9/D11), atomic generation switch (D45) after validation. Takedown (D52) via serving filter if possible, no rebuild. Gates: no measurement (D65/D66) with a build running. CPU build: extraction + BM25 only; T1 embeddings on GPU only. GPU sharing with quotas or MIG (RTX Pro 6000 support TBD): only on a new decision if maintenance windows become unacceptable; then VRAM/CPU caps, D66 re-measure, MIG D65 recalc. Multi-GPU (dedicated pools) LATER. Disk: two generations coexist during rebuild → include in the 500 GB split. | project owner | 2026-11-25 |
| D69 | BM25-only fallback: **disabled by default**. Encoder unavailable → **503 + Retry-After** (D9/D11). Activation: serving config (`allow_bm25_fallback`), not in build spec (no `build_id` change), logged at startup. Triggers: OOM, query-encoder timeout (default 200 ms, configurable), encoder process absent; circuit breaker LATER. Behavior: BM25-only results, no rerank; lite/auto; `/contents` unaffected. Signaling: single **`degraded`** field (reasons: `bm25_only`, `rerank_skipped` [D67], …), metrics per reason, alert >1% over 5 min (configurable); backward-compatible **S2 v1.1**, Gate 0 unchanged. Gates: flag forced off; any 503 or fallback during a gate run **invalidates the run** (no exclusion of degraded responses). Quota: degraded response counted (D9); 503 not counted. Never silent; degraded responses never cached. | project owner | 2026-11-25 |
| D70 | Filter × tier table (**S2 v1.1**, with D69; Gate 0 unaffected — no filters, D12). `lite` and `auto` share the same index/filter engine → **same filters**; they differ only by ranking (rerank in auto). MCP: no filters (HTTP only). `numResults` 1–100 (else 400). `includeDomains`/`excludeDomains`: canon-v1 host, **suffix match on whole labels** (`example.com` covers `docs.example.com`, not `badexample.com`), ≤1200 entries/list, empty = absent, **exclude wins**; path-prefix + wildcard supported (`parity: unverified`). `start/endPublishedDate`: RFC 3339 UTC, inclusive, date-only = 00:00Z, start>end → 400; **docs without `published_date` excluded** when a date filter is present. `category` → 400 (LATER). Unknown/unimplemented field → 400 naming field + tier. `numResults>50` auto: rerank `K=max(50,numResults)` (default). Filters **before** fusion/rerank; **no out-of-filter result** (Gate 1 + property tests). Fewer results ≠ `degraded`. **Amends D8/D27** on the lite-filters point. **`includeText`/`excludeText`: not supported in v1 → 400** (unknown-field rule, D27). | project owner | 2026-11-25 |
| D71 | Evidence-collection rule (closes the fixtures blocker; collection itself = **Gate 1 prerequisite**). Source priority: (1) official docs (URL + consult date); (2) official MCP server source at a **pinned commit** (license TBD); (3) real API calls, **≤50 manual**, only if ToS §4.2(f) + D35 allow; (4) else replica default marked `parity: unverified`. Date everything (sources disagree on the type list). Collect: HTTP auth headers/status/body; validation (unknown field, wrong type, `numResults` 0/100/101/absent); filter forms; MCP JSON-RPC transcripts (`initialize`, `tools/list` schemas+defaults, `tools/call` success, invalid args `-32602` vs `isError`, auth fail 401 vs JSON-RPC, key passing); stdio (absent key, stdout=JSON-RPC, stderr logs, exit code); 429 **not provoked**. Storage: raw transcripts local, **not committed**; repo = redacted normalized fixtures + `PROVENANCE`. Completeness: each line = fixture+source **or** "non capturable → default Dxx". | project owner | 2026-11-25 |
| D72 | Memory policy: **serving ≤96 GB RAM** (≈32 GB left for OS + page cache); **build peak ≤120 GB**. If the full ANN index does not fit → quantize or disk-based index (S6). Needed to choose the ANN index and to verify D68. | project owner | 2026-11-25 |
| D73 | **Disk budget (head of S6), D36.** Reference capacity `C_util` = usable capacity measured with `df` after formatting (Gio), never the advertised "500 GB". **Peak inequality:** `F + L + 2·G + S ≤ 0.85·C_util` (15% never filled). Caps: **F ≤ 80 GB** (OS, containers, CUDA, model weights, HF cache), **L ≤ 10 GB** (logs/metrics/run manifests, rotated), **G ≤ 100 GB** per generation (docstore text, BM25, vectors, ANN graph, metadata, D79 manifest) of which **V ≤ 50 GB** vectors, **S ≤ 100 GB** build scratch (extracted text, passages Parquet, intermediate embeddings). Peak is during build N+1: N stays, N−1 purged first. Pre-build check (free ≥ G_est(N+1)×1.2 + S_max + reserve, else refuse, delete nothing); emergency stop at 85% (purge scratch, N untouched); post-build upload rebuild cache to artifacts (D74), purge scratch, atomic switch (D68). Never stored locally: WARC (streamed, D38/D40/D53), raw HTML, rebuild cache. Measure bytes/doc per component at 10k/100k (D75), project ×1.2 to T1, 1M must be ±20%. Levers if over: zstd → stream intermediates to bucket → int8 rescoring (re-run D81 step 4) → reduce overlap (new decision after D44) → new T1 decision. **Never** reduce the 15% or single generation. Alerts 75%/85%; per-component usage in run manifest. | project owner | 2026-11-25 |
| D74 | Rebuild cache: **local scratch** does not keep WARC. WARC extracts stay in `exa-replica-corpus` for **90 days** (D53); rebuild cache (**text + passages, Parquet**) lives in `exa-replica-artifacts`. After 90 days, re-extraction requires a **new download → new decision** (D38/D40). Rebuild from cache (embeddings + index) **≤12 h** (= D65 minus extraction). | project owner | 2026-11-25 |
| D75 | Scale-test method: measure at **10k (T0) / 100k / 1M (T1)**; metrics = throughput, RAM peak, bytes/doc, p95 latency vs N. Criterion: 100k→1M extrapolation within **±20%** of actual, else block before T2. | project owner | 2026-11-25 |
| D76 | Language detection **follows D57** (license filter). **Default GlotLID** (verify license at the pinned revision, believed Apache-2.0); fastText `lid.176` (CC BY-SA 3.0) only if an explicit decision extends D57 to tool models. **Document-level**, confidence threshold, `und` below, `lang` in metadata. Gates the 80/20 T1 split (D37), D58 stats, and B. | project owner | 2026-11-25 |
| D77 | Cleaning pipeline, in order: boilerplate removal → **NFC** normalization → control-char removal → min doc length → exact dedup (hash) → near-dedup (MinHash). **Near-dedup disabled by default in v1**; measure the near-dup rate on T0 (Jaccard ≥ 0.8 on 5-grams), enable only if it exceeds `X`%; if enabled, docs get `dup_of` + `not_in_index` (D20). All **versioned in the manifest**. Affects doc/passage counts → disk + build time. | project owner | 2026-11-25 |
| D78 | UTF-8 offsets: **internal = byte offsets on NFC-normalized text**; API v1 exposes **no offsets**; highlights convert at output (code points or UTF-16 per client). Prevents broken multibyte cuts. | project owner | 2026-11-25 |
| D79 | Manifest v1 (split per D46): **spec** = `generation_id`, crawl + **WARC-list hash**, extractor/cleaning/chunker/lang-detection versions, model (id + revision + hash), `PromptConfig` (D61), precision bf16/fp8, licenses; **result** = doc/passage counts; **run manifest** = build durations (kept out of `spec` so `build_id` stays idempotent). Required to reproduce a build, switch generation (D68), verify which generation a gate ran on. | project owner | 2026-11-25 |
| D80 | **Planning order + S6 gate.** Order: cleaning + language detection (D76/D77) → B protocol → passage spec freeze (D44) → manifest v1 (D79). **S5 and S6 advance together** (circular: S5 needs S6 for highlights/LUT/cache; S6 needs S5 for the model). S5 is "done" when its own decisions are frozen (model choice, eval, provenance); the S6/S7-tagged items move with their subject. **Final S6 validation only after S2–S5** (reinforces D47). | project owner | 2026-11-25 |
| D81 | **Embedding-model choice = a 5-step rule (not a name).** (1) Eliminatory filters in order: license (D57) → EN+FR (D58) → T1 embedding ≤8 h with 20% margin (D65) → query encode p95 ≤50 ms (D66) → vector size fits D73. (2) Preselect ≤3 finalists from a **dated MTEB capture** (D71). (3) Quality: **nDCG@10 on the dev golden set, hybrid BM25+dense, RRF k=60, no rerank**; EN decides; FR ≤3 pts below best finalist **and** IC95 upper <0; must beat BM25 (IC95 lower >0); ≤15% unjudged in top-10. (4) S6 link: **R0 exact GPU default; R1 (binary + int8 rescoring) only if R0 fails**; total loss vs bf16/full-dim ≤2 pts (0 with R0, measured only for R1) at the S6 index setting. (5) Tie-break: paired bootstrap (B=10 000, IC95, fixed seed); if not significant → least costly (T1 time → p95 → bytes/vector, each <10%). Thresholds frozen before the full run; **no dev golden set → provisional choice only**. Long list ≤1B params (candidates per step 1). Result → **D81-R** (journal: model/version/scores/IC/reasons/MTEB ref; spec D79: id/version/license/PromptConfig/precision/dim/quant; run manifest: throughputs; result: counts). | project owner | 2026-11-25 |
| D82 | **Dense index settings.** **R0 exact GPU (default):** bf16 native-dim vectors, exhaustive dot-product in VRAM, exact top-k, ties by `passage_id`. **R1 compressed CPU (fallback):** binary native-dim vectors, exhaustive Hamming scan; top `K_bin` rescored int8 from RAM. **Excluded in v1:** MRL, HNSW graph, PQ. **Rule:** keep R0 if it meets the D66 dense-latency budget + VRAM; else R1 if recall@100 vs R0 ≥0.95 and loss within D81 step 4; if R1 fails too → new decision opens HNSW. **D81 step 4:** loss = 0 with R0; only R1 measured. R1 params: 128 B/vector (~0.6 GB), int8 rescoring (~5 GB). **`K_bin` rule (D82, not D13):** options 500 / 1000 / 2000; measure recall@100 vs R0 exact on the D81 set; criterion recall@100 ≥0.95 **and** latency within D66 dense share; default = smallest passing value; if none passes → R1 is not a valid fallback, signal before build and revise D82. Library: default plain matmul (PyTorch); optional FAISS (IndexFlatIP GPU / IndexBinaryFlat) if D57 + Blackwell support. Generation switch (D68): load N+1 in VRAM, switch, free N → budget 2×V_gpu; if it doesn't fit, short dense outage (BM25 still served) in the runbook. **D68 check:** if build/serving never share the GPU, R0 very likely; else measure R0 latency during a build. Thresholds: 2×V_gpu ≤24 GB, recall@100 ≥0.95, nDCG loss ≤2 pts, dense latency = D66. | project owner | 2026-11-25 |
| D83 | **BM25 index (lexical) settings.** (1) **Engine:** default **Tantivy** (verify license at pinned revision, a-priori MIT); fallback **Lucene** (Apache-2.0, JVM) if Tantivy fails a criterion; **custom excluded**. Criteria: Python bindings (tantivy-py) vs JVM dep, build time ≤ D65, index size in G (D73), p95 (D66), RAM (D72). (2) **Indexed unit = passages** (same `passage_id` as dense, for RRF same-granularity). Document score = **max over passages** (both branches), aggregation **before** fusion; keep the **winning passage id** (the passage that produced the score). RRF (k=60) ranks **documents**. **Rerank D67 input:** for each of the top-50 RRF docs, **one passage** = the winning passage of the branch that ranks the doc higher (tie → smallest `passage_id`, D83/8); budget D67 unchanged. *Option (measure on D81, adopt only if gain IC95>0 and latency ≤ D66):* send 2 passages/doc (BM25 winner + dense winner, deduped). **Reference passage** = the passage kept after rerank (or the one chosen above if no rerank); **D84 starts from it**. (3) **Text analysis + EN/FR routing:** default **Option A** — two fields `text_en`/`text_fr`, doc indexed in its D76 language field, query analyzed with both analyzers and queries both fields (short-query lang detection unreliable); Snowball EN/FR; French elisions (l', d', qu'); accent folding; **stopwords kept in v1**. If A does not beat **Option B** (single neutral field: lowercase + accent fold, no stemming) on FR (paired IC95, D81 method) → keep B. Analyzer version in the **index spec (D79)**, not `chunker_version`. (4) **Positions: disabled by default v1**; highlights computed at query time on passage text (D78 offsets); revisit only if highlights decision needs phrase queries (then measure size at 10k/100k, D75). (5) **Scoring:** BM25 **k1=1.2, b=0.75 fixed, no dev tuning** (avoid overfitting small golden set). (6) **Filters (incl. `includeText`/`excludeText` → 400 per D70/D27) applied before fusion**, same semantics as dense. (7) **Safe query analysis:** never interpret user text as query syntax (operators, quotes, `field:`); escape/tokenize raw text; consistent with the error table (no 500 / syntax injection). (8) **Determinism:** ties by `passage_id`; merge to a fixed segment count (ideally 1) at build end for reproducible order/stats. (9) **Criteria:** p95 BM25 = **50/80 ms** (D66), RAM ≤ D72, BM25 floor (D19), index size G ≤ D73, build time ≤ D65. **D69 unchanged** (BM25-only fallback stays disabled by default). | project owner | 2026-11-25 |
| D84 | **Highlights (extractive, v1).** **Method:** extract sentences **at query time, only for returned results** (never all candidates); **no LLM generation** in v1. **Source:** doc text via D78 offsets; start from the **reference passage** (D83 correction A), may expand to neighboring passages of the same doc. **Unit:** sentence (deterministic EN/FR split); no-punctuation text (lists/tables/code) → window of N chars cut between words. **Guiding text:** highlights text from the query (**S2, D8/D27**) → `objective` → `query` (order); `/contents` without guiding text → first N sentences; **`not_in_index` doc (text present in store) → same split on the fly**; `not_found` → no highlights. **S0:** `objective` + `query` concatenated (D83/3 analyzer). **S1:** encode the same text with the *query* template (D61). `objective` is used as **text**, not instruction (D61 "objective as instruction = LATER" — no conflict, stated explicitly). **D51:** `nosnippet`/`max-snippet:0` → `highlights: []` (no error); `max-snippet:N` → each excerpt cut to N chars; `max-snippet:-1` → no limit. **Determinism:** same inputs → same highlights; tie → smallest offset. **Format:** HTTP fields per **S2 (D8/D27)** (Exa a-priori `highlights` + `highlightScores`, re-verify per D71; scores not guaranteed comparable across docs); MCP stable text rendering; **offsets not exposed in v1**. **D83/4 closure:** highlights re-read text on the fly → **no positions needed**; reopen only if R2 exceeds budget. **Decision rules:** **R1 selection** — S0 lexical (BM25 per sentence, D83/3 analyzer, CPU) default; S1 dense (cosine sentence vs guiding text, encode pool) only if gain ≥2 pts IC95>0 (bootstrap B=10 000) and latency ≤ R2; **lite forces S0**. **R2 latency** — **Highlights sub-line of D66** on the Contents share (**100 ms lite / 300 ms auto**, provisional; Contents split = store 50/100 + highlights 100/300, sum ≤ Contents; recalibrate with D17 measures); measure added p95 for 10 results; if exceeded in prod → switch S1→S0, log event (D71). **R3 number/length** — names/bounds from **S2 (D8/D27)**; if S2 v1.0-gate0 only has `highlights: true`, any option → 400 (D27) → defaults become **server constants**; exposing options needs **S2 v1.1**. Proposed defaults 1 excerpt/URL, ≤3 sentences, caps 5 excerpts / 5 sentences. **Later:** LLM highlights, cross-encoder sentence ranking, multi-doc highlights. **Eval:** **D94** highlight metric + non-regression (**byte-exact for S0**; for S1 fix batch/order or apply **D63 tolerance** on scores + require the **same sentence choice**). | project owner | 2026-11-25 |
| D85 | **Index interface.** One port per branch: **`DenseIndex`** and **`LexicalIndex`**, each with `search(query, filters, k, deadline)`, `stats()`, `version()`. **No `add`/`delete` in v1** — full rebuild per build (D56); deletions via serving exclusions (D52). Each search is bound to the **`index_version`** fixed for the request (§1.3.1). An unsupported filter raises **`UnsupportedFilter`** (§1.3.1 point 4). | project owner | 2026-11-25 |
| D86 | **Orchestrator (v1).** A **static plan per tier** (`TierPlan`, §1.3.1) suffices. Executes in the D66 order: query encode → **BM25 in parallel with dense** → fusion (RRF) → rerank → contents → highlights. **`Deadline` checked between steps**; one trace per node; **no memoization in v1**. A real Canon-style DAG is **LATER** (new decision). Execution (workers, bounded queues) belongs to **S7**. | project owner | 2026-11-25 |
| D87 | **Sharding (v1).** **Single local shard per branch** (D36). For test 5a, provide **N local partitions** by page hash, with a **per-branch merge before RRF**. With R0/R1 the search is **exact** → top-k identical between 1 and N shards. **BM25 uses global statistics** to preserve 1/N equivalence. Rebalancing and multi-GPU: **LATER**. | project owner | 2026-11-25 |
| D88 | **Recall target per tier.** Dense recall vs exact: **R0 = 1** by construction; **R1 ≥ 0.95 @100** (D82). **Same target in lite and auto** (same index, D70). End-to-end quality remains D14/D19. Closed by reference, **no new threshold**. | project owner | 2026-11-25 |
| D89 | **Runtime topology (v1) = (b) gateway + separate workers** on D36 mono-box. **Gateway (single process):** HTTP + MCP on the same ASGI app, same `SearchService` (§3.3.1) → parity by construction. **Workers:** **one GPU process** (query encode + R0 dense + rerank; single CUDA context, no VRAM dup D72, internal batching); **CPU process(es)** (BM25/Tantivy + contents store read + highlights); **search pool is split** across the GPU process (dense) and a CPU process (BM25). **IPC:** local, **no external broker v1** (no Redis/RabbitMQ); **default = Unix socket + msgpack**; ZeroMQ/gRPC only if the measured p95 IPC overhead exceeds the D66 margin. **Measure p95 overhead per hop** (real query vector, K candidates, rerank passages) → counts in D66 overhead/margin. **Queues:** bounded; full → **503 + Retry-After** (§1.3.1, D11). **lite priority (d):** separate queue per tier or reserved lite capacity (§1.3.1); isolation test: auto burst → lite p95 ≤600 ms. **Supervisor (e):** restart workers + health/readiness; **default = systemd** (supervisord only if no systemd); link D17 5f/D69 (BM25 down → dense-only, `degraded`, never cached); measure restart time. **build_id (f):** each worker announces its `build_id`; gateway refuses to mix two builds in one response; switch → D45/D79. **Frameworks (h):** FastAPI/Starlette + official MCP SDK, versions pinned in spec; verify MCP SDK license (D57) and that 2025-11-25 (D23) is still current. **Single-process fallback:** only if it passes the same measures; must stay a **single** process (multiple uvicorn workers would dup VRAM); BM25/contents under the GIL — measure, don't assume. **License/target check (amended 2026-11-26, replaces "spec 2025-11-25 current"):** MCP Python SDK = **MIT** (D57 OK). **Target = the revision marked "Current" on the official Versioning page at M0 freeze (2026-07-28 to date)**; SDK **mcp (Python) 2.x** serves all prior revisions from the same server (no dedicated code); **no tool depends on a server-initiated request** (elicitation/sampling/roots removed in 2026-07-28); exact version pinned at M0 (`[V1]`). | project owner | 2026-11-25 |
| D90 | **Caching (v1) = option 1: query-embedding + contents; full-response cache OFF.** **Placement:** after auth + quota; a cache hit **consumes quota (D9)**; errors (401/429/503) never cached; **keyless: only full responses are not cached — embedding + contents caches stay shared**. **D52 exclusions applied after cache read** (takedown immediate). **Keys:** embedding = (model D81, PromptConfig hash D61, query text) with key normalization **identical to the encoded text**; contents = (`build_id`, `url_canonical`) for text+passages only (**highlights recomputed per request**); full response (if enabled) = `build_id` + PromptConfig + tier + normalized params (filters D70, `numResults`) + `objective`. **Decision rule:** options (0 none / 1 embedding+contents / 2 +full responses); measure hit rate on a query replay, p95 gain, RAM; **option 2 enabled only if hit rate ≥20% on replay AND p95 gain ≥10% AND RAM ≤ D72**; default v1 = option 1. **Storage:** bounded **LRU in RAM in the gateway**, no Redis v1 (embedding hit avoids the GPU round-trip). **Non-regression:** same query with/without cache → same response (S0 byte-exact, S1 D63 tolerance; consistent with D84). **Gate 4:** cache state always declared (D16); **validate with a cold cache**, warm numbers informative only. | project owner | 2026-11-25 |
| D91 | **Security (concrete).** (1) **API keys:** HMAC hash (D3); logs show only the key **prefix**, never the secret. (2) **TLS:** terminated on a reverse proxy in front of the gateway; gateway listens on **localhost only**; HSTS if publicly exposed. (3) **Size limits** (defaults, overridable via D92 config): HTTP body ≤**1 MiB** checked before parsing; `query`/`objective` ≤**4096** chars (as MCP); `urls` ≤**100**; `maxCharacters` cap (S2 §8); **max response size = `urls_max (100) × maxCharacters_cap (5,000,000)` chars → byte limit in UTF-8 (1–4 bytes/char) with JSON escaping (control chars → 6 bytes; `ensure_ascii=True` escapes non-ASCII, e.g. "é" 2→6 bytes, matters for FR); default = cap total response at 550 MB (≈ 524.5 MiB) → truncate or 413 (D11)**; overridable via D92; MCP messages = HTTP body limit by default. (4) **Error codes:** body too large → **413** (D11 amended); field limit → 400 (D11). (5) **CORS:** **disabled by default** (server-to-server API); allowlist configurable. (6) **Secrets:** pepper + Postgres creds from env or a secret manager; validated at startup (§1.4.1); gitleaks pre-commit + CI. (7) **Logs:** never query, objective, full URL, content, or key (D17 5d). (8) **Deserialization:** no `eval`/`exec`/`pickle`; IPC accepts only msgpack/JSON with a worker-side validated schema. (9) **Path containment (store + manifests):** resolve then verify under the intended root; symlinks escaping the root rejected. (10) **IPC isolation:** Unix socket **0600**, workers + gateway same user; workers never listen on the network. (11) **Supply chain:** lockfiles, pip-audit, cargo audit, SBOM (§1.4.1, D17 5e). (12) **SSRF:** **out of scope v1** (no live fetch D56; `web_fetch_exa` reads the snapshot); TODO trigger to reopen with the live-fetch seam. (13) **Container:** non-root, images pinned by digest. (14) **Tests (planned):** oversized body → 413; no key in logs (redaction); CORS preflight refused by default; path traversal rejected; IPC socket 0600. | project owner | 2026-11-25 |
| D92 | **Config & DI.** **Settings:** one typed, immutable object loaded from env + file, validated at startup (process stops on invalid config); default **pydantic-settings** (license per D57). **Composition root:** one per process (gateway, GPU worker, CPU worker); instantiates adapters behind the D85 ports; **no DI framework**. **Config separation:** serving config (D51 `contents_policy`, `allow_bm25_fallback` D69, cache sizes D90, limits D91) vs build spec (D79). **Startup checks:** consistency with the manifest — PromptConfig (D61) + `build_id`; on mismatch the process refuses to start; gateway also refuses to serve if workers announce different `build_id`s (D89). | project owner | 2026-11-25 |
| D93 | **Golden set sizing & composition.** Base = §1.5 (200 = 100 dev/100 test provisional, cluster dedup, hash split, tags, specific objectives) — **not restated**. **Gated scope = EN only** (100 dev / 100 test). **FR = fixed diagnostic cohort `N_FR = 100`, not gated** (amends D33; D81 + TODO D84 aligned). **Tier = execution condition** (§1.5): same queries under lite and auto (**paired**); deep out of v1 gates (D15/D18). **Strata:** closed domain list fixed pre-draw; **min per stratum = 10**; below → "too small" (reported, never gating); allocation = min quota per stratum then proportional. **Growth rule:** `h` fixed pre-pilot (smallest effect the gate must resolve: D31 absolute-threshold gap, D19 BM25-floor margin; NI → h < δ=0.05); σ from the dev pilot (**paired diffs** for the BM25 floor, not raw scores); `n_test = max(100, ceil((1.96·σ/h)²))` rounded up to 50, **cap 400**; >400 → new decision (revise h or metric, no silent extension). Decided on **dev only, before any test run**; existing test frozen; additions via the same procedure. **Note:** D37 80/20 applies to the **corpus**, not queries. | project owner | 2026-11-25 |
| D94 | **Highlight relevance metric.** Base = §1.5 (in-context judgment, same objective; page vs highlight judged separately; key = (task_id, page_key, hash of excerpt); success@3 highlight; N/A for BM25) — **not restated**. **Scale 0–3 per excerpt:** 0 = off-topic, 1 = tangential, 2 = partially useful, 3 = answers the objective. **Primary metric:** success@3 highlight (§1.5). **Secondary:** mean excerpt precision over top-10. **Decision (D47):** precision over **all** top-10 pages (default, what the user sees), not only judged-relevant. **S0 vs S1:** paired bootstrap per query, D84 R1 rule (gain ≥2 pts **and** IC95 lower >0 → adopt S1, else S0 default). **No gate in v1** (diagnostic only); trigger = explicit product requirement. **Judge:** same calibrated judge (D13/D14) but **κ measured separately on highlights**; if κ < **§1.5 (κ ≥ 0.6, provisional)** → highlights "uncalibrated", cannot be used for D84 R1. **Amends D84:** "3g/S8" → "D94". | project owner | 2026-11-25 |
| D95 | **Repo, layout, naming.** **Repo strategy:** measure = **share of existing code reused as-is** in the new layout; **threshold = <30% reused → (a) new repo `exa-replica`** (default), else **(b) refactor in place**; measured **before the first commit of the new repo**. **Harness (D35, non-throwaway):** migrate into the new repo **keeping history** (`git filter-repo`/subtree), archive the old repo read-only with a pointer (no two harness versions). **Naming:** `exa-replica` = **internal code name**; **public name neutral, chosen before first publication** (milestone in D97); compatibility stated in the README ("API compatible with…"), not in the name. Crate **`ann-core`**, Python module **`ann_core`**. **Layout:** `src/<pkg>/` = `domain/` (pure), `ports/` (D85), `application/` (SearchService, pipeline, TierPlan, orchestrator D86), `adapters/inbound/` (http FastAPI, mcp), `adapters/outbound/` (store, encoder, ann wrapper, contents), `bootstrap/` (composition root D92 — only wiring place), `entrypoints/` (1 per pool D89 + single-process fallback); `ann-core/` (Rust, maturin, **optional R1 only, K1**); `eval/ bench/` (harness §1.5/D35, **outside** the product package); `deploy/` (systemd units D89); `docs/`. **Packaging:** **one Python distribution (src layout) + optional Rust crate** (`ann-core`, R1 only, K1), maturin, **lockfiles committed** (`uv.lock`, `Cargo.lock`); multi-package workspace only if a component must be published separately (e.g. `ann-core` on PyPI) — reopen trigger. **Measurable criteria:** no circular dep → **D96 contracts green in CI** (D17 5e); reproducible build → **lockfiles committed + same image digest for same source** (D17 5b/5c). | project owner | 2026-11-25 |
| D96 | **Dependency rules (import-linter).** **Layer contract:** `entrypoints → bootstrap → adapters → application → ports → domain`; imports go **down only**. **Prohibitions:** `domain` imports **no** fastapi, MCP SDK, httpx, store driver, or `ann_core`; **only `adapters/outbound/ann` imports `ann_core`**; **only `bootstrap` instantiates adapters** (D92). **Independence:** adapters do not import each other; `inbound/http` and `inbound/mcp` are independent. `eval/` and `bench/` may import the product, **never the reverse**. **Contracts:** `layers` (down-only) + **`forbidden`** (`entrypoints` must not import `adapters`, must go through `bootstrap`; optional: `domain`/`application` import no fastapi/httpx/torch) + **`independence`** between `adapters` subpackages — together these make "only bootstrap references an adapter class" import-checked, the rest by code review. **Application:** import-linter **blocking in CI** (D17 5e); the Rust PyO3 API stays **minimal and frozen by the ANN port**. **Exceptions:** each listed in the config with a justification + decision ref; **no silent exception**. | project owner | 2026-11-25 |
| D97 | **Milestones + DoD + public name.** Milestones by **exit criteria**, not dates. **Gate placement (D47): default (A) keep milestone order, move the gates; criterion = each gate measures only what already exists + the test split is used once per RC.** **M0 Skeleton** (no gate; repo+layout D95, import-linter D96, lockfiles, CI D17 5e, DCO bot, OpenAPI/`tools/list` stubs, D89 license precondition → CI green + digest) · **M1 Contract e2e** → **Gate 0 (D12) + Gate 1 (MCP drop-in, replica)**: `/search` lite + auto (TierPlan auto; reranker passthrough OK on T0; **provisional model per D81; single-process/minimal topology — D89 arrives M5**), `/contents` with **highlights S0 (D84)**, both MCP tools · **M2 Eval on dev** (harness §1.5/D35, golden set, pilot σ, D93 growth, D81 model choice) → n_test frozen, no test run · **M3 Auto complet** (real reranker) → **Gate 2 (keyed mode, D3–D11)** + **Gate 3 on dev split** + **Gate 4 pilot (non-blocking)** · **M4** S1/R1 + D94 only (S0 already in M1) · **M5 RC** → D89 + D90 + full D16 suite → **Gate 3 on test split (single run)** + **Gate 4 blocking (final topology, cold cache)** + **Gate 5 (D17)** + D91 + public name + v0.1.0. **Smallest steps:** independent mergeable PRs, CI green, ≤400 lines diff. **DoD per PR:** tests; import-linter green; OpenAPI + `tools/list` updated or justified diff; docs; Dxx ref. **Public name** before first public push. **Amended: gate placement aligned with D8/D12/D14/D16/D89/D90.** | project owner | 2026-11-25 |
| D98 | **CLA/DCO, versioning, docs.** **DCO by default** (`Signed-off-by` verified in CI); Apache 2.0 inbound=outbound; **explicit:** a later license change becomes hard; **trigger to CLA** = need to relicense/dual-license. **Versioning (3 axes):** **code** = SemVer (0.x: breaking allowed in minor, stated); **API/MCP surface** = additive → minor, breaking → major with a **deprecation period = max(1 minor version, 90 days)**; signaling = CHANGELOG + `Deprecation` (RFC 9745) + `Sunset` (RFC 8594) headers on `/search` + `/contents` + MCP tool description; **applies to 0.x too for the Exa-compatible surface** (default yes); OpenAPI + `tools/list` snapshots compared in CI; **models/index/judge** do **not** follow code SemVer → D13/D14, D17 5b/5c, D32. **Docs:** README (compatibility + non-affiliation), self-host quickstart, API/MCP refs **generated** from contracts, ops guide (D89/D92), `SECURITY.md` (D91), `CONTRIBUTING.md` (DCO), `CHANGELOG.md`. | project owner | 2026-11-25 |
| D99 | **v2.2 confirmed (§1.3.1 decisions 1–5).** (1) `/search` degrades via the **single `degraded` field (D69: list of reasons, absent when nominal)**; **`/answer` is out of v1** (surface = `/search` + `/contents`) and must fail explicitly if ever added (LATER). (2) Deadline per-tier v1; an override that **exceeds** the tier deadline is **clamped to the cap**, and the **effective value is returned in a response header `X-Effective-Deadline-Ms`** (not a body field). (3) `needs_vector` derived from the tier's stages (or validate all TierPlans at startup). (4) Unsupported filter → **400 `unsupported_field` (D27)** + `filter` + `tier` (covers a future deep tier; no new tag). (5) `index_version` pinned via optional request header **`X-Index-Version`**, **always echoed in the response**; content store keyed by `(index_version, doc_id)` or content-addressed; old version readable until drain; **mismatch → 409 `index_version_mismatch`** (added to D11); **MCP: no client pin, server-resolved**. | project owner | 2026-11-26 |
| D100 | **K1 keep/cut.** **Keep (core):** Rust `ann-core` (**optional R1 Hamming only**, D82), measured operating points + `EXPERIMENTS.md` (**historical — IVF/nprobe replaced by D82**), ingest/dedup (SQLite bounded), gate/bench harness concepts, security hardening (constant-time auth, strict config, path containment), tests (salvage selectively); content store = **historical/concepts** (D48–D50 Parquet + mapping). **Cut:** config split (`config.py` + `config_loader.py`), **global/shared MCP config outside the project** (the MCP tools `web_search_exa`/`web_fetch_exa` stay), pipeline scripts (`run_pipeline`, `build_index`), stale docs, notebooks (0.027 baseline), box-only ledgers (`runs.jsonl`). **ann-core creation criterion:** only if **R1 is retained per D82** AND profiling shows the Hamming scan is the bottleneck AND **≥2× p95 gain at equal recall (±0.5 pt recall@100, k=100)** on **T1, search pool**, reference = Hamming numpy/PyTorch or FAISS `IndexBinaryFlat`; default = **not created**. | project owner | 2026-11-26 |
| D101 | **Governance source.** **`AGENTS.md` = source of truth**; **`CLAUDE.md` contains only the pointer/import to `AGENTS.md`**. **CI check fails if `CLAUDE.md` contains anything else.** Pillars + anti-drift live in AGENTS.md. | project owner | 2026-11-26 |
| D102 | **Dev rules (exhaustive thresholds + enforcement; §1.4.1 is part of this by reference).** Structure: **≤500 lines/file** (hard, >400 → split), **≤50 lines/function**, **≤3 nesting**, **cyclomatic ≤10**; one responsibility/module; no circular imports (D96); no mutable global state. Typing: full hints on public functions, **mypy --strict on `src/<pkg>/`**, no `Any` outside FFI/JSON, Pydantic at boundary, frozen dataclasses inside. Errors: validate at boundary, standard envelope, timeout + explicit degrade, no bare `except` except process boundaries, typed errors, fail fast, retry backoff+jitter (no 4xx). Pipelines: idempotent+resumable, atomic writes, manifests, one knob/experiment. Testing: **coverage ≥80% lines on `domain/` + `application/`; `adapters/` excluded (covered by contract tests)**; tier-0 <10s no net/GPU; contract tests; golden tests; **mutmut + hypothesis**. **Tools:** complexity → ruff C901 + **pylint R1702 / PLR0911 / PLR0912 / PLR0915**; file/function length → dedicated lint; **cargo fmt + clippy (`too_many_lines`)**; typing → mypy strict; **architecture → import-linter (D96 `layers` + `forbidden` + `independence`)**; **pip-audit + cargo audit + gitleaks**; **PR ~400 lines + conventional commits**; **`make check`**. **Derogation:** justified comment + review + tracked exception list. **All checks blocking in CI** (transitional M1 exception only if written). | project owner | 2026-11-26 |
| D103 | **Contract artifacts + Exa comparison.** **OpenAPI snapshot + `tools/list` snapshot versioned in the repo**; CI compares every contract change to the snapshots; a contract change follows the D98 deprecation policy; **Exa comparison → D19** (diagnostic/LATER). Links D71 (capture), D98 (deprecation), D19 (parity). **Captured 2026-11-26:** OpenAPI 2.0.0 (`docs/contracts/exa-openapi-2.0.0.yaml`, sha256 `d625c66c…af499b`, source https://exa.ai/docs/exa-spec.yaml + PROVENANCE). | project owner | 2026-11-26 |

---

## 7. Open questions by subject

> **Historical — answered in §6.** Each question maps to a decision; kept for traceability.

### S1 — Definition of done → D12/D14/D16/D18–D19/D94
- What does "target" mean: project definition of done, capacity target, or both?
- What is the success test for "reproduce Exa MCP"?
- What are the anti-goals (things that would make this a failure even if they work)?

### S2 — Product contract → D8 (S2 frozen)
- Which endpoints/tools are v1?
- Exact OpenAPI compatibility vs semantic compatibility?
- Which Exa fields are non-negotiable?
- How is `objective` consumed (query understanding, rerank, highlights)?

### S3 — Scale & hardware → D30/D36/D72
- Target corpus sizes (1M/10M/100M/1B)?
- Latency/throughput budgets per tier?
- Memory budget policy (VRAM/disk/sharded)?
- Single node vs multi-node for v1?

### S4 — Data plane → D28/D56
- WET-only vs WET+WAT vs WARC for v1?
- Data structure (see §4)?
- Update/freshness model?
- Dedup/clean policy?
- Idempotence/reproducibility mechanics?

### S5 — Models → D81/D82 (model/dims/quant), D67 (reranker), D61/D79 (versioning); generator → §3.8 (LATER)
- Embedding model(s), dims, quantization?
- Query vs doc model?
- Reranker?
- Generator for answer/deep?
- Versioning/pluggability?

### S6 — Index & retrieval
- Index family → **D82** (R0 exact GPU / R1 binary + int8); interface → **D85**.
- Hybrid dense+sparse → **D81/D83** (BM25 + dense, RRF k=60).
- Passage-level vs document-level → **D83/2** (passages; doc = max; winning passage).
- Highlights extraction → **D84** (extractive v1).
- Orchestration DAG and tiering → **D86** (static plan v1); sharding → **D87**; recall target → **D88**.

### S7 — Serving & platform
- MCP + HTTP shape + topology → **D89** (gateway + workers; FastAPI + MCP SDK).
- Auth, rate limits, concurrency → **D3–D11, D24, §1.3.1**.
- Caching → **D90** (embedding + contents; LRU RAM; cold-cache gate).
- Failure/degradation → **D69, D17 5f, §1.3.1**.
- Observability (metrics/traces/logs) → **D17 5d**.
- Security → **D91**.
- CI/CD → **D17 5e**; config/DI → **D92**.

### S8 — Evaluation
- Recall@N / quantization / coverage → **D13** (3d/3e/3f), D82, D88.
- Golden set & query set → **D93** (EN gate 100/100; FR diagnostic 100; growth rule).
- Highlight relevance metric → **D94** (success@3, 0–3 scale); model → D84.
- Judge calibration, judged@k, versioning → **§1.5 (Judge calibration, Judgment versioning) + D14**.
- Test split / pilot σ → **§1.5 + D14/D81**.
- BM25 floor, paired bootstrap CIs, metrics → **D14, D19, D81**.
- Load test harness → **D16** (Gate 4).
- Reproducibility → **D17 5b/5c, D32, D63**.
- Scale extrapolation (±20%) → **D75**.
- Regression gates in CI → **D17 5e**.
- Fast bench harness → **§1.5, D35**.
- Research/answer eval → `[LATER]` (reopen if `/answer` in scope).

### S9 — Repo & milestones
- Package/module boundaries, repo, naming, packaging → **D95**.
- Dependency rules (import-linter, down-only) → **D96**.
- Config/DI → **D92**; CI/CD + release → **D17 5e**.
- Code/model/data licenses → **D55**; CLA/DCO + versioning → **D98**.
- Milestones + DoD (tied to gates) + public name → **D97**.
- Security → **D91**; observability → **D17 5d**; harness → **§1.5/D35**.

---

## 8. Next actions

1. **Cross-cutting: done** — v2.2 (D99), K1 (D100), AGENTS.md/CLAUDE.md (D101), dev rules (D102), D17 5d per-pool (amended), P1→D91, P3→D15 4c/D17 5d, proofs (D103).
2. **Evidence (unblocks execution):** B run (buckets + T0) → freeze D44; D81 model choice; OpenAPI + `tools/list` as versioned contract artifacts (D103/D71/ToS); baseline → **§5**.
3. **Then implementation** (M0→M5, D97) — no code before planning is complete (D47).

---

## 9. Sources

- Common Crawl formats: https://commoncrawl.org/get-started, https://commoncrawl.org/blog/web-archiving-file-formats-explained
- Exa 2.0: https://exa.ai/blog/exa-api-2-0
- Exa crawler: https://crawler.exa.ai/, https://exa.ai/docs/admin/faqs
- Exa web indexing: https://exa.ai/blog/what-is-web-indexing
- Exa search API: https://exa.ai/docs/reference/search
- Exa MCP: https://exa.ai/docs/get-started/exa-mcp
- Exa AWS embedding throughput: https://aws.amazon.com/blogs/machine-learning/exa-boosts-embedding-throughput-by-50-to-index-billions-of-documents-on-aws-ai-chips/
- MTEB leaderboard: https://leaderboard.mteb.org/
- Embedding models 2026: https://getaight.ai/blog/best-embedding-models/, https://gpuwerk.com/blog/best-open-embedding-models/
- ANN: https://www.couchbase.com/blog/diskann/, https://aws.amazon.com/blogs/big-data/choose-the-k-nn-algorithm-for-your-billion-scale-use-case-with-opensearch/
- GPUs: NVIDIA RTX 5090, RTX PRO 6000 Blackwell, H200, B300 product pages
- Hybrid/RRF: https://weaviate.io/blog/hybrid-search-explained, Cormack et al. RRF paper
- LLM serving: https://developersdigest.tech/blog/vllm-vs-tgi-vs-sglang-inference-server-comparison, https://tensormesh.ai/learn/vllm-vs-sglang/
- Exa engineering blog: https://exa.ai/blog/ — Exa 3.0, web-scale vector DB, Exacluster, BM25 optimization, Canon, exa-d