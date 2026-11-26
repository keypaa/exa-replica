# Exa (exa.ai) Engineering Blog — Technical Digest

Scope: 35 sources read (31 Exa blog posts + 2 third-party technical interviews + supporting pages). This digest extracts concrete engineering facts to inform a self-hosted, open-source, Exa-like search engine. Claims are tagged:

- **[S]** = directly stated in a source (quoted or closely paraphrased).
- **[I]** = inference by the author of this digest (reasoned, not directly stated).
- **[?]** = uncertain / not verifiable / contradictory across sources.

All numbers are quoted as given. Do not treat blog marketing framing as ground truth.

---

## 1. Executive summary — the 15 most important takeaways for a replica

1. **Exa is a neural-first, embedding-centric engine, not a keyword engine with an LLM bolted on.** Documents are preprocessed into embeddings by in-house trained transformer models; retrieval is "predict the document/link that would follow the query text" (link-prediction objective, a "neural PageRank"). [S — building-search-post-chatgpt, latent.space]
2. **The vector index is a custom clustered + binary-quantized system, not HNSW.** 4096-dim embeddings are truncated via Matryoshka to 256 dims (20x memory cut), then binary-quantized to 1 bit/dim (another 16x). Search uses an asymmetric dot product (float query × binary docs) with a 16-entry LUT held in CPU registers. ~100k clusters; only the query's cluster + neighbors are searched (~1000x throughput gain). [S — building-web-scale-vector-db]
3. **Hybrid retrieval is first-class: dense + sparse (BM25) fused with RRF (k=60).** The orchestrator DAG shows `retrieve dense (web, 50)`, `retrieve sparse (inverted, 30)`, `fuse rrf k=60`. [S — composing-a-search-engine]
4. **BM25 memory is a primary cost driver: >1.8 TB per 1B docs.** Exa cut it >50% with frequency-grouped postings, delta+varint doc-ID encoding (4B → 1.3B avg), zstd, consolidated buffers, singleton special-casing, and a single flat buffer with (offset,len) pointers. Side effect: query latency dropped ~10%. [S — bm25-optimization]
5. **Highlights (query-relevant passage extraction) are the core token-efficiency primitive.** 500 chars of highlights ≈ first 8,000 chars of page on SimpleQA (16x fewer tokens); 4k chars of highlights beats 32k chars of full text. Runs per request, not cached, <100ms. [S — highlights-for-agents]
6. **Dynamic Highlights generalizes this across results: one forward pass over all concatenated docs**, allocating a token budget across results, 95% fewer tokens than full page text. [S — dynamic-highlights, exa-3]
7. **Orchestration is a typed DAG ("Canon") with a pull-based runtime.** Automatic parallelism, per-node retry, memoization of diamond dependencies, cancellation propagation (parent cancel → cancel children), and full tracing at every invocation boundary with zero per-node instrumentation. [S — composing-a-search-engine]
8. **The data plane ("exa-d") is a typed, declarative column dependency graph over Lance on S3.** Surgical per-fragment, per-column patching; query planning = diff(ideal, actual); Ray Data executes the topologically sorted graph; Ray Actors keep embedding models resident in GPU memory; convergence after partial failure. [S — exa-d]
9. **Serving is tiered by compute, not by index.** Exa Lite ($4/1k) and Exa Auto ($7/1k) run on the *same index*; Auto spends more compute on candidate generation, highlights, and ranking. High-compute "Websets" is the test-time-compute tier. [S — exa-3, how-to-build-nextgen-search]
10. **Hardware: a $5M, 144×H200 cluster ("Exacluster", 18 nodes × 8 GPUs)** plus an older 80×A100 cluster; 20 TB HBM3, 36 TB DDR5, 270 TB NVMe, ~100 kW. Orchestrated by Pulumi → Ansible/Kubespray → NVIDIA operators → Alluxio (NVMe cache over S3) → Flyte. [S — meet-the-exacluster]
11. **Scale: >2 trillion URLs tracked, ~100B pages served** (Monitors v2 says 130B+; see contradictions). Vertical indexes: 1.27B product listings, 211M places, 350M publications, 3.2M podcast episodes, 1B+ people, 70M+ companies. [S — exa-3, places-search, publications-search, podcast-search, monitors-v2]
12. **Exa Snapshot: 400B+ page snapshots over 20 years**, selectable via `snapshotAsOf` for point-in-time / leakage-free evaluation. [S — exa-snapshot]
13. **Exa trains and evaluates on agentic search, and publishes open evals** (WebCode, ATLAS, people/company benchmarks) that separate *contents quality* from *retrieval quality* and *correctness* from *groundedness*. [S — webcode, atlas-benchmark, people-search-benchmark, company-search-benchmarks]
14. **A better search backend improves RL training, not just inference**: 4B agents trained with Exa beat SERP-trained agents on every benchmark and often beat a 235B model; Exa needed 69% fewer tokens to reach parity. [S — rl-search-outcomes]
15. **Multi-region is achieved by replicating the full index + serving stack** (EU: AWS Stockholm, own GPUs for routers/vector DB/inference/rerankers/highlights; no silent fallback). [S — eu-data-residency]

---

## 2. Architecture — acquire → parse → embed → index → serve

Exa's own framing: web search has three fundamental pieces — **crawling documents, preprocessing them for retrieval, and serving queries** — and they rebuilt all three. [S — how-to-build-nextgen-search]

### 2.1 Acquisition (crawl)
- Constantly discover new URLs, crawl across a **distributed network of machines and IPs**, run documents through a **custom-built HTML parser**, store raw content in **S3**. [S — how-to-build-nextgen-search]
- Crawler is **ExaSearchBot**; respects `robots.txt` and per-site rate limits; `robots.txt` controls crawling while `noindex` meta/X-Robots-Tag controls indexing (removed on next re-fetch). [S — what-is-web-indexing]
- URL discovery is itself a quality problem: "most documents are low quality... a difficult challenge is identifying the best URLs." [S — how-to-build-nextgen-search]
- **Exa Snapshot** implies time-versioned storage: 400B+ snapshots spanning two decades, addressable by date. [S — exa-snapshot]

### 2.2 Parse / preprocess
- Custom HTML parser (above); for publications, **OCR + document-parsing models** turn PDFs into high-quality searchable text, joined with author/institution/citation/collaborator metadata. [S — publications-search]
- Preprocessing produces many derived artifacts per page (text, metadata, embeddings, structured extractions), each with its own update schedule and dependency surface. [S — exa-d]
- WebCode treats content extraction as a scored problem: strip nav/sidebars/chrome, keep prose, code, API signatures, tables; golden reference built from **rendered screenshots + DOM via a cloud browser + multimodal model**. [S — webcode]

### 2.3 Embed
- In-house trained transformer embedding models convert each document into an embedding (or set of embeddings). Original serving dim **4096 floats**. [S — how-to-build-nextgen-search, building-web-scale-vector-db]
- Training objective historically: **link/document prediction** — hide a link in text, predict the document that follows; billions of examples. Described as "neural PageRank" and "strictly more powerful than PageRank" because paraphrases of the same target are learned. [S — latent.space, building-search-post-chatgpt]
- Later stages add synthetic data + supervised fine-tuning for controllability/robustness (analogy to LLM post-training). [S — latent.space]

### 2.4 Index
- Two coupled indexes: a **dense vector index** (clustered, binary-quantized) and a **sparse BM25 inverted index**. [S — building-web-scale-vector-db, bm25-optimization]
- Metadata **filter indexes**: hashmaps from filterable value → doc IDs; filtering restricts the search to matching docs. [S — building-web-scale-vector-db]
- Vertical indexes (people, company, publication, places, podcast, products, code) are separate/derived indexes queried and fused with the web index. [S — publications-search, people-search-benchmark, company-search-benchmarks, webcode]

### 2.5 Serve
- Query → orchestrator DAG (classification, localization, retrieval, ranking) across multiple indexes concurrently; target **250ms** end-to-end for a serving query. [S — composing-a-search-engine]
- Retrieval is multi-stage: candidate generation → fetch extra → rerank with uncompressed data → highlights → optional answer/agent loop. [S — building-web-scale-vector-db, highlights-for-agents]
- **Canon** is the orchestrator (see §7); **exa-d** is the offline data plane (see §8). [S — composing-a-search-engine, exa-d]

---

## 3. Embeddings & models

### 3.1 Embedding model
- **Dimension: 4096** floats for the served model (Dec 2024). [S — building-web-scale-vector-db]
- **Matryoshka Representation Learning (MRL)** is used so prefixes are valid embeddings: first 2048 dims are a good embedding, 1024 also good, down to ~32. Exa truncates to **256 dims** for the index, a **20x memory reduction**. [S — building-web-scale-vector-db]
- Exa 3.0: "Trained a **larger embedding model with more compute and data than any previous model**." Exact size/dims not disclosed. [S — exa-3] **[?]** 3.0 dimension unknown; may still be 4096 base with MRL truncation.
- People search uses **fine-tuned Exa embeddings** + Exa search in a **hybrid** setup; company search similarly "fine-tuned our retrieval model." [S — people-search-benchmark, company-search-benchmarks]
- Training data is a deliberate moat: "novel methods for gathering embedding training data from the web"; quality of training data controls output quality; LLMs used as labelers for search relevance ("simple questions about billions of things"). [S — how-to-build-nextgen-search, latent.space]

### 3.2 Prompts / query vs doc
- No explicit "query prefix vs document prefix" convention is disclosed. The training objective is **asymmetric link prediction** (text context → predicted document), which is the closest thing to a query/doc distinction. [S — latent.space] **[I]** The serving asymmetry (float query × binary doc) is an *inference-time* asymmetry, not necessarily a prompt asymmetry.
- Query side is float (uncompressed); document side is binary-quantized. [S — building-web-scale-vector-db]

### 3.3 Quantization
- Binary quantization: each of 256 dims → 1 bit (sign: >0 → 1, else −1). Another **16x** reduction. [S — building-web-scale-vector-db]
- No product-quantization (PQ) / scalar-quantization details are published beyond this. **[?]**

### 3.4 Reranker
- A reranker is trained on the Exacluster ("training a reranker" listed as a concurrent workflow). [S — meet-the-exacluster]
- Retrieval recovers recall by fetching extra candidates and **reranking with uncompressed data**. [S — building-web-scale-vector-db]
- **Size / architecture / license: not disclosed.** [S — none]

### 3.5 Generator / answer model
- `/answer`, Deep, and Websets agent loops consume **highlights, not raw page content**. [S — highlights-for-agents]
- Agent Ultra uses **frontier models where needed and faster models where sufficient**, across many subagents. Specific models are not named as Exa's own. [S — exa-agent-ultra]
- **[?]** Exa does not appear to ship its own general LLM; the "generator" is a harness over third-party/frontier models plus its own highlights + reranker. **[I]**

### 3.6 Highlights model
- In-house highlights model; "product of many rounds of research"; runs **per request, uncached, <100ms**. [S — highlights-for-agents]
- Dynamic Highlights uses **one forward pass** over all retrieved docs concatenated into one unified document. [S — dynamic-highlights]
- Architecture/size not disclosed. [S — none]

---

## 4. Vector DB / ANN

Source: "How we built a web-scale vector database" (Dec 2024) is the canonical reference. [S]

### 4.1 Requirements
- Search **billions of vectors**, each 4096 floats. [S]
- Metadata filtering (date range, domain, category). [S]
- **<100ms** query latency. [S]
- **>500 QPS** at reasonable cost. [S]

### 4.2 Five optimizations
1. **Matryoshka truncation:** 4096 → 256 dims (keep first 256). **20x** memory reduction. [S]
2. **Binary quantization:** 16-bit float → 1-bit sign. **16x** more. [S]
3. **Asymmetric dot product:** keep binary document vectors, **float query vector**, dot-product similarity. Length-4 (or 8) subvectors; each binary 4-subvector has 16 possible values; **precompute all 16 dot products** into a LUT. Cuts compute by 1/m (mostly m=4 or 8). [S]
4. **LUT in CPU registers:** entire lookup table loaded into registers, faster than RAM. This part was written in **C++ rather than Rust** for performance. [S]
5. **Clustering:** **100,000 clusters** by similarity; at query time find the query's cluster and search only it + nearby clusters. **~1000x throughput** improvement with little accuracy loss. [S]

### 4.3 Recall recovery
- Optimizations are lossy; **fetch extra results and rerank with uncompressed data**. [S]

### 4.4 Filtering
- Per filterable value (category, date, etc.) build an **inverted index**: hashmap value → list of doc IDs. Only search docs that match the filter. [S]
- **Clustering fits filters better than HNSW**: HNSW's global graph "can't be partitioned easily"; clusters can be sharded and filtered. [S]

### 4.5 System properties
- **10x cheaper** than cloud vector DB quotes. [S]
- **Shardable by cluster** (unlike a global HNSW graph). [S]
- A **custom query language** defines multi-stage pipelines for different scoring algorithms. [S]

### 4.6 Serving-engine details
- Vector DB, API routers, inference, rerankers, and highlights services run on **own GPUs**; in the EU region all of these run in Stockholm. [S — eu-data-residency]
- Highlights server migrated Python → **Rust** to 4x throughput on one 8×A100 node; rayon + tch-rs; watch CUDA async timing and thread-safety (parallel iterators across GPUs caused OOM; serial iterators + separate CPU-return passes fixed it). [S — scaling-our-highlights-server]

**[?]** Exact ANN recall numbers, cluster count per shard, centroid training algorithm (k-means?), and update/merge policy for the vector index are not published.

---

## 5. Lexical / hybrid

### 5.1 BM25 structure
- In-memory inverted index: hashmap `token_id → Vec<(doc_id, freq)>`, sorted ascending by doc_id. [S — bm25-optimization]
- **>1.8 TB RAM per 1B indexed documents** across distributed workers before optimization. [S]

### 5.2 Query algorithm
- **Selective initial retrieval:** identify rarest query terms (highest IDF), use their postings lists to build a targeted candidate set ("impact-ordered indices"). [S]
- **Threshold-based pruning:** dynamically drop documents that mathematically cannot reach top-k (WAND-style). [S]
- Result: **sub-500ms** to retrieve thousands of top results. [S]

### 5.3 Memory optimizations (cumulative)
1. **Frequency grouping:** `(freq → [doc_ids])` instead of `(doc_id, freq)` per doc; freq is small (1–15). [S]
2. **Delta + variable-length encoding of doc IDs:** average 4 bytes → **1.3 bytes** per doc ID. [S]
3. **zstd** over each postings list (streamable encode/decode, low latency). [S]
4. **Consolidated buffers:** flatten all inner lists into one `Vec`; `unique_freq_values` bitset (2 bytes for 1–15); reserved `SEPARATOR` byte (encode `doc_id+1` so no byte is zero). ~16 bytes overhead for a 100-doc/15-freq list. [S]
5. **Singleton optimization:** tokens in only one doc → store just the doc_id (avoid 24B Vec + freq + padding). [S]
6. **Consolidated buffers 2.0:** one continuous `Vec` for all postings; hashmap entry becomes `(offset, len)` = **8 bytes** (down from 24). [S]

### 5.4 Result
- **>50% memory reduction**, no performance drop; average query latency actually **dropped ~10%** (better cache locality). [S]
- Benefits: larger candidate pools, lower cost, faster cold starts, better hybrid quality. [S]

### 5.5 Fusion
- **Reciprocal Rank Fusion (RRF)** with **k=60**, fusing dense and sparse result lists. [S — composing-a-search-engine]
- The DAG example: dense retrieve (web, 50 results) + sparse retrieve (inverted, 30 results) → RRF fuse (k=60) → fetch content. [S]
- **[?]** Whether weights (beyond RRF k) or score normalization are used is not disclosed.

---

## 6. Highlights

### 6.1 Per-page highlights (standard)
- Extract spans of each document relevant to the agent query; reduce search tokens ~5x vs full content. [S — dynamic-highlights]
- **500 chars of highlights ≈ first 8,000 chars of page** on SimpleQA → **16x fewer tokens**; **4k chars of highlights > 32k chars of full text**. [S — highlights-for-agents]
- Runs for **every request, not cached**, completes in **<100ms**. [S — highlights-for-agents]
- Big gains on long technical docs (API refs, SDK docs, specs, papers): **60% vs 6%** at a 500-char budget. [S — highlights-for-agents]
- Powers `/answer`, Deep, and Websets agent loops. [S — highlights-for-agents]

### 6.2 Dynamic Highlights (cross-result)
- **Token-level, not document-level:** selects tokens with awareness of *all* returned documents. [S — dynamic-highlights]
- **One forward pass** over a single unified document (all retrieved docs concatenated), allocating more tokens to better content and none to irrelevant content. [S — dynamic-highlights]
- **95% average token reduction** vs full page content. [S — dynamic-highlights, exa-3]
- Evals:
  - Single-turn, 12k-char budget: **+40% token efficiency** vs existing highlights, **+3.8% quality**. [S]
  - Agentic (Exa Agent, Auto on BrowseComp + WideSearch; Medium on internal company/people): **30% reduction in agent token usage**, **+2.1% avg quality**. [S]
- API: `contents.highlights.dynamic = true`. [S]
- GA in Exa 3.0 at no extra charge; "model efficiency improvements made it substantially faster and cheaper." [S — exa-3]

### 6.3 Token budgets
- Single-turn evals averaged across four runs with different character limits; 12k chars is the cited budget. [S — dynamic-highlights]
- Per-doc budget in standard highlights can starve highly relevant docs — the motivation for dynamic (cross-result) allocation. [S — dynamic-highlights]

---

## 7. Orchestration & observability

### 7.1 Canon (search orchestrator)
- Search is "a graph of 20+ node types with many branches"; Canon makes the pipeline an explicit **typed DAG**. [S — composing-a-search-engine]
- Node types: `retrieve` (dense/sparse, index, numResults), `fuse` (method `rrf`, k), `fetch_content`; root specifies output/query/numResults. [S]
- **Benefits:** automatic parallelism (independent nodes run concurrently), durable execution (retry from failed node without re-running predecessors), introspectability (the graph is data → visualize/validate/analyze), and **definition decoupled from execution** (same graph runs sync in tests, distributed in prod, dry-run for previews; caching/retries/tracing live in the executor). [S]
- **When a DAG is wrong:** reactive event loops (no work to schedule), consensus protocols (need one sequence), feedback loops (cycles until fixed point). [S]
- **Observability:** compile pipeline to a serializable graph; trace the exact path to answer "why did query X at date Y fail to return URL Z, even if it was the obvious result." [S]

### 7.2 Runtime semantics
- **Pull-based:** a node runs only when a downstream consumer demands its value → laziness + cancellation propagation for free. [S]
- **Memoization:** diamond dependencies compute the shared ancestor once. [S]
- **Cancellation:** if a parent is cancelled (timeout, client disconnect, lost a race), all children are cancelled. [S]
- **Tracing:** runtime sits at every invocation boundary and records timing, inputs, outputs, decisions; errors enriched with failing node + upstream context. [S]
- **Uniform interface requirement:** if a node makes its own network call, the runtime cannot cancel/cache/trace it — the node becomes invisible. [S]
- **Totality / typestate:** every node must handle every outcome; the type checker rejects graphs with unhandled branches. [S]

### 7.3 Offline orchestration (training / data)
- **Flyte** is the scheduler for the ML cluster: code-first Python, local run, PyTorchJob/MPIJob, Ray/KubeRay burst, task caching + checkpoint/resume, dataset/artifact lineage, priority queues, cloud burst. [S — meet-the-exacluster]
- **Pulumi** (Python IaC) → **Ansible/Kubespray** → **NVIDIA GPU/Network Operators** → **Alluxio** → **Flyte**. [S — meet-the-exacluster]

---

## 8. Data plane — exa-d

Source: "exa-d: Data Framework to Process the Web" (Jan 2026). [S]

### 8.1 Why a custom framework
- Web properties: many derived artifacts per page, heterogeneous content (HTML/PDF/JS apps/multimedia), varying update frequency (hourly news vs never-changing papers), petabytes of raw content. [S]
- Rejected warehouses / SQL transformation layers / existing orchestrators; built a framework around three priorities: typed columns + declarative dependencies; surgical updates + full rebuilds; efficient parallel execution from tens to thousands of nodes. [S]

### 8.2 Logical layer — dependency graph
- Columns are typed; derived columns declare intent: `Column(name, type).derive()._from(...).impl(Tokenizer/EmbeddingModel)`. [S]
- Execution order is derived from the graph, not hardcoded scripts. [S]
- Column definitions are contracts (e.g. `Tokenizer: str → Tensor`); builder pattern enforces type guarantees. [S]
- Adding a field = add a node + edges, not duplicate a pipeline. [S]

### 8.3 Storage layer — Lance on S3
- Data lives in **Lance** (columnar) on **S3**, as **fragments with partial schemas**. [S]
- Core operation: **write or delete a single column for a specific fragment without rewriting the rest of the fragment** (`write_column_to_fragment`, `bind_file_to_fragment`, `commit_to_lance`). [S]
- Lance uses a **global manifest** on S3; manifest update is atomic (compare-and-swap / rebase). [S]
- Fragment metadata records which columns are present → no auxiliary validity tables; targeted debugging by deleting/invalidating a column on specific fragments. [S]
- Avoids write amplification: small appends / small replacements rather than rewriting all rows. [S]

### 8.4 Execution layer
- Query planning = **diff between ideal state (all columns populated) and actual state**; topological sort ensures a column computes after its dependencies; per-fragment parallelism; **checkpoints after each fragment**. [S]
- Single execution rule: **compute missing or invalid columns** — backfills and incremental updates share one code path. [S]
- **Ray Data** executes the topologically sorted graph; each graph node = a Ray Data pipeline stage; **Ray Actors** load the embedding model once and stay resident (model load can take seconds→minutes); separate Actor stages give pipeline parallelism (GPU embeds one fragment while CPU tokenizes the next and network fetches a third). [S]
- **Convergence:** rerunning after partial failure eventually reaches the same fully-computed state. [S]

### 8.5 Lineage / idempotence
- Dataset + artifact lineage tracked by Flyte (offline) and by column provenance (exa-d). [S — meet-the-exacluster, exa-d]
- Idempotence comes from "compute the diff" + atomic manifest commits. [I, grounded in S]

---

## 9. Serving & tiers

### 9.1 Search types / tiers
| Tier | Price (list) | Compute profile | Index |
|---|---|---|---|
| **Exa Lite** | **$4 / 1k requests** | Lower compute; same index as Auto | Same as Auto |
| **Exa Auto** | **$7 / 1k requests** | More compute across candidate generation, highlights, ranking | Same as Auto/Lite |
| **Websets** (high-compute) | usage-based, **$5 / 1k searches** (V2) | Minutes-scale, exhaustive list building | Web + vertical DBs |
| **Exa Agent / Ultra** | effort-based | Multi-agent, thousands of sources | Full stack |

Source: exa-3, how-to-build-nextgen-search, websets-v2, exa-agent-ultra. [S]
- **Lite and Auto share the index**; differentiation is compute, not coverage. [S — exa-3]
- "Together, Lite and Auto set a new Pareto frontier for search." [S — exa-3]
- Websets V2 is **4x faster, 2x cheaper**, accuracy + recall +20%; usage-based, no subscription. [S — websets-v2]

### 9.2 Latency budgets
- Serving a query (classification + localization + retrieval + ranking across indexes) in **~250ms**. [S — composing-a-search-engine]
- Vector search **<100ms**. [S — building-web-scale-vector-db]
- Highlights **<100ms**. [S — highlights-for-agents]
- BM25 **sub-500ms** for thousands of results. [S — bm25-optimization]
- End-to-end "fastest search API in the world at **sub-450ms**" (2025 claim). [S — announcing-series-b]
- Publications search **0.578s ± 0.017** mean latency (Exa). [S — publications-search]
- EU vs US: EU endpoint saves **>100ms** for EU users. [S — eu-data-residency]

### 9.3 Caching / freshness
- Highlights are **not cached** (per request). [S — highlights-for-agents]
- `maxAgeHours` limits cached content age; `0` forces a live fetch every request. [S — what-is-web-indexing]
- Monitors keep per-run state ("remembers what it's already seen") and only push changes. [S — monitors-v2]

### 9.4 Auth / residency / limits
- **Zero Data Retention (ZDR)** available on all product endpoints (possible because Exa owns the stack). [S — announcing-series-b]
- **EU residency:** `api.eu.exa.ai`, region-locked API keys, no silent fallback, `x-exa-processing-region: eu` header, TLS terminated in EU, ZDR default. [S — eu-data-residency]
- Rate limits exist (Snapshot full coverage/rate limits gated by sales). [S — exa-snapshot]

### 9.5 API surface
- `/search`, `/contents`, `/answer`, Deep, Websets, Monitors, Agent; `category` filters (company, people, publication, news, personal site, financial report, etc.); `contents` with `text`, `highlights` (incl. `dynamic`), `summary`; `snapshotAsOf`; `maxAgeHours`; `numResults`; `type` = `lite|auto|deep` (deep referenced in webcode). [S — various]
- **Monitors v2:** 3 stages — Retrieve (fast search, time window matched to cadence) → Judge (drop seen; checks relevance, source legitimacy, new information, event timing) → Compose (summary or JSON matching `outputSchema`, with sources + per-field confidence); webhook push; **$2 / 1k runs** (from $15). [S — monitors-v2]
- **Websets V2:** usage-based; searches at **$5 / 1k**; per-match costs vary with difficulty ($0.001 to $0.044 in examples). [S — websets-v2]

### 9.6 Cost notes
- Lite is aimed at cost-sensitive apps; Exa claims Exa 3.0 lets agents do **20–50% fewer search queries per task** than other providers (Artificial Analysis). [S — artificial-analysis]
- Websets V2: average cost per match ~50% lower than legacy; Vanguard example 454 candidates reviewed → 100 matches at $0.001/match; hard climate-tech example 6,000+ candidates → 19 matches at $0.044/match. [S — websets-v2]
- Vector DB was **10x cheaper** than cloud vector DB quotes. [S — building-web-scale-vector-db]

---

## 10. Scale & hardware

### 10.1 Exacluster (H200)
- **$5M** purchase; **144× H200-141GB**; **18 nodes × 8 GPUs**. [S — meet-the-exacluster]
- **20 TB HBM3**, **3,456 Xeon threads** (192/node), **36 TB DDR5-5600**, **270 TB Gen-4 NVMe** (12.8 TB/node), **100 kW**. [S]
- Lenovo ThinkSystem SR680a V3; Mellanox ConnectX-7 + BlueField-3 DPUs; GPUDirect RDMA / RoCE. [S]
- Tom's Hardware: **569,958 TOPS (~570 PetaTOPS)**, 141GB HBM3E per GPU. [S — tomshardware]

### 10.2 Older cluster (A100)
- **80× A100-80GB** (10 nodes × 8), Supermicro AS-4124GO-NART+, **6.4 TB HBM**, **960 EPYC threads** (96/node), **10 TB DDR4**, **~80 TB Gen-4 NVMe**, dual 100 GbE + NVLink v3. [S — meet-the-exacluster]
- Half of the 2021 seed money went into this first cluster. [S]

### 10.3 Combined
- **28 nodes, 224 GPUs, 26.4 TB GPU RAM, 4,416 CPU cores, 46 TB system RAM, 350 TB NVMe, ~168 FP16 PFLOPs.** [S — meet-the-exacluster]
- A run that took a week now takes ~1 day. Rebuild bare metal → 224 GPUs in **<1 hour**. [S]

### 10.4 Infra stack ("Hephaestus")
- **Pulumi** (Python IaC, mypy-typed) → **Ansible/Kubespray** (K8s, Calico CNI) → **NVIDIA GPU Operator** (driver/CUDA, `nvidia.com/gpu`, MIG, DCGM→Prometheus) + **Network Operator** (OFED, GPUDirect RDMA, RoCE, ConnectX-7/BlueField-3) → **Alluxio** (fuse ~350 TB NVMe into a distributed cache; S3 authoritative; sync/async write; S3-compatible endpoint) → **Flyte** (scheduler; PyTorchJob/MPIJob; Ray/KubeRay; task cache; checkpoint/resume; lineage; priority/quotas; logs→Loki, metrics→Prometheus, artifacts→S3). [S]

### 10.5 Scale metrics
- Index tracks **>2 trillion URLs**, serves **~100B pages** (Exa 3.0); Monitors v2 says **130B+ web pages**. [S — exa-3, monitors-v2] **[?]** 100B vs 130B inconsistency.
- **1.27B** ecommerce/product listings. [S]
- **211M** places. [S]
- **~350M** publications (publications-search) vs **500M+ research papers** (websets-v2). [S] **[?]** inconsistency.
- **3.2M** podcast episodes / 119k shows / 23.7B words / 2.2M hours. [S]
- **1B+ people**, **70M+ companies**. [S]
- **400B+** page snapshots over 20 years. [S]
- People ingestion pipeline built for **50M+ updates/week**. [S]
- Cluster 1 inference requirements grew **100x** by late 2024. [S]

### 10.6 Multi-region
- **EU:** AWS Stockholm (`eu-north-1`); full index replicated (petabytes, real-time across two continents); routers, vector DBs, inference, rerankers, highlights on own GPUs. [S — eu-data-residency]
- Mix of owned cluster + AWS for inference; "more inference for search for sure." [S — latent.space]

---

## 11. Evals

### 11.1 WebCode (coding agents, Mar 2026)
- Open-sourced (github.com/exa-labs/benchmarks). Splits **contents quality** vs **retrieval quality**.
- **Contents quality:** golden extraction from rendered screenshots + DOM (Browserbase + multimodal model → markdown) over **250 URLs** from simulated coding-agent search distributions. Metrics: LLM-judged (completeness, accuracy, structure) + deterministic (signal, code recall, table recall, ROUGE-L). Results (0–100): Exa 82.8 / 94.5 / 81.8 / 89.3 / 96.7 / 91.9 / 83.2; Parallel 74.2 / 77.6 / 80.8 / 89.2 / 94.1 / 92.2 / 73.7; Claude 59.8 / 55.1 / 75.1 / 81.1 / 82.4 / 82.0 / 66.8. [S]
- **Highlights eval reframed as discriminative:** *groundedness* (do highlights contain the gold answer?) vs *correctness* (does synthesized answer match?). Correctness clusters ~86% across providers; groundedness has higher variance and better isolates search quality. [S]
- **Retrieval quality:** 317 queries generated from long-context docs (up to millions of chars), requiring niche facts that two frontier models fail to answer from parametric memory over 3 completions; 5 providers (Exa, Brave, Perplexity, Parallel, Tavily); groundedness + citation precision. [S]
- **End-to-end coding tasks:** Modal sandbox, bash + unit tests; seed libraries >200 GitHub stars with releases after Aug 1 2025 having ≥3 breaking changes; difficulty-gated against frontier models with up to 10k reasoning tokens. [S]

### 11.2 ATLAS (agentic search, Oct 2026)
- **547** deep+wide research tasks from clustered anonymized search demand; discover every entity meeting conditions + enrich 2–10 multi-hop attributes. [S]
- Construction: median **8 agent-hours + 1,200 searches per task**; committee of frontier models + providers; two builders (Codex/GPT-6 Astra, Claude Code/Opus 5.5); provider-neutral interleaved search (Exa, Brave, Perplexity). [S]
- Metrics: **Discovery F1**, **Row F1** (headline; correct only if every cell correct), **Item F1**. [S]
- Memorization: **9%** (BrowseComp 48%, WideSearch 59%, DeepSearchQA 61%). [S]
- Grading: deterministic where possible + LLM judge on ~4.5% of cells; **~$0.0004/answer, ~15s/answer, ~$0.24/system on 547 tasks (~$2 per 10 runs)**; 98.6% regrade agreement. [S]
- Results: best system **0.66 Row F1 at $8.92 and 18 min/task**; **no system under $1/task reaches 0.5 Row F1**. Hiding top-7-of-10 results halves ATLAS score (vs 81–89% retained on BrowseComp/WideSearch/DeepSearchQA). [S]
- 74% of tasks require ≥10 entities; median 4 domains for discovery, 18 domains for full enrichment. [S]

### 11.3 People search (Dec 2025)
- **1B+ people**; **hybrid** fine-tuned Exa embeddings + Exa search; ingestion **50M+ updates/week**. [S]
- **1,400** role-based queries (targeted lookup + role-based discovery); recall@k, NDCG for lookup; LLM judge for discovery; sourced from 10k historical queries clustered into 3 categories. [S]

### 11.4 Company search (Jan 2026)
- **~800 queries**; retrieval track **605** (named lookup, attribute filtering, funding, composite, semantic); RAG track **201** (static + dynamic facts). LLM-hard dataset deliberately avoids memorized unicorns. [S]

### 11.5 Publications search (Jul 2026)
- Exa recall **86.4%**, MRR **0.726**, latency **0.578s**; Perplexity 66.8% / 0.568 / 1.277s; Parallel Advanced 50.0% / 0.312 / 3.118s; Parallel Turbo 39.2% / 0.278 / 0.403s; Google Scholar 28.0% / 0.179 / 1.098s. "Correct paper for 82.8% of queries." [S]

### 11.6 Places (Oct 2026)
- **400 queries**; F1 for correct metadata: Exa Fast **0.800**, Perplexity 0.529, Parallel Advanced 0.333. [S]

### 11.7 Podcasts (Oct 2026)
- 250 active shows: Exa returns newest episode in top-5 **98.4%**; 667 questions: **85.0%** correct. [S]

### 11.8 RL outcomes (May 2026)
- Qwen3-4B-Instruct-2507 + LoRA (Tinker); Exa vs SERP backend; 5 results × 2,000-char snippets; MuSiQue/HotpotQA + Dr. GRPO; SimpleQA LLM grader; −0.25 penalty on context overflow. [S]
- Exa-trained 4B beats SERP-trained on all six benchmarks, often beats 235B (e.g. SimpleQA 0.767 vs 0.692 SERP vs 0.730 235B; 2Wiki 0.839 vs 0.798 vs 0.774). [S]
- Token efficiency: SERP needed **1.89B** tokens vs Exa **1.58B** to step 100 (20% more); Exa reached parity with **69% fewer tokens** (0.58B vs 1.89B), **62% fewer search calls** (93k vs 248k), **58% fewer turns** (146k vs 350k). [S]
- Per-action answer-containing rate: Exa **36.1±2.4%** vs SERP **32.6±2.3%** (+10.7%); first search call **34.0±2.5%** vs 30.5±2.5% (+11.5%). [S]

### 11.9 Earlier evals
- **API evals (Jan 2025):** SimpleQA with gemini-1.5-flash query gen + 4o-mini answer; MSMARCO 1,000 queries graded 1–5 by GPT-4o LLM-as-judge. [S]
- **Websets evals (Feb 2025):** 200 o1-generated queries; Google avg **16** correct, Websets low-compute **66**, high-compute **320** (~20x Google). [S]
- **Artificial Analysis (Oct 2026):** Exa 3.0 #1 for quality and fewest queries/task; 20–50% fewer queries than other providers. [S]

---

## 12. What to steal for our replica

### 12.1 Data plane
- **Adopt a columnar, fragment-based store (Lance or Parquet + a manifest) on object storage.** Model derived fields as typed columns with declared dependencies; plan execution as `diff(ideal, actual)`. This gives surgical updates, full rebuilds, and backfills on one code path. [S — exa-d]
- **Track completeness per (fragment, column)** in metadata; make manifest commits atomic (CAS). Never keep a separate "validity" sidecar table. [S — exa-d]
- **Pipeline-parallel execution:** separate worker pools per stage (network fetch / CPU tokenize / GPU embed) with **resident model actors**; gate scheduling on fragment completeness. [S — exa-d]
- **Convergence/idempotence** as a first-class property: rerun after partial failure must reach the same state. [S — exa-d]
- **Versioned/time-travel storage** (snapshot-by-date) from day one — it is cheap to add and unlocks leakage-free evals and backtests. [S — exa-snapshot]

### 12.2 Models
- **Train embedding models with MRL** so you can truncate dimensions at serve time without retraining; this decouples index memory from model quality. [S — building-web-scale-vector-db]
- **Asymmetric quantization:** float queries × binary docs + LUT is simple, fast, and CPU-friendly; avoid HNSW if you need filters/sharding. [S — building-web-scale-vector-db]
- **Preprocess with LLMs/embeddings; rerank a small candidate set** (10–1000) with a stronger model at query time. Do not run a large model over the whole index. [S — latent.space, how-to-build-nextgen-search]
- **Invest in a highlights model early** — it is the highest-leverage token/cost/latency lever and the substrate for answer/agent products. [S — highlights-for-agents]
- **Use LLMs as labelers** for relevance at web scale (cheap, better than human keyword matching for semantic relevance). [S — latent.space]
- **Train on a link-prediction / document-prediction objective** if you can build a crawl with link context; it bakes in a quality/canonicity prior (neural PageRank). [S — latent.space, building-search-post-chatgpt]

### 12.3 Index
- **Clustered binary-quantized ANN with register-resident LUT**; size clusters so a query scans cluster + a few neighbors; shard by cluster. [S — building-web-scale-vector-db]
- **Hybrid by default:** dense + BM25 + RRF (k≈60). Build the BM25 index memory-efficiently from the start (freq grouping, delta+varint, consolidated buffers, singleton special-case, zstd). Memory is the binding constraint at billions of docs (>1.8 TB/1B). [S — bm25-optimization, composing-a-search-engine]
- **Filter via inverted indexes value→docIDs**, and prefer cluster-based ANN over graph-based ANN precisely because filters/sharding compose better. [S — building-web-scale-vector-db]
- **Design a small query DSL / DAG** for multi-stage scoring so retrieval pipelines are data, not code. [S — building-web-scale-vector-db, composing-a-search-engine]

### 12.4 Serving
- **Tier by compute, not by index** (Lite/Auto share an index; spend more on candidates/highlights/ranking for higher tiers). This keeps a single corpus and a simple pricing story. [S — exa-3]
- **Orchestrator as a typed DAG with a pull-based runtime**: free parallelism, cancellation, memoization, and full tracing with no per-node instrumentation. Enforce a uniform node interface so nothing bypasses the runtime. [S — composing-a-search-engine]
- **Latency budget targets:** vector search <100ms, highlights <100ms, BM25 <500ms, full serving ~250ms. [S — various]
- **Highlights uncached per request** (query-dependent); cache raw content with `maxAgeHours` and allow live fetch at 0. [S — highlights-for-agents, what-is-web-indexing]
- **Multi-region by replicating the whole serving stack + index**, region-locked keys, no silent fallback, per-response processing-region header. [S — eu-data-residency]
- **Offer ZDR** as a design property of owning the full stack. [S — announcing-series-b]
- **Monitors pattern:** retrieve → judge (dedupe + relevance/legitimacy/new-info/timing) → compose (structured output + citations + confidence) → webhook. [S — monitors-v2]

### 12.5 Eval
- **Separate contents quality from retrieval quality**; grade extraction against rendered-DOM golden references, not raw HTML. [S — webcode]
- **Separate correctness (generative) from groundedness (discriminative)** — groundedness isolates the search provider; correctness mostly measures the synthesis model. [S — webcode]
- **Build unmemorized, wide+deep, cheap-to-grade evals** (ATLAS-style): fixed audited answer keys, deterministic grading where possible, report Row/Item/Discovery F1, and measure memorization + search-degradation sensitivity. [S — atlas-benchmark]
- **Measure cost and latency alongside quality** (Pareto frontier), not quality alone. [S — atlas-benchmark, eu-data-residency]
- **Test whether a better backend improves RL training**, not just inference (denser per-step reward). [S — rl-search-outcomes]
- **Publish open harnesses** to attract ecosystem and enable reproducibility. [S — webcode, people-search-benchmark, company-search-benchmarks]

### 12.6 Suggested blueprint for our replica (mapped)
| Subject | Concrete choice |
|---|---|
| **Data plane** | Lance/Parquet on S3/MinIO; typed column DAG; per-fragment per-column patching; Ray Data + resident embedding actors; snapshot-by-date |
| **Models** | MRL-trained embedder (e.g. 1024–4096 base, truncate to 256–512); binary doc quantization; small cross-encoder reranker; highlights model; link-prediction pretraining if crawl supports it |
| **Index** | Clustered binary-ANN + register LUT (C++/Rust); sharded by cluster; BM25 with freq-grouped delta+varint+zstd consolidated buffers; RRF k≈60; inverted filter indexes |
| **Serving** | Typed-DAG orchestrator with pull runtime + tracing + cancellation; Lite/Auto tiers on one index; highlights uncached; maxAgeHours cache; ZDR; region replication |
| **Eval** | WebCode-style extraction + groundedness; ATLAS-style wide/deep F1 with cost/latency; open harness |

---

## 13. Uncertainties / contradictions

- **Index size:** Exa 3.0 / what-is-web-indexing say **~100B pages served**, **>2T URLs tracked**; Monitors v2 says **130B+ web pages**. [S, contradictory]
- **Publications count:** publications-search says **~350M publications**; Websets V2 says **500M+ research papers**. [S, contradictory]
- **Embedding dimension for Exa 3.0:** only the Dec 2024 **4096** base dim is documented; Exa 3.0 says "larger model" without dims. Whether serving is still 256-dim MRL truncation is not stated. [S — exa-3] **[?]**
- **Reranker details:** existence confirmed ("training a reranker", "rerank with uncompressed data"), but architecture, size, license, and whether it is trained in-house vs open-source are undisclosed. [S — meet-the-exacluster, building-web-scale-vector-db] **[?]**
- **Highlights model architecture/size:** undisclosed. [S — none]
- **Generator/answer models:** Exa appears to use frontier/third-party models in agent harnesses; no evidence of an Exa-owned general LLM. [I]
- **Cluster CPU count:** Exa blog says **3,456 Xeon threads (192/node)** for 18 nodes; Tom's Hardware headline says "192 96-core CPUs", which is ambiguous/inconsistent with 18×2 sockets. Trust the Exa blog's 192 threads/node. [S, contradictory]
- **ANN recall / cluster count / centroid algorithm / update policy:** not published. [S — none]
- **Fusion weights:** RRF k=60 is documented; any additional per-index weighting or score normalization is not. [S — composing-a-search-engine] **[?]**
- **ATLAS grading cost:** Table 1 says "$2" for 10 full runs; text says ~$0.24/system on 547 tasks (~$2.40 for 10) and $0.0004/answer. Roughly consistent, minor rounding. [S]
- **"Exa Lite runs on same index as Auto"** is explicit; whether Lite uses a *subset* of clusters/shards is not stated. [S — exa-3] **[?]**
- **Pricing** is list price as of the cited posts (Oct–Nov 2026) and may change; Websets V2 usage pricing ($5/1k searches) differs from Search pricing ($4–7/1k). [S]
- **Marketing vs measurement:** many comparative numbers (Artificial Analysis, "20x better than Google", "SOTA") are vendor-run or vendor-reported; treat as directional, not independently verified. [I]
- **No source describes the crawl frontier / URL-selection ranking model, dedup/canonicalization pipeline, or anti-bot strategy in technical detail** beyond "distributed network of machines and IPs", "custom HTML parser", and data partnerships. [S — how-to-build-nextgen-search, latent.space]

---

## 14. Sources

Exa blog (all https://exa.ai/blog/…):
1. https://exa.ai/blog/exa-3 — Introducing Exa 3.0 (Oct 19, 2026)
2. https://exa.ai/blog/building-web-scale-vector-db — How we built a web-scale vector database (Dec 17, 2024)
3. https://exa.ai/blog/meet-the-exacluster — Meet the Exacluster (May 15, 2025)
4. https://exa.ai/blog/bm25-optimization — Serving BM25 with 50% memory reduction (May 5, 2025)
5. https://exa.ai/blog/composing-a-search-engine — Composing a Search Engine / Canon (Apr 17, 2026)
6. https://exa.ai/blog/exa-d — exa-d: Data Framework to Process the Web (Jan 13, 2026)
7. https://exa.ai/blog/dynamic-highlights — Dynamic Highlights (Aug 28, 2026)
8. https://exa.ai/blog/scaling-our-highlights-server — Scaling our highlights server (Feb 21, 2024)
9. https://exa.ai/blog/how-to-build-nextgen-search — How we're building the next generation of search (Mar 11, 2025)
10. https://exa.ai/blog/perfect-search — A Perfect Search Engine (Jan 7, 2025)
11. https://exa.ai/blog/webcode — WebCode: Search Evals for Coding Agents (Mar 23, 2026)
12. https://exa.ai/blog/atlas-benchmark — ATLAS: Evaluating Agents on Search-Intensive Tasks (Oct 8, 2026)
13. https://exa.ai/blog/exa-snapshot — Introducing Exa Snapshot (Sep 17, 2026)
14. https://exa.ai/blog/places-search — Introducing Exa Places (Oct 5, 2026)
15. https://exa.ai/blog/publications-search — SOTA Search Over Academic Publications (Jul 23, 2026)
16. https://exa.ai/blog/podcast-search — Introducing Exa Podcasts (Oct 29, 2026)
17. https://exa.ai/blog/exa-agent-ultra — Introducing Exa Agent Ultra (Sep 25, 2026)
18. https://exa.ai/blog/monitors-v2 — Introducing Monitors v2 (Oct 29, 2026)
19. https://exa.ai/blog/websets-v2 — Websets V2: 4x Faster, 2x Cheaper (Nov 17, 2026)
20. https://exa.ai/blog/rl-search-outcomes — How Search Quality Shapes RL Outcomes (May 13, 2026)
21. https://exa.ai/blog/api-evals — State-of-the-art web search API (Jan 24, 2025)
22. https://exa.ai/blog/websets-evals — Search that's >20x better than Google for complex queries (Feb 19, 2025)
23. https://exa.ai/blog/artificial-analysis-exa-3-best-search-api — Exa Ranks #1 on the Artificial Analysis Search Index (Oct 19, 2026)
24. https://exa.ai/blog/people-search-benchmark — Introducing Exa's People Search Benchmarks (Dec 17, 2025)
25. https://exa.ai/blog/company-search-benchmarks — Introducing Exa's Company Search Benchmarks (Jan 22, 2026)
26. https://exa.ai/blog/building-search-for-the-post-chatgpt-world — Building Search for the Post-ChatGPT World (Aug 8, 2023)
27. https://exa.ai/blog/what-is-web-indexing — What is web indexing (Oct 6, 2026)
28. https://exa.ai/blog/what-is-semantic-search — What is semantic search (Oct 1, 2026)
29. https://exa.ai/blog/highlights-for-agents — Exa Highlights: Quality, Token-Efficient Search (Apr 22, 2026)
30. https://exa.ai/blog/eu-data-residency — Exa Search, now in the EU (Nov 13, 2026)
31. https://exa.ai/blog/exa-google-cloud — Exa and Google Partnership (Apr 28, 2026)
32. https://exa.ai/blog/announcing-series-b — Exa raises $85M (Sep 3, 2025)
33. https://exa.ai/blog/superknowledge — We need superknowledge before superintelligence (Jul 12, 2024)

Third-party technical:
34. https://www.latent.space/p/exa — Beating Google at Search with Neural PageRank and $5M of H200s (Latent Space, Jan 10, 2025)
35. https://www.tomshardware.com/tech-industry/artificial-intelligence/nvidia-hopper-based-100kw-cluster-deploys-with-144-h200-gpus-exacluster-features-192-96-core-cpus-36tb-ddr5-ram-and-270tb-of-nvme-storage — Tom's Hardware Exacluster (Jan 11, 2025)