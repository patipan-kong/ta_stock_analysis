# Portfolio Runtime Adoption — Audit (M29)

**Status:** Audit only. No production code was changed to produce this document.
**Scope:** Full repository sweep (282 backend `.py` files, 144 frontend `.ts`/`.tsx` files) for runtime behavior driven directly by `AssetType` or asset-identity proxies, versus behavior that should be driven by the Asset Definition Runtime's `CapabilityView`.

---

## 0. Correction to the milestone brief's premise

The brief for this audit states that the Asset Definition Program (M10–M28) is "complete," including "Registry integration" and "Enforcement infrastructure," and that six canonical Asset Definitions exist. **The repository does not support that framing, and this audit is grounded in the repository, not the brief.** Verified directly against source and `docs/engineering/DECISION_LOG.md`:

- **Two** canonical Asset Definitions exist: `CASH` v1 and `EQUITY` v1 (`docs/definitions/asset_definition_library.md`). The other seven `AssetType` members (`ETF`, `FUND`, `BOND`, `CRYPTO`, `COMMODITY`, `PROPERTY`, `OTHER`) have no transcription in `library.py`.
- The runtime has reached **Stage R1.5** (branch `feature/m13-runtime-adoption-stage-R1.5`, milestones M10–M13 in DECISION_LOG.md): a `CapabilityView`/`GovernanceProjection` exist, and two consumers (`ledger_validator.py`, `asset_registry.mint()`) run **read-only shadow consultations** that log disagreements but never raise, block, or change behavior. `enforcement_decisions.py`'s own docstring: *"This module makes no decision by itself and enforces nothing."* No "enforcement infrastructure" is live.
- No frontend code references `AssetType`, `CapabilityView`, or any capability endpoint. There is no serialized capability surface today.

This matters for the audit's conclusions: the platform is earlier in the adoption curve than the brief assumes, several of the "future" migration questions (which `AssetType` members need new vocabulary before they can even be defined) are **already answered** by M13's `enforcement_decisions.py`, and this document builds on that existing decision record rather than re-deriving it.

---

## 1. Executive Summary

The fear this audit was designed to test for — "AssetType branching sprawled across the codebase, silently deciding behavior everywhere" — **is not what was found.** Direct branching on `AssetType`/`asset_type` is narrow and concentrated almost entirely in the Registry/identity layer, where it belongs (Category A). Explored across ~130 backend files read in depth plus the full frontend tree, only a handful of files contain genuine behavior-deciding branches on asset identity.

The real findings are different in kind from what the brief anticipated, and more important for planning purposes:

1. **A shadow, parallel asset-classification system exists outside `AssetType` entirely.** `backend/services/optimizer/execution_penalty.py` classifies every symbol into `EQUITY | DR | ETF | INDEX` using regexes and a hardcoded ETF ticker list, and drives real behavior with it — liquidity/spread baselines, hard position caps, slippage penalties. The frontend has an unrelated, same-named `AssetType` type (`frontend/lib/api.ts:587`, `EQUITY | DR | ETF | INDEX`) that is this same taxonomy leaking into the API contract, not the canonical `asset_domain.AssetType`. Neither this taxonomy nor `broker_fees.py`'s separate `.BK`-regex fee-profile selection is expressed through the Asset Definition Runtime.
2. **The highest-risk items are not branches at all — they are absent gates.** Six independent modules (`ledger_validator.py`, `portfolio_transactions.py`, `portfolio_metrics.py`, `portfolio_snapshots.py`, `snapshot_repair.py`, `portfolio_rebuilder.py`, plus `agents/optimizer.py`'s weight computation) universally assume `value = shares × price` and universally accept `DIVIDEND` transactions for any symbol, with no check of whether the asset in question actually has quantity-based valuation or grants a dividend flow. This works today only because every position the platform has ever held is equity-shaped. It is silent, un-alarming, and exactly the class of risk `CapabilityView.unit_quantity_equals_value()` / `grants_flow(FlowType.DIVIDEND)` exists to make explicit.
3. **The AI/analytics/optimizer stack (agents, factor engine, timing intelligence) has effectively zero `AssetType` adoption in either direction** — it neither branches on asset kind nor consults the runtime. Every technical/fundamental/dividend/factor engine runs unconditionally against every symbol. This is a bigger latent risk than any explicit branch: nothing would stop a `BOND` or `CRYPTO` position from silently receiving a meaningless P/E-based fundamental score.
4. **`bootstrap_planner.py` hardcodes every ledger-only historical mint as `AssetType.EQUITY`**, because ledger evidence carries no asset-kind signal. This is a real mislabeling risk the moment any future Stage R2 gate checks `asset_type` against the registry.
5. Of the 9 `AssetType` members, the runtime's own M13 enforcement-decision table (`enforcement_decisions.py`) already correctly identifies that 6 of the 7 undefined kinds (`FUND`, `BOND`, `CRYPTO`, `COMMODITY`, `PROPERTY`, and to a lesser extent `ETF`) cannot be authored today without first extending the closed vocabulary (`ValuationQuestion`, `EventFamily`, `SettlementPattern`) — this is not new information this audit needed to produce, and the migration plan below defers to it rather than re-litigating it.

**Bottom line:** this is not a "flatten 200 switch statements" migration. It is (a) reconciling one rogue classification system into the canonical vocabulary, (b) adding explicit capability gates to a small number of high-leverage shared functions before they silently mis-handle a non-equity asset, and (c) deciding, for each of 5-8 concrete spots, whether AI/analytics behavior should become kind-aware at all before the platform ever onboards a non-equity, non-cash holding.

---

## 2. Repository Audit Statistics

| Metric | Count |
|---|---|
| Backend `.py` files in repo (excl. venvs/caches/backups) | 282 |
| Frontend `.ts`/`.tsx` files in repo (excl. `node_modules`) | 144 |
| Backend files read in depth for this audit | ~95 |
| Frontend files swept for this audit | full tree (144), 5 read in depth |
| `AssetType` canonical members | 9 (`EQUITY, ETF, FUND, BOND, CRYPTO, COMMODITY, CASH, PROPERTY, OTHER`) |
| Canonical Asset Definitions authored | 2 (`CASH` v1, `EQUITY` v1) |
| Files with literal `AssetType`/`asset_type` references (backend, incl. tests) | 32 |
| Files with literal `AssetType`/`asset_type` references (frontend) | 1 (`lib/api.ts` — unrelated taxonomy, see §1) |
| Files with production (non-test) `AssetType` usage | 9 (`asset_registry.py`, `library.py`, `enforcement_decisions.py`, `coverage_report.py`, `ledger_validator.py`, `binding_resolver.py`, `registry_lookup.py`, `bootstrap_planner.py`, `agents/optimizer.py`) |
| Catalogued branching/behavior findings (this audit) | 79 |
| — Category A (Identity — Keep) | 23 |
| — Category B (Runtime Behavior — Candidate), explicit branches | 14 |
| — Category B (Runtime Behavior — Candidate), implicit/systemic absence-of-gate | 12 |
| — Category C (Legacy/Transitional) | 12 |
| — Category D (Presentation) | 18 |
| Domains with **zero** `AssetType` adoption (neither branches nor runtime consultation) | AI agents (`agents/*.py`), analytics (`factor_engine.py`, `regime_detector.py`), decision-memory, timing-intelligence, optimizer policy/strategy, market-data providers, `main.py`, migrations (all but the founding DDL) |

---

## 3. Findings by Domain

### 3.1 Identity / Registry Domain

*Files: `asset_domain.py`, `asset_registry.py`, `asset_repository.py`, `registry_lookup.py`, `bootstrap_planner.py`, `registry_*.py` (13 files), `symbol_*.py` (3 files), `listing_equivalence.py`, `provider_*.py`, `resolver_domain.py`, `identity_resolver.py`, `transaction_canonicalizer.py`, `replay_*.py`, `migration_*.py`, `ledger_asset_backfill.py`, `ledger_evidence_builder.py`, `runtime_consultation.py`, `models/asset.py`, `models/database.py`, `services/asset_definitions/*` (the runtime itself).*

| File | Line | Function | Current usage | Category | Recommendation | Rationale |
|---|---|---|---|---|---|---|
| `asset_registry.py` | 72-110 | `_consult_runtime_for_mint()` | Compares legacy `True` (mint accepts every kind) against `DefinitionRegistry.exists(asset_type.value)`; logs disagreement | A | Keep — this is the sanctioned migration on-ramp | Telemetry/logging only, `_log.warning`, never gates `mint()` |
| `asset_registry.py` | 129-137 | `mint()` | Calls the above inside `try/except Exception` | A | Keep | Matches the existing, correct shadow-consultation pattern |
| `asset_registry.py` | 149 | `mint()` | `repo.create_asset(..., asset_type=claim.asset_type.value, ...)` | A | Keep | Persistence only |
| `registry_lookup.py` | 102, 142 | `AssetView`, `_to_asset_view()` | `asset_type: AssetType` field / `AssetType(asset.asset_type)` coercion | A | Keep | Pure read-model projection |
| `models/asset.py` | 54 | `Asset` model | `asset_type = Column(String, nullable=False)` | A | Keep | Persistence column |
| `models/asset.py` | 64-67 | `Asset` model | `tradable`, `fractional_support`, `lot_size`, `settlement_cycle` persisted alongside `asset_type` | A (flag for consolidation) | Evaluate deriving these from `CapabilityView` once more definitions exist, instead of persisting a second copy | These four columns duplicate exactly the facts (unit divisibility, acquisition semantics, settlement pattern) `CapabilityView` exists to declare — a latent dual-source-of-truth risk |
| `registry_symbol_matching.py` | 56-68 | `_legacy_bk_match()` | Symbol-suffix (`.BK`) equivalence helper | A | Keep | Decides symbol-spelling equivalence, not asset-kind behavior |
| `symbol_market_convention.py` | 67-83 | `infer_market_exchange()` | DR-pattern/`.BK`-suffix → market/exchange hint | A | Keep | Feeds `AssetClaim.market`/`exchange`, never `asset_type` |
| `symbol_normalization.py` | 29-64 | `get_yfinance_symbol()` | Symbol-shape if-chain → provider ticker | A | Keep | Provider routing only |
| `symbol_resolver.py` | 61-158 | `resolve_symbol()`, `is_dr()`, etc. | DR regex/map-based detection | A | Keep | Symbol/display routing only |
| `listing_equivalence.py` | 57-71 | `same_listing()` | DR-detection vetoes bundling two symbol spellings into one identity claim | A | Keep | Identity-equivalence decision, not behavior |
| `bootstrap_planner.py` | **171-177** | `build_bootstrap_plan()` | `AssetClaim(..., asset_type=AssetType.EQUITY, ...)` — **every** ledger-evidence-only mint is unconditionally typed `EQUITY` | **C — Legacy/Transitional (flagged risk)** | Needs resolution before any Stage R2 gate ships: either infer/require asset kind from richer evidence, or explicitly document/quarantine non-equity historical positions | Ledger evidence carries no asset-kind signal, so this is a structural placeholder that silently mislabels any historical BOND/FUND/etc. position as `EQUITY` — becomes consequential the instant `asset_type` is checked against the registry |
| `asset_domain.py` | 46-59 | `AssetType` enum | Declaration only, docstring: "Engines are expected to branch on this" | A | No action | Definitional; not itself a branch |
| `services/asset_definitions/*` | — | Runtime itself | `CapabilityView`, `GovernanceProjection`, `library.py`, `binding_resolver.py`, `enforcement_decisions.py`, `coverage_report.py` | N/A | Not a migration candidate — this is the target architecture | Confirmed still holstered: no engine calls `CapabilityView` directly yet, only the two shadow consumers |

All other identity/registry files (`registry_domain.py`, `registry_query.py`, `registry_service.py`, `registry_bootstrap.py`, `registry_classification_seed.py`, `registry_recommendation_context.py`, `registry_replay_parity.py`, `registry_findings_repository.py`, `asset_repository.py`, `provider_adapter.py`, `provider_domain.py`, `resolver_domain.py`, `identity_resolver.py`, `transaction_canonicalizer.py`, `replay_key.py`, `replay_cutover.py`, `migration_executor.py`, `migration_planner.py`, `migration_report.py`, `ledger_asset_backfill.py`, `ledger_evidence_builder.py`, `runtime_consultation.py`, `models/database.py`) contain **no** asset-kind branching.

**Domain total: A=11, C=1(flagged), B=0, D=0.**

---

### 3.2 Ledger / Portfolio / Execution / Evaluation Domain

*Files: `ledger_validator.py`, `ledger_repair*.py`, `repair_plan_executor.py`, `portfolio_transactions.py`, `portfolio_rebuilder.py`, `portfolio_snapshots.py`, `portfolio_metrics.py`, `snapshot_repair.py`, `snapshot_return_recovery.py`, `snapshot_scheduler.py`, `broker_fees.py`, `execution_plan.py`, `funding_source_analysis.py`, `basket_simulation.py`, `override_classifier.py`, `evaluation/*` (10 files), `optimizer/execution_penalty.py`, `execution_optimizer.py`, `constraint_resolver.py`.*

This is where nearly all Category B findings live.

| File | Line | Function | Current usage | Category | Recommendation | Rationale |
|---|---|---|---|---|---|---|
| `ledger_validator.py` | 1227-1322 (multiple) | `_consult_runtime_capabilities()` | `resolver.resolve(AssetType.EQUITY.value)` used as a hardcoded stand-in for "whatever the transaction actually is," because `Transaction` rows carry no resolvable asset-kind today | C | Keep as scaffolding; promote to a real per-transaction capability check once `Transaction.asset_id` is reliably populated | Self-documented as a proxy comparison, non-enforcing by design (Stage R1) |
| `ledger_validator.py` | **681** | `_replay_and_check()` | `if tx_type in _CASH_IN_TYPES or tx_type == "DIVIDEND": state.cash += amount` — DIVIDEND accepted for **any** symbol | **B — implicit/systemic** | Gate on `CapabilityView.grants_flow(FlowType.DIVIDEND)` once asset identity is resolvable at this call site | This is the exact legacy assumption the runtime-consultation block above already shadows but does not enforce |
| `portfolio_transactions.py` | 140, 272 | `execute_buy()`, `execute_sell()` | `resolve_fee_profile(symbol)` — fee schedule chosen by a `.BK` regex over the raw symbol, not by resolved asset identity | **B — explicit** | Migrate fee-profile selection to the already-resolved `asset_id`/registry lookup instead of a symbol regex | `resolved_asset_id` is computed a few lines away in the same function — the regex is redundant with data already in hand |
| `portfolio_transactions.py` | 466-522 | `execute_dividend()` | Accepts a DIVIDEND transaction for any symbol (or `None`), credits cash unconditionally | **B — explicit** | Gate on `grants_flow(FlowType.DIVIDEND)` | Nothing stops recording a "dividend" against a BOND/CRYPTO/PROPERTY symbol today |
| `portfolio_transactions.py` | 136-222, 262-342, 549-614 | `execute_buy/sell/initial_position` | Universal `value = shares × price` | **B — implicit/systemic** | Cross-check against `unit_quantity_equals_value()` before onboarding any non-equity-shaped kind | Baked into every write path; not a literal branch, but an unguarded assumption |
| `broker_fees.py` | 112, 125-136 | `resolve_fee_profile()` | `_DR_RE` regex (`.BK` suffix) selects `DR_STANDARD` vs `SET_STANDARD` | **B — explicit** | Migrate to identity/relationship-backed lookup (note: DR isn't an `AssetType` — it's `RelationshipType.DEPOSITARY_RECEIPT_OF`) | Textbook "fee rules differ by asset class," currently keyed by string heuristic entirely outside both `AssetType` and the runtime |
| `optimizer/execution_penalty.py` | **24-27, 39, 106-205** | `classify_execution()` | Local `EQUITY/DR/ETF/INDEX` taxonomy from regex + hardcoded ETF ticker set; drives liquidity/spread baselines, hard position caps (`DR_MAX_POSITION_PCT`), slippage premiums, score penalties | **B — explicit (highest priority)** | Reconcile with canonical `AssetType`/relationships, or formally adopt this as a *second*, deliberately execution-specific taxonomy — but stop letting it silently diverge from `AssetType` | A full parallel, ad-hoc classification system driving real execution behavior, entirely outside the Asset Definition Runtime; `DR`/`INDEX` aren't representable in `AssetType` at all today |
| `optimizer/execution_penalty.py` | 230 | `compute_portfolio_execution_context()` | `"asset_type": meta.asset_type` surfaced to prompts/UI | D | Re-source from real identity once migrated | Becomes pure display data after the above fix |
| `portfolio_snapshots.py` | 270-271, 297-298 | `generate_daily_snapshot()` | Universal `mv = shares × price` | **B — implicit/systemic** | Same `unit_quantity_equals_value()` cross-check | CASH is structurally excluded (separate balance field) but any other non-equity holding would be forced through this formula |
| `portfolio_snapshots.py` | 89, 368 | `generate_daily_snapshot()` | DIVIDEND treated unconditionally as market-related income | **B — implicit/systemic** | Same as `ledger_validator.py:681` | Third independent copy of the pattern |
| `snapshot_repair.py` | 494-495, 527-528 | `_repair_one()` | Same universal valuation formula, replayed | **B — implicit/systemic** | Same | Duplicate of the systemic assumption in the repair engine |
| `portfolio_metrics.py` | 138-142, 151-156 | `compute_period_metrics()` | `sum(shares × price)` for imported value and manual-adjustment value | **B — implicit/systemic** | Same | Highest-leverage single fix — this is the one canonical (ADR-004) metrics implementation shared by 3 engines |
| `portfolio_metrics.py` | 168-169 | `compute_period_metrics()` | `elif transaction_type == "DIVIDEND": period_dividend_income += ...` unconditional | **B — implicit/systemic** | Same as above | Same pattern, in the canonical shared module |
| `snapshot_return_recovery.py` | 66, 166, 173-177 | `_compute_return_fields()` | Delegates to `portfolio_metrics.compute_period_metrics()`; inherits the DIVIDEND filter | B — inherited | Fix upstream in `portfolio_metrics.py` | No independent logic of its own |
| `portfolio_rebuilder.py` | 359-360 | `_apply_transaction()` | Same universal DIVIDEND-acceptance pattern | **B — implicit/systemic** | Same as `ledger_validator.py:681` | Fourth independent copy (replay engine) |
| `portfolio_rebuilder.py` | 377, 419, 445, 612-613 | `_apply_transaction()`, `_build_snapshot_day()` | Same universal `shares × price`/avg-cost formula | **B — implicit/systemic** | Same `unit_quantity_equals_value()` cross-check | Same systemic pattern, replicated in the rebuild engine |
| `basket_simulation.py` | 192-196 | `simulate_basket()` | Same formula, low severity (no live money movement) | B — implicit, low priority | Same note, lower priority | Deterministic simulation only |
| `execution_plan.py` | 118 | `build_execution_plan()` | Same formula, feeds funding decisions | **B — implicit/systemic** | Same | Feeds real execution/funding sequencing |
| `execution_plan.py` | 128 | `build_execution_plan()` | `.BK` suffix widens a SQL `IN` filter; actual match delegated to registry | A | Keep | Filter-widening only, not a decision |
| `basket_simulation.py` | 288-308 | `_resolve_symbol_sectors()` | Registry-first symbol resolution with documented legacy `.BK` fallback | A | Keep | Identity resolution, not behavior |

No `AssetType`/asset-kind branching found in `ledger_repair.py`, `ledger_repair_plan.py`, `repair_plan_executor.py`, `override_classifier.py`, `snapshot_scheduler.py`, `funding_source_analysis.py`, `execution_optimizer.py`, `constraint_resolver.py`, or any of the 10 `evaluation/*.py` files (these operate on repair-type, transaction-type, signal, sector, and regime axes — orthogonal to asset identity). `evaluation/ideal_series.py:584`'s hardcoded `"^SET.BK"` benchmark constant is Category A (config/identity).

**Domain total: A=9, B=20 (8 explicit, 12 implicit/systemic), C=10 (concentrated in `ledger_validator.py`'s shadow block), D=1.**

---

### 3.3 Optimizer / AI Agents / Analytics / Decision-Memory / Timing-Intelligence Domain

*Files: `agents/*.py` (6), `optimizer/policy_engine.py`, `strategy_profiles.py`, `stabilization.py`, `scorer.py`, `idea_review.py`, `goal_profile.py`, `allocation_engine.py`, `position_sizing.py`, `portfolio_construction.py`, `analytics/factor_engine.py`, `analytics/regime_detector.py`, `decision_memory/*` (4), `regime_attribution.py`, `human_vs_ai_timing.py`, `timing_*.py` (5), `optimizer_timing.py`, `optimizer_action_summary.py`, `noise_filter.py`, `operations_center.py`, `run_progress.py`.*

| File | Line | Function | Current usage | Category | Recommendation | Rationale |
|---|---|---|---|---|---|---|
| `agents/optimizer.py` | 1937 | inline, "attach execution metadata for frontend badge rendering" | `a["asset_type"] = per_sym_exec[sym].get("asset_type", "EQUITY")` | D | Keep as AssetType-driven | Pure UI-badge metadata attachment, explicitly labeled, does not alter any decision |
| `agents/optimizer.py` | **91** | `_compute_portfolio_weights()` | Docstring: "equity-only"; `market_value = shares × price`, weight_pct correct only for equity-shaped holdings | **C (self-documented) / B if extended** | Replace the "equity-only" code comment with an explicit `unit_quantity_equals_value()`/`unit_divisibility()` check | The author already knew and scoped the limitation; making it a query instead of a comment is exactly what CapabilityView is for |
| `idea_review.py` | 93 | `_normalize_sector()` | `"REIT" in s → "Real Estate"` | N/A (excluded) | No action | Sector classification, not `AssetType` branching — a REIT equity and non-REIT equity take the same code path afterward |

No other `AssetType`/asset-kind branching, and **no CapabilityView/`services.asset_definitions.*` import**, in any of the other 28 files in this domain. `policy_engine.py`'s `violation_type` values (`CASH_BREACH`, etc.) are policy-violation classifications referring to the *cash floor*, not `AssetType.CASH`. `shadow_tracker.py`'s `shadow_type` (`STATIC_FROZEN`/`ACTIVE_MODEL`) is a shadow-portfolio lifecycle enum. `strategy_profiles.py`'s `dividend_bias`/factor tilts operate on computed factor exposure per symbol (via `factor_engine.py`), not on asset kind — a bond or REIT ETF flows through the identical weighting path as an equity today, unchecked.

**Domain total: D=1, C=1 (self-documented, not a literal branch).**

**The dominant finding in this domain is absence, not presence:** every technical (`RSI`/`MACD`), fundamental (`P/E`/`ROE`/`debt-equity`), factor (`growth/value/momentum/quality/dividend`), and timing-intelligence engine runs **unconditionally** on every symbol with zero capability gate. This is recorded as systemic risk item **SR-1** in §5 rather than as a per-line finding, because there is no branch to point to — only an absent one.

---

### 3.4 Market-Data / API Infrastructure / Frontend Domain

**Backend infrastructure:** swept `main.py` (6,889 lines), `manage.py`, all `models/*.py`, `market_data/*.py` (4 files), `sector_taxonomy.py`, `translations/muji_translator.py`, `routers/scheduler.py`, and every Alembic migration under `migrations/versions/`. **Zero** `AssetType`/asset-kind branching found anywhere in this set — adoption (in either direction: branching or runtime consultation) is entirely confined to the 9 production files listed in §2. Only one migration (`d6f8a0b2c4d6_add_asset_registry_foundation.py`) references `asset_type` at all, and it is schema DDL (Category A). `manage.py`'s `asset_definition_coverage` CLI help text is descriptive only.

| File | Line | Context | Current usage | Category | Recommendation | Rationale |
|---|---|---|---|---|---|---|
| `models/asset.py` | 64-67 | `Asset` model | (see §3.1 — duplicated here for cross-reference) | A (flagged) | See §3.1 | Dual-source-of-truth risk with `CapabilityView` |
| `market_data/provider.py` | 38-47 | `get_provider()` | Branches on `PRICE_PROVIDER` env var, not asset kind | A | No action | Deployment config, unrelated to `AssetType` |

**Frontend:**

| File | Line | Component | Current usage | Category | Recommendation | Rationale |
|---|---|---|---|---|---|---|
| `lib/api.ts` | **587** | module type | `export type AssetType = "EQUITY" \| "DR" \| "ETF" \| "INDEX"` | **D (naming collision, not a real dependency)** | Rename to `ExecutionAssetType` before any capability projection is ever exposed to the client | Same-named but unrelated to the backend's canonical `AssetType` — different members, different purpose (execution-risk classification, matches `execution_penalty.py` §3.2) |
| `lib/api.ts` | 590, 622 | `ExecutionSymbolMetadata.asset_type`, `TargetAllocation.asset_type` | Declared but never read by any component — only derived fields (`execution_risk`, `slippage_est_pct`, etc.) are consumed | D | Remove if confirmed dead, or document as reserved | Confirms zero client-side branching on this value |
| `components/TransactionModal.tsx` | 56-57 | component body | `isCash = mode === "deposit" \|\| "withdraw"`; `isEquity = mode === "buy" \|\| "sell" \|\| "initial_position"` | **B (Runtime Behavior candidate)** | When capability data is ever exposed to the client, derive form shape from `unit_quantity_equals_value()`/`acquisition_semantics()` instead of the caller-picked `mode` | Functionally re-implements the CASH-vs-EQUITY unit-axis distinction the runtime already declares, but keyed off UI workflow selection, not asset identity |
| `components/TransactionModal.tsx` | 100, 109, 305, 353, 371 | `total`, `canSubmit`, symbol/shares/amount fields | Field visibility and validation branch on `isCash`/`isEquity` | **B (Runtime Behavior candidate)** | Same as above | This is the frontend's version of the "fractional support"/"quantity vs. amount" concern named in the task brief |
| `components/TransactionModal.tsx` | 201, 445, 476 | header, placeholder, preview panel | Cosmetic copy/toggle differences by mode | D | Keep | Pure display |
| `components/PortfolioTable.tsx` | 38-67 | `DRBadge`, `UpsideCell` | Renders server-computed `is_dr`/`parent_symbol` | D | Keep | Server-computed relationship fact, display only |
| `app/watchlist/page.tsx` | 105-121 | `UpsideCell` | Same DR badge pattern | D | Keep | Duplicated component |
| `app/stock/[symbol]/page.tsx` | 637-644 | fundamentals panel | Same DR badge/tooltip pattern | D | Keep | Same |
| `lib/api.ts` | 115, 134, 200 | `PortfolioItem.is_dr`, `WatchlistItem.is_dr` | `is_dr?: boolean; parent_symbol?: string \| null` | A | Keep | Closest frontend analog to `permits_relationship()`, but display-only today |

**Frontend → backend dependency assessment:** the frontend has **no live dependency** on the backend `AssetType` enum or `CapabilityView` today. If/when frontend behavior is made capability-aware (e.g., `TransactionModal` deriving field shape from asset kind), a **new API surface does not exist yet and would need to be built** — most plausibly `GET /assets/{id}/capabilities` returning a client-relevant subset of `CapabilityView` (unit divisibility, quantity-equals-value, acquisition semantics). This is a prerequisite for any frontend migration work, not an incidental detail.

**Domain total: backend A=2 (+1 cross-referenced), frontend D=11, B=6.**

---

## 4. Classification Summary

| Category | Count | Where concentrated |
|---|---|---|
| **A — Identity (Keep)** | 23 | Registry/identity domain (11), ledger/execution domain (9), backend infra (3) |
| **B — Runtime Behavior (Candidate), explicit** | 14 | `execution_penalty.py` taxonomy (2), `broker_fees.py`/`portfolio_transactions.py` fee & dividend logic (3), frontend `TransactionModal.tsx` (6), other (3) |
| **B — Runtime Behavior (Candidate), implicit/systemic** | 12 | `value = shares × price` and unconditional-DIVIDEND, repeated across `ledger_validator.py`, `portfolio_transactions.py`, `portfolio_metrics.py`, `portfolio_snapshots.py`, `snapshot_repair.py`, `portfolio_rebuilder.py`, `basket_simulation.py`, `execution_plan.py`, `agents/optimizer.py` |
| **C — Legacy/Transitional** | 12 | `ledger_validator.py`'s Stage R1 shadow-consultation block (9), `bootstrap_planner.py`'s hardcoded EQUITY (1, flagged risk), `broker_fees.py`'s DR-placeholder (1), `agents/optimizer.py`'s equity-only comment (1) |
| **D — Presentation** | 18 | Frontend badges/copy (11), `execution_penalty.py`/`agents/optimizer.py` badge metadata (2), backend CLI help text (1), other (4) |
| **SR — Systemic risk (absence of a gate, not a branch)** | 2 items, ~12 call sites each cross-referenced above | AI/analytics engines running unconditionally on every symbol (§3.3); valuation/dividend formulas with no capability check (§3.2) |

---

## 5. Recommended Migration Candidates (Prioritized)

**SR-1 (highest priority, cross-cutting). Gate the "value = shares × price" and "DIVIDEND is always cash-additive" assumptions.**
Nine call sites across `ledger_validator.py`, `portfolio_transactions.py`, `portfolio_metrics.py`, `portfolio_snapshots.py`, `snapshot_repair.py`, `portfolio_rebuilder.py`, `execution_plan.py`, and `agents/optimizer.py` all independently assume equity-like unit and flow semantics with zero check. This is a correctness time-bomb, not a style issue: it will silently produce wrong NAVs or wrongly-accepted dividends the day a non-equity, non-cash asset enters a real portfolio. **Recommendation:** consolidate the DIVIDEND-acceptance check and the quantity×price valuation check into shared helpers (they are already conceptually shared via `portfolio_metrics.compute_period_metrics()` per ADR-004 — the same discipline should extend to the other five call sites), each backed by `CapabilityView.grants_flow(FlowType.DIVIDEND)` / `unit_quantity_equals_value()`, once `Transaction.asset_id` resolution is reliable enough to make the query meaningful (currently gated by the same limitation `ledger_validator.py`'s shadow consultation already documents).

**M-1. Reconcile `execution_penalty.py`'s `EQUITY/DR/ETF/INDEX` taxonomy with canonical `AssetType`.**
This is the one place a parallel, un-governed classification system drives real, hard behavior (position caps, slippage penalties). Two sound outcomes exist: (a) express `DR` via the existing `RelationshipType.DEPOSITARY_RECEIPT_OF` and `INDEX`/`ETF` via `AssetType`, retiring the local regex/ticker-list; or (b) formally document this as a deliberately separate, execution-specific taxonomy that is allowed to diverge from `AssetType` — but the current state (silent, undocumented divergence, plus a same-named-but-different type leaking into the frontend API) is not acceptable either way.

**M-2. Migrate `broker_fees.py` and `portfolio_transactions.py` fee-profile selection off the `.BK` regex.**
Fee calculation is a genuine financial computation. `resolved_asset_id` is already computed in the same functions that run the regex — this is close to a mechanical fix once M-1's DR-relationship question is settled.

**M-3. Fix `bootstrap_planner.py`'s hardcoded `AssetType.EQUITY`.**
Not a behavior migration in the CapabilityView sense, but a data-integrity gap that should be closed (or explicitly documented as an accepted limitation with a quarantine path) before any Stage R2 enforcement is authorized, since R2 would check exactly this field.

**M-4. Decide the AI/analytics/optimizer stack's stance on asset kind.**
No engine in `agents/*.py`, `factor_engine.py`, or the timing-intelligence stack checks asset kind at all. This is a scope decision more than a migration: either (a) explicitly gate these engines to run only on kinds whose shape they assume (equity-like fundamentals), or (b) accept that the platform's near-term roadmap has no non-equity/non-cash holdings and defer this. Given only `CASH`/`EQUITY` are defined today, deferring is defensible — but it should be a recorded decision (per this platform's own DECISION_LOG.md convention), not silent absence.

**M-5. `models/asset.py`'s redundant `tradable`/`fractional_support`/`lot_size`/`settlement_cycle` columns.**
Low priority, no active bug — but flagged as a dual-source-of-truth risk to retire opportunistically as more definitions are authored.

**M-6. `TransactionModal.tsx`'s mode-driven field logic.**
Cannot be migrated today — there is no API surface exposing capability data to the client (§3.4). Blocked on a future `GET /assets/{id}/capabilities`-style endpoint; recorded for when that exists, not actionable now.

**Rename-only, no migration needed:** `frontend/lib/api.ts:587`'s `AssetType` type should be renamed to avoid the collision with the backend's canonical enum before either taxonomy is touched further — this is cheap and removes a standing source of confusion for anyone reading both codebases together.

---

## 6. Risk Assessment

| Risk | Severity | Likelihood today | Notes |
|---|---|---|---|
| Non-equity asset enters ledger, silently gets wrong NAV via `shares × price` | High (financial correctness) | Low today (no non-equity holdings exist), rises to High the moment one is onboarded | SR-1; no alarms would fire — the systems would just compute a number |
| Non-equity asset gets a DIVIDEND recorded and accepted | High (financial correctness) | Same as above | SR-1; the ledger validator's own shadow consultation already proves this gap exists, it just doesn't act on it |
| `execution_penalty.py` taxonomy drifts further from `AssetType` as more kinds are added | Medium | Increases with each new `AssetType` usage elsewhere | M-1; the two systems already disagree on vocabulary (`DR`/`INDEX` vs the canonical 9) |
| `bootstrap_planner.py` mislabels a historical non-equity position as `EQUITY` | Medium | Only manifests if Stage R2 enforcement is ever authorized, or if any report trusts `asset_type` for historical bootstrap-minted assets | M-3; currently latent because nothing checks it yet |
| AI/analytics engines score a non-equity asset with equity-shaped fundamentals (P/E, ROE) | Medium | Zero today (no non-equity assets flow through), immediate the day one does | M-4; this is a "the moment a BOND appears in a portfolio" cliff-edge, not a gradual risk |
| Frontend `AssetType` naming collision causes a future engineer to conflate the two systems | Low | Ongoing, low-cost | Rename fixes it outright |
| Stage R1 shadow-consultation code itself changing production behavior | Very Low | Explicitly tested against (`test_asset_definitions_enforcement.py`'s migration-safety tests, `test_ledger_validator_runtime_consultation.py`) | Not a finding — this is working as designed |
| Vocabulary gaps blocking authorship of 6 of 7 remaining definitions (`ValuationQuestion`, `EventFamily`, `SettlementPattern` all need extension) | Medium, but already documented | N/A — already recorded | `enforcement_decisions.py` (M13) already did this analysis; this audit defers to it rather than re-deriving |

**None of these risks are urgent in the sense of "broken today."** They are all latent — correct only because the platform has never held anything but cash and equity. The risk profile inverts sharply the moment `ETF`, `BOND`, `FUND`, `CRYPTO`, `COMMODITY`, or `PROPERTY` moves from "enum member" to "actual position," which is precisely why this audit's value is in identifying them *before* that happens.

---

## 7. Suggested Implementation Order

1. **Rename** `frontend/lib/api.ts`'s `AssetType` → `ExecutionAssetType` (isolated, zero-risk, removes ongoing confusion). *Not gated on anything else.*
2. **SR-1**: Add `CapabilityView`-backed gates for DIVIDEND-acceptance and quantity×price valuation, starting with the shared `portfolio_metrics.compute_period_metrics()` (single highest-leverage call site per ADR-004), then propagate the same pattern to the other five/six call sites. Ship as a **shadow check first** (log-only, same pattern M11/M12 already established for `ledger_validator`/`asset_registry`) before ever gating — this repo has a strong, tested precedent for that rollout shape.
3. **M-3**: Resolve or explicitly document `bootstrap_planner.py`'s `EQUITY`-only assumption. Low effort, should not wait on anything else.
4. **M-1 + M-2**: Reconcile `execution_penalty.py` and `broker_fees.py`'s DR/ETF/fee-profile logic with canonical identity — likely needs a small, explicit decision on whether `DR`/`INDEX` become first-class or stay execution-domain-local, then a mechanical rewire of the two consumers.
5. **M-4**: Record an explicit decision (DECISION_LOG.md-style) on whether the AI/analytics stack should gate on asset kind now or defer — this is a judgment call for the platform owner, not something this audit should decide unilaterally.
6. **M-5**: Retire `models/asset.py`'s redundant columns opportunistically, as part of whichever future milestone authors the next Asset Definition (natural side effect of that work, not a standalone project).
7. **M-6**: Blocked — revisit once a capability-projection API endpoint exists. Not sequenced against the others; this is a "when," not a "next."
8. Only after the above, and only if the platform actually plans to onboard non-equity/non-cash assets soon: resume the M13 `enforcement_decisions.py` roadmap toward Stage R2 (vocabulary extensions for `ValuationQuestion`/`EventFamily`/`SettlementPattern`, then authoring `ETF_V1` as the closest-shaped candidate, then the harder four).

---

## 8. Estimated Effort

| Item | Effort | Notes |
|---|---|---|
| Frontend `AssetType` rename | 0.5 day | Mechanical, low risk, includes updating the ~3 consuming components |
| SR-1 shadow-check rollout (all 6-8 call sites) | 2-3 weeks | Follows the established M11/M12 shadow-consultation pattern; bulk of the time is in `portfolio_metrics.py`/`portfolio_rebuilder.py`/`ledger_validator.py` since they're the most-tested, highest-scrutiny modules in the repo (per DECISION_LOG's own regression-check discipline) |
| SR-1 → actual enforcement (Stage R2 for these specific gates) | Separate future decision, not estimated here | Depends on whether/which non-equity assets are ever onboarded; this audit's brief explicitly excludes implementation |
| M-3 (`bootstrap_planner.py` fix) | 1-2 days | Small, self-contained; main cost is deciding the correct fallback behavior, not the code change |
| M-1 (`execution_penalty.py` taxonomy reconciliation) | 1 week | Requires a design decision (see §7 step 4) before implementation; implementation itself is mechanical once decided |
| M-2 (`broker_fees.py`/fee-profile migration) | 3-4 days | Blocked on M-1's DR-relationship decision |
| M-4 (AI/analytics stance decision) | 0.5 day to decide, 0 to 3+ weeks to implement depending on the decision | The decision itself is cheap; implementation cost is entirely conditional on the outcome |
| M-5 (redundant column retirement) | Folded into future Asset Definition authoring milestones | Not a standalone project |
| M-6 (frontend capability API + `TransactionModal` migration) | 1-2 weeks, once unblocked | New endpoint + client integration; not startable yet |
| **Total for actionable items (excludes M-4/M-6 implementation, excludes Stage R2 enforcement itself)** | **~5-6 weeks** | Audit-only estimate; does not include the vocabulary-extension work `enforcement_decisions.py` already scoped for the remaining 6 Asset Definitions, which is a separate, larger, already-tracked effort |

---

## Appendix: Files confirmed to have zero AssetType/asset-kind branching

For completeness — these were read or swept in full and contain no findings of any category:

`registry_domain.py`, `registry_query.py`, `registry_service.py`, `registry_bootstrap.py`, `registry_classification_seed.py`, `registry_recommendation_context.py`, `registry_replay_parity.py`, `registry_findings_repository.py`, `asset_repository.py`, `provider_adapter.py`, `provider_domain.py`, `resolver_domain.py`, `identity_resolver.py`, `transaction_canonicalizer.py`, `replay_key.py`, `replay_cutover.py`, `migration_executor.py`, `migration_planner.py`, `migration_report.py`, `ledger_asset_backfill.py`, `ledger_evidence_builder.py`, `runtime_consultation.py`, `models/database.py`, `ledger_repair.py`, `ledger_repair_plan.py`, `repair_plan_executor.py`, `override_classifier.py`, `snapshot_scheduler.py`, `funding_source_analysis.py`, `execution_optimizer.py`, `constraint_resolver.py`, all 10 `evaluation/*.py` files, all 6 `agents/*.py` files except `optimizer.py`, `optimizer/policy_engine.py`, `optimizer/strategy_profiles.py`, `optimizer/stabilization.py`, `scorer.py`, `goal_profile.py`, `allocation_engine.py`, `position_sizing.py`, `portfolio_construction.py`, `analytics/factor_engine.py`, `analytics/regime_detector.py`, all 4 `decision_memory/*.py` files, `regime_attribution.py`, `human_vs_ai_timing.py`, all 5 `timing_*.py` files, `optimizer_timing.py`, `optimizer_action_summary.py`, `noise_filter.py`, `operations_center.py`, `run_progress.py`, `main.py`, `manage.py` (logic; CLI help text is Category A), `market_data/base.py`, `market_data/yahoo.py`, `market_data/yahoo_chart.py`, `sector_taxonomy.py`, `translations/muji_translator.py`, `routers/scheduler.py`, all Alembic migrations except `d6f8a0b2c4d6_add_asset_registry_foundation.py`.
