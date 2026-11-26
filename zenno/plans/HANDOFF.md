# Handoff — Exécution des plans Exa Replica

> Session de départ pour exécuter les plans. Cette session n'a pas l'historique : tout ce qu'il faut est ici + dans les fichiers cités.

## 1. Projet
Réplique open-source, auto-hébergée, de type Exa : **MCP + HTTP** (`/search`, `/contents`), pipeline complet (acquisition → parse → embed → index → serve). Objectif : architecture complète, invariante d'échelle, reproductible, sans dépendance unique. **Aucun code produit n'a encore été écrit** (D47) : la planification est close, on passe à l'evidence puis à M0.

## 2. Fichiers clés
- **Journal de décisions** : `docs/EXA_REPLICA_RESEARCH.md` — **D0–D103** (§6, tableau). C'est la source de vérité.
- **Contrat S2** : `docs/s2_contract_matrix.md` (v1.0-gate0 figé, sha256 `c2920819…595c43`) + §9 v1.1 (`degraded`, score normalisé).
- **TODO** : `docs/EXA_REPLICA_TODO.md` (S1–S9 + transverses ; 18 `[BLOCKER]` = evidence).
- **Specs S4** : `docs/s4_passage_spec_skeleton.md`, `docs/s4_manifest_schemas_v0.md`, `docs/s4_b_thresholds.md` (sha256 `4c9804f7…eeee`), `docs/s4_cleaning_lang_spec.md`, `docs/s4_b_tokens_protocol.md`, `docs/s4_t0_extractor_protocol.md`.
- **Contrats capturés** : `docs/contracts/exa-openapi-2.0.0.yaml` (sha256 `d625c66c…af499b`) + `docs/contracts/PROVENANCE.md`.
- **Plans (à exécuter)** : `zenno/plans/2026-11-26-M{0..5}-*.md`.

## 3. Décisions à connaître absolument
- **D39** : le **Thinkpad ne build jamais**. Tout travail lourd (ingest/embed/index, `cargo build`, baseline) → **RTX Pro 6000** (96 Go, 128 Go RAM, 16 vCPU, 500 Go NVMe) ou **Modal**. Le Thinkpad = docs/code léger uniquement.
- **D47** : pas de code avant planification complète. **Remplir les valeurs TBD par la mesure** (evidence), amender la décision avec valeur + source + date.
- **D36** : profil de mesure = 1× RTX Pro 6000.
- **D38/D40** : buckets HF `exa-replica-corpus` (write-once) + `exa-replica-artifacts` (no overwrite) ; manifests repo `exa-replica-manifests`.
- **D89 (amendé 2026-11-26)** : cible MCP = révision « Current » (2026-07-28), SDK `mcp` Python 2.x (MIT). Pas de requête serveur (elicitation/sampling/roots supprimés).
- **D95/D96** : layout `src/exa_replica/{domain,ports,application,adapters/{inbound,outbound},bootstrap,entrypoints}` + crate `ann-core` optionnel (R1, D82) ; import-linter down-only.
- **D97** : jalons M0→M5 par critères de sortie (gates 0–5).
- **D99** : `degraded` champ unique (D69) ; `unsupported_field` 400 (D27) ; `X-Index-Version` + 409 `index_version_mismatch` ; `X-Effective-Deadline-Ms`.
- **D102** : dev rules (mypy strict, ruff, import-linter, couverture ≥80% domain+application, PR ≤400, conventional commits, DCO).
- **D103** : OpenAPI + `tools/list` = snapshots versionnés, comparés en CI.

## 4. État
- **Planification close** : 104 décisions (D0–D103), 0 lacune.
- **Evidence en cours** : ✅ M0 prérequis (SDK MIT, OpenAPI capturé, `tools/list` capturé). ⏳ Bloqué sur infra.
- **18 `[BLOCKER]` = tous evidence** : S4 (1 : passage spec D44), S5 (5 : D81), S6 (10 : mesures C_util/R0/R1/BM25/D84 + vérif Tantivy + D68), S7 (1 : D89 cible + revue docs), Cross (1 : baseline run).

## 5. Ordre d'exécution
### Phase evidence (sans code produit, harness autorisé)
1. **Créer les buckets HF** (D38/D40) + quota guard (≤2.5 TB ; T0/T1 ≤500 Go) — **TODO humain** (voir §7).
3. **Run B** (buckets + T0, sur RTX) → geler **D44** (passage spec).
4. **D81** : choix modèle provisoire (golden set dev + T0).
5. **Baseline §5** : `cargo test`/build sur RTX ; inventaire read-only sur Thinkpad.
6. **Épingler** FastAPI + `mcp` 2.x (M0).
7. **Revue docs MCP** (D89) : retirer `initialize`/sessions/`Mcp-Session-Id`, exemples v1/FastMCP.
8. Chaque blocker levé → **amende la décision** (valeur + source + date).

### Phase implémentation (M0→M5, D97)
- **M0 Skeleton** (`zenno/plans/2026-11-26-M0-skeleton.md`) — pas de gate.
- **M1 Contract e2e** (Gate 0 D12 + Gate 1 §1.1).
- **M2 Eval dev** (pas de test run).
- **M3 Auto + gates** (Gate 2 + Gate 3 dev + Gate 4 pilote).
- **M4 Highlights S1** (D84 R1 + D94).
- **M5 Hardening + release** (Gate 3 test 1× + Gate 4 bloquant + Gate 5 + D91 + nom public + v0.1.0).

**Méthode** : skill `superpowers:subagent-driven-development` (un sous-agent par tâche + revue), ou `executing-plans` en natif.

## 6. Pièges / gotchas
- **`.env` contient `EXA_API_KEY`** : ne jamais lire/imprimer ; sourcer avant tout appel API. **Aucun appel API Exa** (ToS §4.2(f), D19/D71).
- **D44 (passage spec)** et **D81 (modèle)** = valeurs TBD par conception : ne pas inventer, attendre B.
- **D63** : déterminisme — stages exacts bit-exact ; flottants (embeddings) par `stage_key` + tolérance.
- **D68** : build et serving jamais simultanés (mono-GPU) ; 503 + Retry-After pendant rebuild.
- **D82** : R0 exact GPU par défaut ; R1 binaire+int8 en repli ; MRL/HNSW/PQ exclus v1.
- **D84** : highlights S0 extractif par défaut ; S1 seulement si gain ≥2 pts IC95.
- **D89** : MCP 2026-07-28 (pas 2025-11-25).
- **Référencer les décisions** : chaque choix du code cite `Dxx` (traçabilité).

## 7. Questions au humain (avant evidence)
1. **Buckets HF** `exa-replica-corpus` + `exa-replica-artifacts` : existent-ils ? Sinon, les créer + quota.
2. **Accès RTX Pro 6000 / Modal** : ai-je un shell, ou je fournis les commandes à lancer ?
3. **Baseline** : inventaire read-only (Thinkpad) d'abord, puis mesures (RTX) — OK ?

## 8. Première action
Lire `docs/EXA_REPLICA_RESEARCH.md` (§6 D0–D103) + `zenno/plans/2026-11-26-M0-skeleton.md`, puis lancer l'evidence (§5) ou M0 selon les réponses §7.