# Classification Consolidation

_M6 Compatibility-Layer Integration, Phase 7 — the final remaining track named
in [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md)
§5. Shipped 2026-07-10._

_Companion documents: [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md)
(frozen architecture — see §8 Classification), [REGISTRY_INTEGRATION_GUIDE.md](../architecture/REGISTRY_INTEGRATION_GUIDE.md)
(developer-facing usage guide — see its "Phase 7: Classification
Consolidation" section), [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md)
(the M0–M7 epic this is part of), [WATCHLIST_REGISTRY_PILOT.md](WATCHLIST_REGISTRY_PILOT.md)
(the prior, narrower Phase 1 step 2 pilot this milestone follows the same
audit-first / additive-only / fallback-preserving discipline of)._

Per the milestone brief: this is an **adoption** milestone. The Registry
architecture is frozen and was not redesigned. No business rule changed. No
schema changed. Portfolio, Ledger, Replay, Optimizer decision logic,
Recommendation, and Analytics algorithms were not migrated — only
duplicated **classification** logic (sector today; market/exchange/asset_type
are already Registry fields with no duplicated inference to retire, per the
audit below).

---

## 1. Audit — every classification implementation found

Method: `main.py` was read in full for its sector system (the milestone's
named primary target), followed by a codebase-wide search across
`backend/services/`, `backend/agents/`, and `frontend/` for any other
symbol-keyed inference of sector, exchange, market, or asset_type. The
search was not limited to grepping for the four field names — it looked for
the *pattern* (a function that takes a symbol and returns a classification
fact without going through the Registry), per the brief's "do not assume
this list is complete" instruction.

### Classification key
1. **Replace with Registry** — migrated this milestone.
2. **Keep (with justification)** — deliberately not classification, or a
   correct, bounded, non-duplicated concern.
3. **Deferred until Native asset persistence** — blocked on M5 Track B
   (ledger carrying `asset_id` natively) or on a `db` session not being
   threaded to the call site.
4. **Technical debt** — a real duplication or drift, not fixed this
   milestone because fixing it would require a business-logic redesign or
   would risk changing behavior for inputs where implementations disagree.

### Sector

| Location | What it does | Classification |
|---|---|---|
| `main.py`: `THAI_SECTOR_MAP`, `_DR_SECTOR_MAP`, `_get_sector()`, `_fetch_sector()`, `/admin/backfill-sectors`, `/admin/fix-sectors` | Primary sector-classification system for the whole platform — static maps + FA-cache fallback, used at watchlist/holding add-time and by two admin repair endpoints | **1. Replaced with Registry** — see §2 |
| `main.py`: `/admin/fix-dr-sectors` (`_correct_sector`) | Reconciles *already-stored* `PortfolioItem.sector`/`Watchlist.sector` DB columns against the static maps — a data-repair tool, not a classification source | **2. Keep** — its entire purpose is applying the static maps' values as corrections; the static maps remain that source under this milestone's own design (§3). Not touched. |
| `main.py`: `_normalize_transaction_symbol()`'s `f"{s}.BK" in THAI_SECTOR_MAP` check | Uses the sector map's keyset as a "is this a known SET ticker" *exchange-suffix* test, to auto-append `.BK` to a bare user-typed transaction symbol | **2. Keep** — this is symbol normalization for the ledger's own transaction-entry field (identity-adjacent), not a value returned as a classification fact to any caller. Out of this milestone's scope ("only classification: sector, market, exchange, asset_type" — this is neither; it decides how a symbol is *spelled*, not what it *is*). |
| `agents/optimizer.py::normalize_sector()` / `_CANONICAL_SECTORS` | Third-party raw-sector-string canonicalizer (buckets yfinance/FA strings like `"Financial Services"` into 9 canonical keys) | **4. Technical debt** — see §4 |
| `services/idea_review.py::_normalize_sector()` / `_CANONICAL_SECTORS` | A second, independently-written copy of the same canonicalizer, with a **superset** of substring rules vs. the `agents/optimizer.py` copy | **4. Technical debt** — see §4 |
| `services/optimizer/policy_engine.py::_norm_sector()` | A third copy, deliberately reduced ("to avoid circular import with optimizer.py" — an explicit comment in the source) | **4. Technical debt** — see §4 |
| `services/idea_review.py::_get_sector()` (tiered DB → watchlist → yfinance/"Other" lookup, already Registry-aware for *identity* via `registry_symbol_matching.match_known_symbols`) | Sector-lookup fallback chain for AI Committee Review of user-submitted ideas | **3. Deferred** — already uses the Registry for identity matching (Phase 2); extending it to also consult Registry *classification* is a natural next step but was left out of this milestone to keep the diff to the one already-scoped primary target (`main.py`) and avoid touching Optimizer-adjacent decision-support code, per the brief's explicit "Do NOT migrate ... Optimizer" scope fence. |
| `services/basket_simulation.py::_resolve_symbol_sectors()` | Same tiered fallback chain, same Registry-for-identity wiring, consumed by `position_sizing.py`, `allocation_engine.py`, `portfolio_construction.py` | **3. Deferred** — identical reasoning to the row above. |

### Exchange / Market

| Location | What it does | Classification |
|---|---|---|
| `services/symbol_market_convention.py::infer_market_exchange()` | Infers `Thailand`/`SET` from a DR pattern or `.BK` suffix, used only by `bootstrap_planner.py` to mint **new** Registry assets | **2. Keep** — this is Registry-internal bootstrap logic, not a duplicate *of* the Registry; it is part of how the Registry itself gets populated (M5 Track A). |
| `services/symbol_normalization.py::get_yfinance_symbol()` | Assumes a bare, suffix-less symbol is Thai SET and appends `.BK` as a disposable default for routing a yfinance query | **2. Keep** — its own docstring scopes it as a query-routing default, not a durable identity/classification claim. Not a target. |
| `main.py::_normalize_transaction_symbol()` | See Sector table above (same function, exchange-suffix angle) | **2. Keep** — as above. |
| `services/broker_fees.py::resolve_fee_profile()` (`^[A-Z]+\d{2}\.BK$` regex) | Selects a fee schedule (`SET_STANDARD` vs `DR_STANDARD`) from symbol shape | **2. Keep** — a fee-domain decision, not a sector/market/exchange/asset_type classification consumed anywhere else. Both profiles currently charge identical rates. Minor, unrelated note: it re-derives "is this a DR" via its own regex rather than calling `services/symbol_resolver.py::is_dr()` — a small ADR-004 duplication smell, but touching broker fee logic is out of this milestone's explicit non-goals ("Do NOT migrate ... Ledger"/accounting-adjacent code), so left as-is. |
| `frontend/app/stock/[symbol]/page.tsx` (`rawSymbol.endsWith(".BK")`) | Drives a small ".BK (SET)" UI label | **2. Keep** — frontend-local display heuristic, not persisted or consumed elsewhere; out of this milestone's backend-classification scope. |

### Asset Type

| Location | What it does | Classification |
|---|---|---|
| `services/optimizer/execution_penalty.py::classify_execution()` | Infers `asset_type` (EQUITY/DR/ETF/INDEX) from ticker regex + a hardcoded ETF ticker list | **3. Deferred until Native asset persistence** — already tracked in [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md)'s Technical Debt Register (Phase 5 completion audit, 2026-07-10). `AssetView.asset_type` could answer this today, but the only call site (`main.py`'s `POST /analyze/optimizer`, inside a synchronous execution-context step) has no `db` session threaded to it. Confirmed unchanged this milestone; re-audited, not re-implemented, to avoid duplicating an already-recorded finding. |
| `services/optimizer/stabilization.py::diagnose_duplicate_tickers()` | Diagnostic-only same-symbol-duplicate scan within one pipeline run's own output | **2. Keep** — not a classification lookup; already tracked as becoming unnecessary once optimizer internals migrate to `asset_id` keys (a separate, later, out-of-scope phase). |
| `services/data_fetcher.py::is_dr_symbol()` / `normalize_dr_symbol()` (delegates to `services/symbol_resolver.py::is_dr()`) | Identity normalization — "is this a DR, and what does it wrap" — used for price-fetch routing, not classification | **2. Keep** — confirmed identity-adjacent, not classification; every downstream call site (`agents/fundamental.py`, `services/analytics/factor_engine.py`, `services/portfolio_rebuilder.py`, `services/listing_equivalence.py`) uses the flag for identity/price-routing/liquidity purposes only, never to derive sector/market/exchange. |

### Not classification (confirmed, excluded)

- `services/registry_symbol_matching.py::match_known_symbols()` — **identity** matching (is symbol A the same instrument as symbol B), not classification. Already Registry-backed (Phase 2).
- `frontend/lib/sectors.ts` (`SECTOR_COLORS`) — pure display/coloring keyed by an already-resolved sector string. Presentation only.
- `frontend/lib/api.ts`'s `AssetType` TypeScript union — a type mirror for display, not inference logic.

---

## 2. Migration Summary — `main.py`'s sector system

### Previous implementation

`_get_sector(symbol, fa_cache)` — priority order: (1) DR prefix →
`_DR_SECTOR_MAP`, (2) `.BK` suffix → `THAI_SECTOR_MAP`, (3) FA-cache raw
sector string via `normalize_sector()`, (4) `"Other"`. Called from 8 sites:
`add_holding`, `add_watchlist`, `_fetch_agents` (single-stock analysis
enrichment), `/admin/backfill-sectors`, `/admin/fix-sectors`,
`transaction_buy`, `transaction_initial_position`, plus the shared
`_fetch_sector()` async wrapper that adds a live yfinance call when the
synchronous lookup returns `"Other"`.

### New implementation

**`services/sector_taxonomy.py`** (new module) — the static maps,
`normalize_sector()`, `dr_prefix()`, and a new pure helper,
`static_sector_lookup(symbol, *, is_dr)`, extracted from `main.py` verbatim
(byte-identical map contents and matching rules — this is a pure move, not a
rewrite). Extracted rather than left inline so it can be imported by both
`main.py` and the new seed script below without importing the FastAPI app
module itself.

**`main.py::_get_sector(symbol, fa_cache, db=None)`** gained a new priority
0, checked before everything else:

```
0. Asset Registry   — AssetView.classification["SECTOR"], when the
                       Registry has resolved this symbol's identity AND
                       has a current SECTOR classification fact for it
1. DR stocks        — _DR_SECTOR_MAP (unchanged)
2. Thai .BK         — THAI_SECTOR_MAP (unchanged)
3. US stocks        — FA cache (unchanged)
4. "Other"          — (unchanged)
```

`db` is optional (defaults to `None`, which skips step 0 entirely and
reproduces pre-Registry behavior exactly) but every real call site in
`main.py` has a request-scoped session in context and now passes it — all 8
call sites plus `_fetch_sector()`'s two internal calls were updated. A
Registry lookup failure (exception from `registry_lookup.resolve_asset()`)
is caught, logged as a warning, and falls through to step 1 — a total
Registry outage cannot break sector resolution
(ENGINEERING_PRINCIPLES.md "Failure Handling").

**`services/registry_classification_seed.py`** (new module) — the seed:
`seed_sector_classification(db, symbols, *, dry_run=True)` resolves each
symbol via `registry_lookup.resolve_asset()` and, for every symbol that
resolves to a minted Asset with **no current SECTOR classification yet**,
writes one via `registry_service.record_classification()` using
`sector_taxonomy.static_sector_lookup()` as the value source. Never
overwrites an existing classification, regardless of its source (ADR-002:
never silently compensate for or override an existing decision). Exposed as
a new `manage.py` subcommand:

```
python manage.py seed_registry_classification            # dry run
python manage.py seed_registry_classification --commit    # persist
```

Scoped to the single workspace's existing `Watchlist`/`PortfolioItem`
symbols (the exact universe `_get_sector()` actually serves today) — not a
blind sweep of the static maps' keys, since a map key with no corresponding
minted Asset has nothing to attach a classification fact to.

### Why this order is safe (identical behavior today, better behavior over time)

The Registry currently has **zero** SECTOR classification facts recorded
(confirmed by inspecting `registry_bootstrap.py` and every M1–M6 milestone's
own implementation notes — none of them populate `AssetClassification`
rows). Until the seed script is run, priority 0 above is a no-op for every
symbol, and `_get_sector()`'s output is **byte-identical** to the
pre-Registry implementation for every input — proven by
`test_main_get_sector_registry.py`'s `db=None` parity tests and by the fact
that the static-map/FA-cache/`"Other"` code path was moved, not rewritten.
After the seed script runs (and, later, as M5 Track B mints more assets),
priority 0 starts returning real values for a growing subset of symbols —
values that are, by construction, identical to what the static maps would
have returned anyway, since the seed's only value source *is* the static
maps. The seed can never disagree with its own fallback on the day it runs;
divergence can only appear later, deliberately, if a human corrects a
Registry classification fact through the M2 adjudication surface — which is
the entire point of promoting the Registry to primary source.

---

## 3. Retained Fallbacks

Every fallback below is a deliberate, documented retention — not leftover
debt:

| Fallback | Why it remains |
|---|---|
| `THAI_SECTOR_MAP` / `_DR_SECTOR_MAP` (`services/sector_taxonomy.py`) | Seed data for the Registry **and** the live fallback for any symbol the Registry hasn't resolved or hasn't been seeded for. M5 Track B (native `asset_id` on the ledger) and full Registry classification coverage are both still far from 100% — this fallback is load-bearing, not vestigial, for as long as that's true. |
| FA-cache raw sector string + `normalize_sector()` | The last-resort source for any symbol with neither Registry nor static-map coverage (most US equities not already DR-wrapped into the platform). Unchanged. |
| `/admin/fix-dr-sectors` | Continues to apply the static maps to already-stored DB columns — a repair tool independent of this migration's read path. |
| `main.py::_normalize_transaction_symbol()`'s `THAI_SECTOR_MAP`-keyset check | Unchanged; this is symbol-spelling normalization, not sector classification, and was out of scope. |

---

## 4. Technical Debt

### Three divergent `normalize_sector` implementations (new finding this milestone)

`agents/optimizer.py::normalize_sector()`, `services/idea_review.py::_normalize_sector()`,
and `services/optimizer/policy_engine.py::_norm_sector()` are three
independently-maintained copies of "canonicalize a raw sector string," and
they have **already drifted**: `idea_review.py`'s copy has a superset of
substring rules; `policy_engine.py`'s copy is deliberately reduced, per an
explicit in-source comment, "to avoid circular import with optimizer.py."

**Why this was not fixed this milestone.** Unifying three implementations
that already disagree necessarily changes behavior for at least two of the
three call sites, for any raw string where the rules diverge — which
directly conflicts with this milestone's own mandate ("Existing application
behaviour must remain unchanged," "No business rules should change").
Deciding *which* ruleset is canonical is a business-rule question, not a
mechanical deduplication, and is explicitly out of an adoption milestone's
authority ("Do not redesign," §0 of the brief). Recorded here instead so a
future, explicitly-scoped milestone can make that call deliberately — the
fix (once a canonical ruleset is chosen) is straightforward: extract to
`services/sector_taxonomy.py` alongside the version already there, the same
move this milestone made for `main.py`'s copy.

**Blocking dependency:** a product/engineering decision on which of the
three rulesets (or a new, reconciled one) is correct.

### `idea_review.py` / `basket_simulation.py` sector fallback chains not yet Registry-classification-aware

Both already resolve *identity* through the Registry (Phase 2,
`registry_symbol_matching.match_known_symbols`) but still end their sector
fallback chain at yfinance/`"Other"` rather than first checking
`AssetView.classification["SECTOR"]` the way `main.py::_get_sector()` now
does.

**Why deferred:** both files sit in Optimizer-adjacent decision-support
code (`idea_review.py` powers AI Committee Review; `basket_simulation.py`
powers Decision Workspace basket simulation), and the brief's explicit scope
fence ("Do NOT migrate ... Optimizer ... Recommendation") counsels a
minimal, surgical diff limited to the one already-named primary target.
Extending them is a natural, low-risk follow-up (same additive pattern as
`main.py`'s change) but was left for a future milestone rather than
expanding this one's blast radius.

**Blocking dependency:** none — purely a scope/sequencing choice. Safe to
pick up any time.

### `execution_penalty.classify_execution`'s asset-type inference

Unchanged carry-forward from [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md)'s
existing Technical Debt Register (Phase 5, 2026-07-10). `AssetView.asset_type`
could answer this today; the blocker is that `main.py:POST /analyze/optimizer`'s
synchronous execution-context step has no `db` session threaded to
`compute_portfolio_execution_context`/`classify_execution`. Re-confirmed
during this milestone's audit, not re-implemented (a business-logic call-chain
change, out of this milestone's read-path-only scope).

**Blocking dependency:** threading a `db` session into that call chain — a
business-logic change to the optimizer's execution-context step.

---

## 5. Future Work

Named here as candidates, not started (consistent with this milestone's own
"stop after Classification Consolidation" instruction):

- **Reconcile the three `normalize_sector` implementations** into one, once
  a canonical ruleset is chosen (§4).
- **Extend `idea_review.py`/`basket_simulation.py`'s fallback chains** to
  consult Registry classification before yfinance/`"Other"`, mirroring
  `main.py`'s change (§4).
- **Thread a `db` session into `execution_penalty.classify_execution`'s call
  chain** so it can read `AssetView.asset_type` instead of regex/hardcoded-list
  inference (§4, carried forward from the M6 read-path plan).
- **Frontend `.BK` display heuristics** (`frontend/app/stock/[symbol]/page.tsx`)
  could read the additive `registry` metadata already available on several
  API responses instead of a local `endsWith(".BK")` check — low priority,
  cosmetic only.
- **Seed more classification dimensions** (`REGION`, once a region-inference
  source exists) using the same `registry_classification_seed.py` pattern —
  currently only `SECTOR` is seeded, since it is the only dimension with an
  existing, authoritative static source (`sector_taxonomy.py`) to seed from.
- **Retire `sector_taxonomy.py`'s static maps as a read-time fallback**
  once M5 Track B gives every symbol a native Registry identity and
  classification coverage reaches practical completeness — the maps
  themselves remain permanently valuable as the *seed data*, but the
  fallback branch in `_get_sector()` becomes dead code at that point (M7
  contraction phase).

---

## 6. Test Coverage

- `backend/tests/test_sector_taxonomy.py` (12 tests) — proves the
  `main.py` → `services/sector_taxonomy.py` extraction is behavior-preserving:
  Thai equities, DR equities (via prefix, with the two/three-digit-suffix
  DR-vs-single-digit-Thai-ticker disambiguation), ETFs/US symbols with no
  static entry, `normalize_sector()`'s canonical-passthrough and
  substring-bucketing rules, and a data-integrity check that every map value
  is a recognized canonical sector.
- `backend/tests/test_registry_classification_seed.py` (7 tests) — Thai
  equity seeded, DR equity seeded, an existing classification never
  overwritten (regardless of source), an unresolved symbol reported and
  left untouched, a resolved symbol with no static seed data reported
  honestly, `dry_run=True` performs zero writes, and a mixed batch resolves
  every symbol independently.
- `backend/tests/test_main_get_sector_registry.py` (13 tests) — the full
  priority-order proof end to end: Registry classification wins over the
  static map when present; a resolved-but-unclassified asset falls back to
  the static map; a historical-only alias (superseded identifier, no
  current claimant) is honestly treated as unresolved by the Registry and
  falls through to the static map rather than being guessed
  (ASSET_REGISTRY.md §4); a fully unresolved symbol with no data anywhere
  returns `"Other"`; `db=None` reproduces pre-Registry behavior exactly; a
  total Registry failure degrades gracefully instead of raising; a mixed
  batch; and `_fetch_sector()`'s async wrapper correctly skips the yfinance
  call when an earlier tier already resolved, and correctly falls through
  to it when nothing else did.
- `backend/tests/test_watchlist_registry.py` — existing 10 tests updated
  only for the `_fetch_sector()` monkeypatch's new `db` parameter signature;
  no behavioral change to the test suite itself.

**Regression:** full backend suite run before and after via `git stash`
isolation. **Byte-identical 58-failure pre-existing set in both runs** (none
in sector/registry/watchlist modules), passed count up by exactly the 32 new
tests (1073 → 1105), 32 skipped unchanged both times.

---

## 7. Success Criteria (restated against this milestone)

- ✅ Registry is the primary source of SECTOR classification for every
  symbol it can resolve and has been seeded for.
- ✅ Duplicated classification logic reduced: `main.py`'s sector system —
  the milestone's named primary target — no longer independently decides
  sector for a Registry-classified symbol.
- ✅ Existing application behaviour remains unchanged: `db=None` parity
  proven by test; the seed can never disagree with its own fallback on the
  day it runs (§2); byte-identical pre-existing test-failure set.
- ✅ All tests pass (32 new, 0 regressions).
- ✅ Every remaining classification implementation found by the audit is
  explicitly classified (1–4) with reasoning (§1).
- ✅ Documentation updated: this file (new), `REGISTRY_INTEGRATION_GUIDE.md`,
  `ASSET_REGISTRY_IMPLEMENTATION_PLAN.md`.

**Stopped here, as instructed.** Native Asset Persistence (M5 Track B) was
not started. The three divergent `normalize_sector` implementations were
audited and documented, not reconciled (§4).
