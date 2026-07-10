# M0 — Current State Analysis

_Investigation only. No production code was changed, no migrations were run, and no refactoring was performed to produce this document. Every claim below is grounded in the codebase as it exists on `feature/platform-evolution` and cites exact file paths and line numbers. Where the code could not answer a question with certainty, that is stated explicitly rather than inferred._

_This document is the first deliverable of [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) §5, Milestone M0. It does not revisit or question the frozen architecture in [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) and its handbook siblings — it establishes the baseline the migration plan must be executed against._

---

## Executive Summary

The investigation confirms the implementation plan's premise and sharpens it in one important way: **the platform is not merely symbol-keyed — parts of it are already inconsistently symbol-keyed, in a way that produces incorrect accounting today, independent of any migration.**

Three findings dominate everything else in this report:

1. **There is no `Asset`/`Instrument` table or `asset_id` anywhere in the codebase.** Confirmed independently by every investigating thread, by direct grep of all 23 ORM model classes in `backend/models/database.py`. This is greenfield work — M1 is additive, not a refactor of an existing partial registry.

2. **The replay engine already computes a canonical (exchange/DR-resolved) symbol and then does not use it for accounting.** `backend/services/transaction_canonicalizer.py` produces both a `raw_symbol` (stripped/uppercased) and a `canonical_symbol` (DR/exchange-resolved, e.g. `NVDA01` → `NVDA`) per transaction. The replay engine, `backend/services/portfolio_rebuilder.py`, keys its entire in-memory holdings state (`state.holdings: dict[str, _HoldingState]`) by `raw_symbol` only — `canonical_symbol` is never referenced in that file. This means **`"KBANK"` and `"KBANK.BK"` are two distinct positions in replay today**, not one. The platform's own ledger validator (`backend/services/ledger_validator.py:249-301`, check `SYMBOL_ALIAS`) already detects and warns about exactly this condition, but only as a `WARNING`-severity finding with no automated repair.

3. **The codebase already contains a forward reference to this exact problem, attributed to a prior "architecture review" that this investigation could not locate as a written document.** `backend/services/ledger_repair.py:32-35` states verbatim: *"SYMBOL_RENAME, IMPORT_CORRECTION, and LEDGER_EXCEPTION are deferred to Phase 6.8+ pending resolution of the raw_symbol / holdings_json coupling identified in the architecture review."* The same deferral is enforced in `backend/services/repair_plan_executor.py:76-83,212-216` and tested in `backend/tests/test_ledger_repair.py:13` and `test_ledger_repair_executor.py:19-21`. No document titled or describing this "architecture review" was found in `docs/` (see Open Questions). **This is the strongest possible internal evidence that the Asset Registry epic is not a speculative improvement — a previous engineering pass already identified this exact gap and explicitly parked its resolution on future work that this epic now is.**

Beyond these three, the platform is symbol-keyed with high consistency and no surprises: transactions, holdings, watchlist, caches, optimizer, decision memory, analytics, AI agent prompts, and the entire frontend all use a plain `symbol: string` as the sole asset-identity field, with zero indirection. A three-tier symbol-representation pattern (platform-storage form / provider form / display form) already exists informally, reconciled ad hoc by regex and a hand-maintained dictionary (`backend/services/symbol_resolver.py`), duplicated independently on the frontend in 13+ files. This is functionally the evidence tier the Asset Registry formalizes — today it is unpersisted, recomputed on every call, and has no stable identity underneath it.

---

## Current Asset Identity Flow

Traced end-to-end from entry to display, per the investigation of the accounting core:

1. **Entry.** A position enters through exactly one door: one-at-a-time creation via `POST /portfolios/{id}/holdings`, which calls `execute_initial_position()` (`backend/services/portfolio_transactions.py:474-555`). **No CSV or broker-statement bulk-import path exists anywhere in the backend** — a grep for import/CSV/bulk-upload routes returned no matches. The symbol string is normalized only by `_resolve_symbol()` (`backend/main.py:133-137`, trim + uppercase) before being stored verbatim into both `Transaction.symbol` and `PortfolioItem.symbol`.
2. **Storage.** `Transaction.symbol` (`backend/models/database.py:214`) and `PortfolioItem.symbol` (`backend/models/database.py:86`, unique per `(portfolio_id, symbol)`, line 95) are both plain, nullable `String` columns with **no foreign key** to anything.
3. **Canonicalization (per-call, not persisted).** Before replay, `backend/services/transaction_canonicalizer.py:170-206` converts each ORM `Transaction` into a `CanonicalTransaction` value object carrying two parallel fields: `raw_symbol` (stripped/uppercased original) and `canonical_symbol` (resolved through `services/symbol_normalization.py` → `services/symbol_resolver.py`, applying a hardcoded `YFINANCE_SYMBOL_MAP` dict and DR-suffix regexes).
4. **Replay.** `backend/services/portfolio_rebuilder.py` keys all holdings state by `ctx.raw_symbol` (confirmed at every mutation site: BUY line 346-361, SELL 372-379, INITIAL_POSITION 382-401, QUANTITY_CORRECTION 405-418). Per-day valuation looks up price by the same raw key (line 579); the yfinance-resolved form is used only for the outbound provider HTTP call and mapped back onto the raw key immediately after.
5. **Commit.** `_commit_rebuild` writes `PortfolioItem(symbol=sym, ...)` for each raw-symbol dict key (`portfolio_rebuilder.py:1259-1268`) and serializes the same raw-keyed holdings list into `PortfolioSnapshot.holdings_json` (a `Text` JSON blob column, `models/database.py:260` — there is no per-holding row table for snapshots).
6. **API / display.** `GET /portfolios/{id}/holdings` (`backend/main.py:778-820`) and `_snapshot_row()` (`backend/main.py:4084-4115`) return the stored raw-symbol strings essentially verbatim.
7. **Frontend.** Every asset-bearing TypeScript type in `frontend/lib/api.ts` (`PortfolioItem`, `WatchlistItem`, `TransactionRecord`, optimizer/analytics types) keys on `symbol: string`; the display layer independently strips `.BK` in 13+ components for presentation, with no shared utility and no field sourced from the backend for this purpose.

The only place any transformation of the identity value happens between entry and display is step 3's canonicalization — and its output (`canonical_symbol`) is discarded for accounting purposes (step 4) and survives only for provider API calls and for the ledger validator's alias-detection heuristics.

---

## Dependency Inventory

Every subsystem investigated, what it currently reads/writes as asset identity, and its exact coupling points. (Full file:line citations are in the per-cluster findings this report synthesizes; the most load-bearing ones are repeated here.)

| Subsystem | Identity representation today | Key coupling points |
|---|---|---|
| **Data model** (`backend/models/database.py`) | Plain `symbol: String` column, repeated independently on 9 tables (`Transaction`, `PortfolioItem`, `Watchlist`, `AgentCache`, `AnalysisCache`, `AnalysisHistory`, `BenchmarkPrice`, `SignalHistory`, `MarketDataCache`); uniqueness scoped per-container (`portfolio_id`/`workspace_id`), never global | No FK from any table to any identity table; sector/classification duplicated per-row (`PortfolioItem.sector`, `Watchlist.sector`, `Transaction.sector` are three independent string columns) |
| **Migrations** (`backend/migrations/versions/`) | Symbol-as-identity present since the very first migration (`5551f8b86e30_initial_schema.py`) | All 28 revisions are additive on top of the symbol-keyed model; none introduces normalization |
| **Transaction ledger** | `Transaction.symbol`, nullable `String`, indexed, no FK (`database.py:214`) | Every write path constructs `Transaction(symbol=symbol, ...)` directly (`portfolio_transactions.py:138,254,443,525,612`) |
| **Replay/Rebuild Engine** | `raw_symbol` (post strip/upper only) — **not** `canonical_symbol`, despite the latter being computed | `portfolio_rebuilder.py` — see Executive Summary finding 2 |
| **Holdings** | `PortfolioItem.symbol`, plain `String`, unique per `(portfolio_id, symbol)` | Reconciliation via Python `set()`/dict operations on the raw string (`portfolio_rebuilder.py:698-706,1058-1064`) |
| **Snapshots** | No per-asset columns at all — only a `holdings_json` text blob | Per-asset breakdown exists only inside JSON (`portfolio_rebuilder.py:592-603`); `verify_snapshots`' duplicate check (`manage.py:961-967`) does plain string-set membership on the JSON `symbol` field, with **no** alias awareness |
| **CLI: `rebuild_portfolio` / `verify_snapshots`** | Raw string throughout | See above |
| **CLI: `validate_ledger`** | The **one** place that groups by resolved identity | `ledger_validator.py:187-246` (`_check_duplicate_initial_positions`, groups by `(canon, date)`) and `:249-301` (`_check_symbol_aliases`, the `SYMBOL_ALIAS` WARNING) |
| **Repair tooling** | Deferred | `ledger_repair.py:32-35`, `repair_plan_executor.py:76-83,212-216` — `SYMBOL_RENAME` explicitly rejected, citing the unresolved raw_symbol/holdings_json coupling |
| **Market data / providers** | Single provider (Yahoo Finance, via `YahooProvider` or `YahooChartProvider`, selected by `PRICE_PROVIDER` env, `services/market_data/provider.py:1-48`) | All methods keyed by raw `symbol: str` (`services/market_data/base.py:6-57`); no per-provider symbol mapping table |
| **Symbol resolution (ad hoc)** | Three cooperating string-rewrite modules, no persisted mapping | `symbol_resolver.py` (`YFINANCE_SYMBOL_MAP` dict + DR regex), `symbol_normalization.py` (Thai `.BK` inference), `main.py:133-156` (`_resolve_symbol`, `_normalize_transaction_symbol`, cross-checked against a hardcoded `THAI_SECTOR_MAP`, lines 366-420) |
| **Caching** (`MarketDataCache`, `AgentCache`, `AnalysisCache`) | Unique-keyed on `(symbol, cache_type)` / `(symbol, agent)` / `(workspace_id, symbol)` | Exact string equality is the only collision boundary; no cross-check against any other identity attribute |
| **Optimizer** (`services/optimizer/`, `agents/optimizer.py`) | `symbol: str` on every Pydantic model (`FundingCandidate`, `OptimizedTrade`, etc., `execution_optimizer.py:75-93`) | Violation-to-trade matching is **substring search on symbol inside a generated message string** (`execution_optimizer.py:106-125`, `policy_engine.py:344,361,401,425-428`) — a fragile text round-trip, not structured matching |
| **AI Evaluation / grading** | Recommendation-to-transaction matching is exact dict-key string equality on `symbol`, no fuzzy/alias resolution | `services/evaluation/execution_analyzer.py:88-155`, `horizon_grader.py:88-116` |
| **Decision Memory** | `Transaction.symbol` is the sole identity column on decision-adjacent records; shadow portfolio holdings keyed by `symbol` throughout | `services/decision_memory/shadow_tracker.py:404-428,571-902`, `calibration.py:125-165` |
| **Analytics / Factor Engine** | `RawMetrics.symbol` / `NormalizedScores.symbol` (`services/analytics/factor_engine.py:53-98`) | Imports DR-normalization helpers directly from `data_fetcher.py` |
| **AI Agent LLM prompts** | Symbol strings are **prompt content and required output-schema tokens**, not just data | `agents/optimizer.py:868-871,917` — the L1 Strategist prompt embeds symbols and mandates the model echo them back verbatim in JSON |
| **Frontend types** (`frontend/lib/api.ts`) | `symbol: string` on every asset-bearing interface; zero `asset_id` anywhere in the frontend | Confirmed by exhaustive grep, zero matches for `asset_id`/`assetId` |
| **Frontend routing** | `/stock/[symbol]/page.tsx` — symbol is a URL path segment, not just a data field | `frontend/app/stock/[symbol]/page.tsx:275-277` |
| **Frontend React keys** | `key={item.symbol}` in 20+ list renders across watchlist, optimizer, decision-workspace, analytics components | Collision risk if any list ever contains two rows sharing a symbol (e.g. a DR and its underlying) |
| **Frontend display normalization** | `.replace(".BK", "")` reimplemented independently in 13+ files, no shared utility | e.g. `StockCard.tsx:7`, `PortfolioTable.tsx:215,435-436`, `optimizer/page.tsx` (10+ occurrences) |

### Current → Target, per subsystem

```
Data Model         symbol column, no FK           →  asset_id FK + symbol as Registry evidence
Transaction Ledger raw string, no resolution       →  asset_id reference, additive (Principle 1)
Replay Engine      keys by raw_symbol (buggy)      →  keys by asset_id (fixes the alias-splitting
                                                        defect as a byproduct, not a goal)
Holdings/Snapshots symbol string in JSON blob       →  asset_id in JSON blob; symbol resolved for
                                                        display only
Market Data        single provider, raw symbol      →  provider adapter returns candidates;
                                                        Registry resolves; observations joinable
                                                        by asset_id
Symbol Resolution  3 ad hoc regex/dict modules       →  one Resolver (M3), same evidence weighed
                                                         through an adjudication verdict, not a
                                                         guess
Optimizer/AI Eval  symbol as dict key + substring     →  asset_id as dict key; symbol only at
                   matching in generated text          presentation edges; violation matching
                                                        becomes structured (asset_id-keyed), not
                                                        text-search
AI Agent Prompts   symbol is prompt content            →  asset_id internally; display_symbol
                   AND output-schema token              resolved at the prompt boundary only
                                                        (translation shim, not a clean re-key)
Frontend           symbol is type key, route           →  asset_id as the stable key/reference;
                   segment, and React key                symbol/display_symbol resolved at
                                                        render time from one shared utility
```

---

## Coupling Analysis

**Structural coupling is total but shallow.** Every subsystem depends on "symbol" being present and unique-enough within its own scope, but almost none of them depend on the *specific string shape* of a symbol (i.e., they don't parse or validate its format) except the exchange/DR normalization modules, whose entire job **is** parsing that shape. This is a favorable finding: it means most consumers (optimizer, decision memory, analytics, frontend types) can be re-keyed by adding a parallel `asset_id` field without needing to understand identity semantics — the semantic work concentrates in a small number of places.

**The concentration points, in order of how much identity logic they actually contain:**

1. `backend/services/symbol_resolver.py` and `backend/services/symbol_normalization.py` — the de facto (unpersisted) identity-resolution layer. This is the code the Resolver (M3) most directly supersedes; its `YFINANCE_SYMBOL_MAP` dict is exactly the seed data for the Registry's evidence tier for already-known DRs.
2. `backend/services/transaction_canonicalizer.py` — already computes the right *shape* of answer (`raw_symbol` vs `canonical_symbol`) but has no persisted identity to attach it to, and — per Executive Summary finding 2 — its own consumers don't agree on which field to trust.
3. `backend/main.py:133-156,366-458` — inline normalizers and two hardcoded sector-map dictionaries (`THAI_SECTOR_MAP`, `_DR_SECTOR_MAP`) duplicating classification data that the Registry's classification stewardship (ASSET_REGISTRY.md §8) is meant to own centrally.
4. `backend/services/broker_fees.py:112,125-136` — a **third, independent** DR-detection regex, distinct from the two in `symbol_resolver.py` and `symbol_normalization.py`. Three independently-maintained regexes answering the same question ("is this a DR?") is itself a coupling risk: they can drift out of sync with each other, and the Registry's minted lifecycle/relationship model is the single place this question should be answerable going forward.
5. `agents/optimizer.py` — the LLM prompt/output-schema coupling. This is qualitatively different from the others: it's not a data-shape dependency but a *behavioral* one (the model's reasoning quality may depend on seeing real ticker text, not an opaque id). This is flagged as its own risk category below.

**No circular or bidirectional coupling was found** — nothing writes back into the symbol column based on downstream computation (the `canonical_symbol` field is derived and discarded, never persisted back onto `Transaction.symbol`). This means the migration's additive approach (Principle 1 of the implementation plan) has no known obstruction: existing columns can be left untouched while an `asset_id` reference is added alongside.

---

## Migration Risks

Beyond the general risks already catalogued in [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) §9, this investigation surfaces risks specific to what actually exists in the code:

- **Pre-existing alias-splitting defect (highest priority).** The replay engine already treats `"KBANK"` and `"KBANK.BK"` as different positions when both appear in one portfolio's history. This is not a risk the migration *introduces* — it is a risk the migration's backfill (M5) will **encounter and must resolve**, because the M3 resolver will correctly identify such pairs as one asset, and the M5 backfill/replay-parity gate will then face a real question: does "parity with the golden baseline" mean matching the *current* (arguably wrong) split-position output, or the *corrected* single-position output? See Open Questions.
- **Three independently-maintained DR-detection regexes** (`symbol_resolver.py`, `symbol_normalization.py`, `broker_fees.py`) may already disagree on edge cases not yet observed. The M0 investigation could not confirm or rule out live disagreement without querying production data (explicit unknown, below).
- **LLM prompt/output coupling.** `agents/optimizer.py` requires symbols as both prompt input and output-schema tokens. A migration that re-keys this layer to `asset_id` without a translation shim risks silently degrading recommendation quality (tickers carry implicit semantic signal) or breaking the JSON-output parsing contract. This is a distinct risk category not present in the accounting engines and should be scoped explicitly in M6.
- **No bulk-import path exists.** This *reduces* one anticipated risk (broker-statement CSV parsing ambiguity) but means the full historical symbol inventory (M0's own deliverable per the implementation plan) is smaller and more tractable than a platform with bulk imports would have — a favorable finding worth noting for M0's own effort-sizing in the implementation plan.
- **Frontend React-key collision risk is real but currently masked.** Because no list today appears to contain two rows with an identical symbol (that would already be a visible bug — duplicate list entries), this risk is latent rather than active; it becomes active the moment identity resolution makes previously-hidden aliases visible in a shared list.
- **Sector/classification data is triplicated** (`PortfolioItem.sector`, `Watchlist.sector`, `Transaction.sector`, plus two hardcoded dictionaries in `main.py`) with no mechanism keeping them consistent. Migrating classification to the Registry (M1/M2) will need to pick one of these as the seed source and treat the others as evidence to reconcile against — not treat any of them as automatically authoritative.

---

## Subsystem Complexity

Classified by how much identity-specific logic must change, not by raw line count.

| Subsystem | Complexity | Why |
|---|---|---|
| Data model (new Registry tables) | **Low** | Purely additive; no existing table needs structural change, only a new nullable FK column added over time |
| Migrations | **Low** | The platform's migration discipline is already additive-only by convention (confirmed across all 28 revisions) |
| Market data / provider adapter | **Low–Medium** | Single provider today (favorable), but the two-implementation split (`YahooProvider`/`YahooChartProvider`) and the `.BK`-triggered native-crash history (`yahoo_chart.py:6-28`) mean provider-layer changes need care around an already-fragile integration |
| Symbol resolution (`symbol_resolver.py`, `symbol_normalization.py`) | **Medium** | Logic is well-isolated (favorable) but must be *replaced*, not wrapped — the M3 resolver needs to absorb the `YFINANCE_SYMBOL_MAP` seed data and the DR-regex heuristic while adding the ambiguity-surfacing discipline that doesn't exist today (today's code always returns *something*, never "ambiguous") |
| Transaction ledger / write paths | **Medium** | Structurally simple (additive column) but numerous call sites (`portfolio_transactions.py` alone has 5+ construction points) must all be audited for consistent normalization before resolution — the investigation could not confirm 100% of write paths normalize consistently (explicit unknown) |
| Replay/Rebuild Engine | **High** | This is where the pre-existing raw_symbol/canonical_symbol defect lives; cutover here is the plan's own M5 hard-gate, and correctly resolving the alias-splitting question (Open Questions) before/during cutover is now confirmed to be genuinely load-bearing, not hypothetical |
| Holdings & Snapshots | **Medium** | No schema change needed for the JSON blob itself, but the *values inside* the JSON need a coordinated switch, and the CLI tooling (`verify_snapshots`) needs its duplicate-detection check upgraded from string-set to asset_id-aware (or retired once the underlying defect is fixed) |
| CLI tooling (`rebuild_portfolio`, `validate_ledger`, `verify_snapshots`) | **Medium** | `validate_ledger` already has the most identity-sophisticated logic in the codebase (`canon`-keyed grouping) and is the natural home to extend, not replace; `verify_snapshots`' cruder check needs deliberate attention so it doesn't silently stop catching real duplicates once `asset_id` exists alongside symbol |
| Repair tooling (`ledger_repair.py`, `repair_plan_executor.py`) | **Medium** | The deferred `SYMBOL_RENAME` repair type is explicitly waiting on this epic; unblocking it is in scope for corporate-action-adjacent work, not this epic, but the M1 identity model should be built with awareness that this is the next consumer waiting on it |
| Optimizer (`services/optimizer/`) | **Medium** | Symbol-as-dict-key is uniform and mechanical to re-key; the substring-matching of violations against generated text (`execution_optimizer.py:106-125`) is the one piece of genuinely fragile logic that needs a structured (non-text) redesign as part of, not incidental to, the re-key |
| AI Evaluation / Decision Memory | **Low–Medium** | Purely dict-key string equality throughout, no fuzzy matching to preserve or break; mechanical re-key once upstream (transactions, recommendations) carry `asset_id` |
| Analytics / Factor Engine | **Low–Medium** | Same pattern as above; depends on the same DR-normalization helpers already flagged for replacement |
| AI Agent LLM prompts (`agents/optimizer.py`) | **High** | Not a data-shape problem but a behavioral one — requires a translation shim design, prompt-quality validation, and re-verification of the output-parsing contract; the plan's existing M6 scope should call this out as its own workstream rather than treating it as "just another consumer" |
| Frontend types & API client | **Low–Medium** | Mechanical addition of `asset_id` fields; the API-URL-uses-symbol pattern (15 endpoints) needs a compatibility decision (dual-route support during coexistence, per the plan's §6) |
| Frontend routing (`/stock/[symbol]/`) | **Medium** | The one place symbol identity is baked into URL structure, not just data; requires an explicit decision on whether to keep symbol-based routing permanently (as a resolved-at-request-time lookup) or migrate to id-based routing — this is a product decision, not purely technical |
| Frontend display normalization | **Low** | 13+ duplicated implementations of the same trivial transform; consolidating into one shared utility sourced from a backend `display_symbol` field is low-complexity and can happen early, independent of the rest of the migration |

---

## Recommended Implementation Order

The investigation does not surface any reason to deviate from the implementation plan's suggested M0→M7 order. Two refinements are recommended within that order, both scoped as adjustments to milestone content, not to sequence:

1. **M1 should explicitly model the alias/relationship concept early enough that M3's resolver can express "these historical raw symbols are the same asset"** — the plan already calls for relationship links in M1 (ASSET_REGISTRY_IMPLEMENTATION_PLAN.md §5, M1 scope), and this investigation confirms that need is not theoretical: the `SYMBOL_ALIAS` warning in `ledger_validator.py` is already firing (or capable of firing) against real historical data patterns the platform itself creates.
2. **M6's scope for the optimizer/AI-agent layer should be split into two distinct workstreams**: (a) the mechanical re-key of decision memory, analytics, and factor engine (Low–Medium complexity, can proceed on the plan's existing schedule), and (b) the LLM prompt-boundary translation shim for `agents/optimizer.py` (High complexity, behavioral risk, benefits from its own design spike and prompt-quality regression testing before being folded into the milestone's cutover).

No subsystem was found to be a blocking dependency the plan had not already accounted for.

---

## Unknowns

Carried forward directly from the investigating threads, stated explicitly rather than resolved by inference:

- Whether every live transaction-write path (not only `portfolio_transactions.py` and the `main.py` routes inspected) normalizes `symbol` consistently before insert — onboarding/administrative paths were not exhaustively traced.
- Whether the three independently-maintained DR-detection regexes (`symbol_resolver.py`, `symbol_normalization.py`, `broker_fees.py`) currently agree on all real symbols in production data, or whether any live disagreement already exists — this requires querying a live database, out of scope for a code-only investigation.
- Whether any production portfolio currently holds a real (not synthetic) instance of the raw_symbol/canonical_symbol alias-splitting defect (e.g., an actual portfolio with both `"KBANK"` and `"KBANK.BK"` rows) — the `SYMBOL_ALIAS` check exists specifically because this is *possible*, but its current firing rate against real data is unknown without a live audit.
- Full behavior of `backend/services/snapshot_repair.py` and `snapshot_return_recovery.py` with respect to the raw_symbol/canonical_symbol split — confirmed to operate on stored `holdings_json` (raw-keyed) directly, but the full consequence chain was not traced to the same depth as `portfolio_rebuilder.py`.
- Coverage completeness of `YFINANCE_SYMBOL_MAP` (`symbol_resolver.py:34-48`) against the full universe of DRs and non-US-listed instruments the platform may already hold — the code's own comments instruct future maintainers to add entries manually, meaning gaps fail silently (fallback to generic suffix-stripping) rather than erroring.
- Whether `agents/fundamental.py`, `technical.py`, `news.py`, `chart_data.py`, `summary.py` embed symbol strings into their own LLM prompts the way `agents/optimizer.py` confirmed does — only `optimizer.py` was read in full; the others were sampled, not exhaustively reviewed.
- Full content of `docs/PORTFOLIO_CALCULATION_RULES.md` and `docs/investment/OPTIMIZER_PHILOSOPHY.md` was not re-read as part of this code-focused investigation; if either contains an existing written policy on corporate-action/rename handling beyond what code comments describe, it was not incorporated here.
- The percentile-aggregation and portfolio-level rollup logic in `factor_engine.py` past its first ~150 lines was not inspected in detail.
- `services/analytics/quant_engine.py`, `regime_attribution.py`, `system_health.py`, and several `services/evaluation/*.py` modules (`plan_grader.py`, `opportunity_cost.py`, `scorecard.py`, `trust_report.py`, `verdict_composer.py`, `expired_writer.py`) were not read line-by-line; based on naming and their callers they likely follow the symbol-string convention documented above, but this is inferred from context, not directly confirmed.

---

## Open Questions

These require a decision from the product owner / architecture editor before M1 begins, because they are judgment calls the code cannot answer and the frozen architecture does not resolve (the handbook correctly leaves "what to do about a pre-existing data-quality condition" as an implementation-level question):

1. **What is "the architecture review" cited in `ledger_repair.py:32-35` and `repair_plan_executor.py:26-28`?** This investigation searched `docs/engineering/DECISION_LOG.md` and the broader `docs/` tree and found no document by that description. If it exists somewhere not searched, it should be read before M1, since it may already contain a considered position on the raw_symbol/holdings_json coupling that this epic would otherwise be re-deriving from scratch. If it does not exist as a written document, that itself is worth recording — the reference may be to an informal or verbal review, in which case this M0 document is now the first written record of the issue.
2. **Resolved — see [ADR-005 — Replay Correctness Baseline](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md).** The question of whether the replay-parity gate (M5) requires matching today's (alias-split) output or the corrected (merged) output is settled: replay parity is measured against correct accounting, not against the current implementation's defects. The alias-splitting defect (and any other correctness defect found before baseline capture) must be repaired before M0's golden baselines are generated, so that "baseline" and "correct" are the same thing by construction. See the ADR for full context, rationale, and consequences.
3. **Does unblocking `SYMBOL_RENAME` as a supported repair type belong inside this epic, or strictly after it (as the code's own "Phase 6.8" framing implies)?** The implementation plan's §12 (Out of Scope) already excludes Corporate Action Domain implementation; `SYMBOL_RENAME` sits right at that boundary — it is a repair-tooling capability, not a corporate-action-processing pipeline, and the Registry's identity model is its direct prerequisite. Recommend treating this as an explicit go/no-go decision at M7 (once the identity layer is stable) rather than silently deferring it further or silently pulling it in.
4. **Should the frontend's symbol-based routing (`/stock/[symbol]/`) be preserved permanently (resolved to an asset at request time) or migrated to id-based routing over the epic's timeline?** This is a product/UX decision — the existing pattern is compatible with the Registry either way (a route resolver step can sit in front of either), but the two choices have different long-term implications for shareable URLs and are worth deciding deliberately rather than by default.

---

## Readiness Verdict

**The project is ready to begin M1 — Canonical Asset Model — with one remaining precondition:** Open Question 1 (locating or confirming the absence of "the architecture review") should be answered before M0's golden baselines are captured. Open Question 2 (the replay-parity-vs-correctness decision) is now resolved by [ADR-005](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md) — golden baselines are captured only after known correctness defects are repaired, per that decision. Everything else — the identity model itself, the evidence-tier design, the lifecycle, the classification stewardship — has no blocking unknown and can proceed on the implementation plan's existing schedule.

This is not a request to redesign the architecture, and it is not a discovery that the plan is wrong. It is exactly the kind of finding M0 exists to surface: a place where "adapt the implementation, not the architecture" requires a deliberate, recorded decision rather than a silent default. The recommendation is to make that decision explicitly — in writing, as this document now does by raising it — and then proceed.

---

## Related Documents

- [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) — the milestone plan this investigation feeds into; M0's deliverables (census, inventory, golden baselines) are partially satisfied by this document and remain to be finalized per its Definition of Done
- [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) — the frozen architecture; nothing in this investigation questions its boundaries or conclusions
- [Architecture Handbook README](../architecture/README.md) — reading order and document-type legend
- [ADR-005 — Replay Correctness Baseline](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md) — resolves Open Question 2 above