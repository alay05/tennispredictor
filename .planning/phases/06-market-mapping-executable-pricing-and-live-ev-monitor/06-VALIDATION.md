---
phase: 06
slug: market-mapping-executable-pricing-and-live-ev-monitor
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-20
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.1.0` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `./.venv/bin/python -m pytest -q tests/unit/test_kalshi_storage.py tests/unit/test_backtesting_decisions.py tests/unit/test_cli_smoke.py -x` |
| **Full suite command** | `./.venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_normalization.py tests/unit/test_kalshi_executable_pricing.py -x`
- **After every plan wave:** Run `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_aliases.py tests/unit/test_market_mapping_resolver.py tests/unit/test_live_scan_orchestration.py -x`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | MKT-01 | T-06-01 / — | Name normalization stays deterministic and never auto-accepts ambiguous fuzzy matches. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_normalization.py -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | MKT-02 | T-06-02 / — | Alias overrides remain schema-validated, additive, timestamped, and auditable. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_aliases.py -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | MKT-03 | T-06-03 / T-06-04 | Market resolution emits explicit matched / ambiguous / unmatched / excluded states with evidence. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_resolver.py -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | MKT-04 | T-06-04 / — | Unresolved markets fail closed and cannot reach scoring. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_live_scan_rejections.py -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 3 | MKT-05 | T-06-03 / — | Bid-only Kalshi orderbooks convert into explicit executable-side price sources and liquidity evidence. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_kalshi_executable_pricing.py -x` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 3 | MKT-06 | T-06-02 / T-06-03 | EV records preserve price source, liquidity, freshness, and fee/slippage assumptions. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_live_scan_pricing_contract.py -x` | ❌ W0 | ⬜ pending |
| 06-04-01 | 04 | 4 | MKT-07 | T-06-04 / — | Live/shadow scans reuse trusted artifact and feature interfaces rather than ad hoc prediction code. | integration | `./.venv/bin/python -m pytest -q tests/unit/test_live_scan_orchestration.py -x` | ❌ W0 | ⬜ pending |
| 06-04-02 | 04 | 4 | MKT-08 | T-06-02 / T-06-03 | Ranked monitor output orders accepted opportunities and preserves rejected/excluded audit summaries. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_live_monitor_reports.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_market_mapping_normalization.py` — deterministic normalization coverage for `MKT-01`
- [ ] `tests/unit/test_market_mapping_aliases.py` — auditable alias override coverage for `MKT-02`
- [ ] `tests/unit/test_market_mapping_resolver.py` — mapping-state coverage for `MKT-03`
- [ ] `tests/unit/test_live_scan_rejections.py` — refusal-to-score coverage for `MKT-04`
- [ ] `tests/unit/test_kalshi_executable_pricing.py` — executable price and liquidity coverage for `MKT-05`
- [ ] `tests/unit/test_live_scan_pricing_contract.py` — EV evidence contract coverage for `MKT-06`
- [ ] `tests/unit/test_live_scan_orchestration.py` — trusted artifact reuse and orchestration coverage for `MKT-07`
- [ ] `tests/unit/test_live_monitor_reports.py` — ranked monitor ordering/reporting coverage for `MKT-08`
- [ ] Install the missing ML/runtime packages before replay-backed full-suite verification

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Confirm the chosen alias-override file format is readable and reviewable by operators | MKT-02 | Human judgment on maintainability and audit clarity is still needed even if schema validation passes. | Create two sample overrides, inspect the stored artifact, and verify raw market name, canonical player target, timestamp, and operator note are obvious without reading code. |
| Confirm ranked monitor output is understandable at the CLI | MKT-08 | The ordering and columns can be unit-tested, but operator usefulness still needs a human read. | Run the Phase 06 scan command against fixtures, inspect the accepted table plus rejected summary, and verify the output answers “what is scorable, why, and with what evidence?” |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-20
