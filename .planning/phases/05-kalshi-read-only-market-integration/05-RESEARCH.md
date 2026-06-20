# Phase 5: Kalshi Read-Only Market Integration - Research

**Researched:** 2026-06-20  
**Domain:** Kalshi read-only market discovery, authenticated request signing, snapshot persistence, and job guardrails [CITED: .planning/ROADMAP.md] [CITED: .planning/REQUIREMENTS.md] [CITED: .planning/STATE.md]  
**Confidence:** MEDIUM-HIGH

## User Constraints

- Scope remains ATP only and Kalshi only. Phase 05 must not broaden tour coverage or introduce other betting venues. [CITED: AGENTS.md] [CITED: .planning/PROJECT.md]
- Read-only is a hard boundary. Phase 05 may collect, normalize, and persist market data, but it must not place, stage, or prepare orders. [CITED: AGENTS.md] [CITED: .planning/REQUIREMENTS.md]
- Kalshi SDK/API payloads must stay behind project-owned interfaces. Business logic should consume normalized DTOs, not raw transport objects. [CITED: .planning/REQUIREMENTS.md]
- Existing repo patterns favor repo-local paths, typed contracts, DuckDB-backed persistence, and thin file writers. Phase 05 should extend those patterns instead of creating a separate storage stack. [CITED: src/tennisprediction/config.py] [CITED: src/tennisprediction/storage/duckdb.py] [CITED: src/tennisprediction/modeling/reports.py]
- Engineering quality remains mandatory: modular, typed, logged, configurable, reproducible code with focused tests for request signing, pagination, persistence, and guardrails. [CITED: AGENTS.md]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| KAL-01 | System provides a Kalshi-only read client with authenticated market listing, market detail, and orderbook retrieval. [CITED: .planning/REQUIREMENTS.md] | Use a project-owned `httpx` client with Kalshi RSA-PSS request signing, timestamp headers, and explicit base-url configuration. The official docs define access-key auth and show read endpoints for markets, a single market, and market orderbooks. [CITED: https://docs.kalshi.com/getting_started/api_keys] [CITED: https://docs.kalshi.com/getting_started/quick_start_authenticated_requests] [CITED: https://docs.kalshi.com/api-reference/market/get-markets] [CITED: https://docs.kalshi.com/api-reference/market/get-market] [CITED: https://docs.kalshi.com/api-reference/market/get-market-orderbook] |
| KAL-02 | System persists raw Kalshi market, market-detail, and orderbook snapshots with timestamps and request metadata. [CITED: .planning/REQUIREMENTS.md] | Persist snapshot rows with collection time, request parameters, cursor state, response metadata, and payload lineage in repo-local storage. Reuse the project’s filesystem-first + DuckDB pattern instead of inventing a remote store. [CITED: src/tennisprediction/storage/duckdb.py] [CITED: src/tennisprediction/config.py] |
| KAL-03 | System handles Kalshi pagination, retries, rate-limit/backoff behavior, and closed/settled market states. [CITED: .planning/REQUIREMENTS.md] | `Get Markets` supports `limit` plus `cursor` pagination, and the docs list market statuses including `unopened`, `open`, `paused`, `closed`, and `settled`. Kalshi rate limits are token-bucket based, 429s require backoff, and the docs do not present `Retry-After` as the primary control surface. Historical markets are exposed separately for settled-before-cutoff data. [CITED: https://docs.kalshi.com/api-reference/market/get-markets] [CITED: https://docs.kalshi.com/getting_started/rate_limits] [CITED: https://docs.kalshi.com/api-reference/historical/get-historical-markets] |
| KAL-04 | System keeps Kalshi SDK/API payloads behind project-owned interfaces so business logic consumes normalized DTOs. [CITED: .planning/REQUIREMENTS.md] | The official docs say SDKs may lag the API and the OpenAPI/AsyncAPI specs are the source of truth. That favors a project-owned client/DTO boundary with only a thin transport adapter underneath. [CITED: https://docs.kalshi.com/sdks/overview] |
| KAL-05 | System can run a read-only snapshot collection job without placing or preparing orders. [CITED: .planning/REQUIREMENTS.md] | Build the collector as a read-only workflow that only depends on market-list/detail/orderbook reads and hard-fails if any write surface is introduced. The collector should be runnable from the CLI or a job entrypoint, but must never expose execution-prep primitives. [CITED: .planning/ROADMAP.md] [CITED: .planning/REQUIREMENTS.md] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Preserve the ATP-only and Kalshi-only boundaries in every DTO, report, and filename. [CITED: AGENTS.md]
- Keep market monitoring read-only for v1. No order placement interfaces belong in core services. [CITED: AGENTS.md]
- Use repo-local storage paths only. `Settings` already resolves `data_dir`, `models_dir`, `reports_dir`, and `duckdb_path` inside the repository. [CITED: src/tennisprediction/config.py]
- Keep persistence thin and auditable. The existing DuckDB helper shows the repo’s preferred pattern for replacing whole tabular snapshots from typed rows. [CITED: src/tennisprediction/storage/duckdb.py]

## Summary

Phase 05 should be planned as a three-slice Kalshi ingestion bridge. The first slice establishes authenticated read access and normalized DTOs. The second slice persists raw snapshots and request metadata in a queryable local store. The third slice adds pagination, retry, rate-limit behavior, market-state handling, and read-only job guardrails so snapshot collection is deterministic and cannot drift into trading logic. [CITED: .planning/ROADMAP.md] [CITED: .planning/REQUIREMENTS.md]

The main architectural decision is to avoid direct business-logic coupling to any generated Kalshi SDK. Kalshi’s docs explicitly position the REST/OpenAPI surfaces as the authoritative API, while SDKs can lag. That makes a project-owned interface with a minimal transport adapter the safer production boundary. [CITED: https://docs.kalshi.com/sdks/overview] [CITED: https://docs.kalshi.com/openapi.yaml]

Snapshot persistence should stay repo-local and auditable. A DuckDB-backed table layer is the natural fit for request metadata and normalized snapshot indexes, while raw response payloads should remain recoverable from the stored record itself or an adjacent repo-local artifact path. The plan should keep the storage contract explicit so later market-mapping and EV work can query it without re-reading HTTP responses. [CITED: src/tennisprediction/storage/duckdb.py] [CITED: src/tennisprediction/modeling/reports.py]

The orderbook contract is binary-market specific. Kalshi’s orderbook response is yes/no ladder data, so the normalized DTO should represent both sides explicitly and keep the complement relationship visible for later pricing logic. [CITED: https://docs.kalshi.com/api-reference/market/get-market-orderbook]

## Architecture Direction

- Transport layer: authenticated `httpx` client with Kalshi request signing and a small retry wrapper for transient failures.
- DTO layer: project-owned market, market-detail, orderbook, and request-metadata models.
- Persistence layer: repo-local snapshot tables plus request metadata, using the existing DuckDB-centered storage pattern.
- Job layer: read-only snapshot collection entrypoint that runs deterministically over market pagination and writes snapshots without any order-related code path.

## Notable API Facts

- `Get Markets` supports `limit`, `cursor`, and multiple filters, including market status filtering. [CITED: https://docs.kalshi.com/api-reference/market/get-markets]
- Market status includes `unopened`, `open`, `paused`, `closed`, and `settled`. [CITED: https://docs.kalshi.com/api-reference/market/get-markets]
- Kalshi authentication uses signed headers with access key, timestamp, and RSA-PSS signature. [CITED: https://docs.kalshi.com/getting_started/api_keys]
- Rate limiting is token-bucket based and needs explicit backoff handling on 429s. [CITED: https://docs.kalshi.com/getting_started/rate_limits]
- Historical market data is separate from the live market listing surface. [CITED: https://docs.kalshi.com/api-reference/historical/get-historical-markets]

