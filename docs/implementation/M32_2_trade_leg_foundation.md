# M32.2 — Constrained Trade Legs and Shadow Cost-Aware Planning

**Date:** 2026-07-14

**Status:** Implemented as shadow-only. Canonical execution-plan cutover remains deferred.

## Contract

`backend/services/execution_trade_leg.py` introduces immutable, versioned
`ExecutionTradeLeg` values. One leg represents one proposed executable trade
without becoming an instruction, order, persistence record, or API payload.

Each leg includes:

- deterministic `leg_id` and `contract_version`;
- recommendation reference, requested symbol, Registry `asset_id`, and
  canonical symbol where Registry facts establish them;
- side, requested/executable quantity, price timestamp, gross amount, total
  estimated cost, and signed estimated net cash effect;
- the original `FeeQuote`, `ExecutionInstrumentFacts`, and
  `ExecutionEligibility` objects, plus convenient form/role summaries;
- an explicit funding role, M32.2 no-op lot/fractional adjustment summaries,
  warnings, provenance, and a completeness flag.

Quantities are `Decimal`. The M32.2 constraint is exact:
`requested_quantity == executable_quantity`. No lot rounding, fractional
adjustment, FX/base-currency conversion, price refresh, deferral, partial fill,
or funding optimization is applied.

For a successful quote, gross, total cost, and signed net cash are direct
projections of that quote. The builder does not recalculate them. For an
unavailable quote, all leg monetary fields are `None`; the original requested
quantity and explicit Registry/eligibility status remain visible. An
unavailable quote is never presented as a free trade.

## Builder and reuse boundary

`ExecutionTradeLegBuilder.build()` is the one construction boundary. It takes
only:

1. `LegacyExecutionTradeRequest` with an already-known quantity and price;
2. `ExecutionInstrumentFacts`;
3. `ExecutionEligibility`; and
4. `FeeQuote`.

It has no database session, ORM, Registry resolver, fee selector, calculator,
clock, or symbol taxonomy. The builder validates only that a successful quote
has the same side, quantity, and price as its legacy request. It retains the
three supplied contract objects by identity.

Warnings are deduplicated direct values from facts, non-eligible eligibility
reasons, and `FeeQuote.warnings`; no new warning vocabulary is invented.
Facts provenance and quote/request provenance are carried as diagnostic
evidence only.

## Shadow integration

`services.execution_plan.build_execution_plan()` still constructs and returns
the exact legacy `ExecutionPlanResult`. After that result exists, it performs
the existing M31.3 one-batch facts resolution and eligibility consultation.
M32.2 then consumes those same facts for a post-result debug-only projection:

```text
legacy active funding action
  + Registry facts + eligibility
  + facts-backed FeeQuote
  -> ExecutionTradeLeg
  -> structured debug comparison
```

For each priceable active `SELL`/`REDUCE` funding action, M32.2 uses the
legacy shares × release percentage and derives the legacy price from its own
estimated release. It records the unchanged legacy gross amount alongside the
quoted gross, estimated total cost, and signed net cash effect in a log-only
diagnostic. This does not alter legacy funding selection, cash release,
deployment, warnings, status, response shape, or persistence.

Current `BuyAction` provides only a gross estimated allocation; it has neither
quantity nor unit price. M32.2 explicitly records such BUY symbols as
unprojectable in the private diagnostic rather than reverse-engineering a
fictional quantity. The projection is fully exception-contained with the
existing post-result shadow block, so a Registry, quote, or diagnostic failure
returns the unchanged legacy plan.

No new API field is emitted. `ExecutionTradeLegShadowProjection` is an
internal immutable diagnostic object and is not retained, persisted, or passed
to the frontend.

## Invariants

- M31 facts and eligibility remain descriptive; no outcome blocks or changes a
  plan.
- Registry resolution happens once at the existing execution-plan shadow
  boundary. The trade-leg builder performs no lookup.
- Fee selection is facts-backed through M32.1. The transaction compatibility
  fee path is not used by the shadow planner and is not removed.
- Legacy plan amounts stay gross. Net numbers are diagnostics only.
- Optimizer recommendations, ledger posting, replay, broker fees, funding
  arithmetic, response schemas, frontend behavior, persistence models, and
  M31 cutover modes are unchanged.

## Future M32.3 integration requirements

M32.3 cannot make these legs authoritative until it supplies a normalized
input with price/quantity for every active BUY and SELL, a price-freshness
contract, lot/fractional policy, base-currency/FX ownership, net-of-cost
funding arithmetic, and an API/persistence decision for a canonical execution
plan. It must also define quote expiry/requote behavior and resolve Registry
fee-schedule coverage without relying on `broker_fees_compat.py`.

## Explicit non-goals

M32.2 adds no execution-plan replacement, funding/cash balancing, lot or
fractional policy, partial execution, FX, price refresh, optimizer or
evaluation change, frontend/API change, schema/migration, execution intent,
M31 enforcement, compatibility removal, commit, or push.

## Verification

- Focused M32.2 contract and shadow tests: **10 passed**.
- M32.2 + M32.1 fee/accounting + execution-plan + M31 consumer/Registry
  integration group: **91 passed**.
- Broader transaction/write/replay-adjacent group: **250 passed**.
- Registry replay parity: **28 passed** when pytest used a workspace-local
  `--basetemp`; the default Windows user-temp directory is inaccessible in
  this environment.
- Optimizer execution/timing regression tests: **36 passed**. Optimizer
  history injection adds **5 passed** when the Registry Asset mapper is
  imported, as its focused in-memory metadata requires.
- Python syntax compilation and `git diff --check` pass.

The only observed failures were pre-existing/environmental: four stale
`test_optimizer_pipeline.py` tests call `_consensus_engine(l2, l3)` without its
required leading argument; five optimizer-history tests fail when executed in
an import order that omits `models.asset`; and nine async replay-cutover tests
cannot run because this test environment lacks the async pytest plugin. None
touches M32.2 code.
