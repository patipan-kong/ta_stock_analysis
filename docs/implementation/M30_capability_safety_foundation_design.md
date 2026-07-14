# M30 — Capability Safety Foundation — Technical Design

**Status:** Design only. No production code, migrations, Asset Definitions, or enforcement were added to produce this document, per the milestone brief's explicit constraints.
**Depends on:** [portfolio_runtime_adoption.md](portfolio_runtime_adoption.md) (M29 audit). **Governed by:** [asset_definitions.md](../architecture/asset_definitions.md) (constitution, laws D1–D12), [OPTIMIZER_PHILOSOPHY.md](../investment/OPTIMIZER_PHILOSOPHY.md), [PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md), [ENGINEERING_PRINCIPLES.md](../engineering/ENGINEERING_PRINCIPLES.md).

---

## 0. What This Design Does Not Do

Per the brief's constraints, and worth stating before anything else so no reader mistakes intent: this document does not modify `portfolio_metrics.py`, `ledger_validator.py`, `execution_penalty.py`, or `bootstrap_planner.py`. It does not add an Alembic migration, a new Asset Definition, or a gate that blocks a transaction. Every code shape below (`class`/`def` blocks, file names) is a **proposal to be reviewed**, in the same spirit `enforcement_decisions.py` is prose describing a future decision rather than a decision itself. Where a question genuinely has no single correct architectural answer — and two of the six design areas do — this document says so explicitly in §5 rather than picking one to look decisive.

---

## 1. Current State (from M29)

Verified facts this design is built on, restated because they discipline every choice below:

- **Two** canonical Asset Definitions exist — `CASH` v1, `EQUITY` v1 (`docs/definitions/asset_definition_library.md`). `library.py`'s `DEFINITION_LADDERS` contains exactly these two keys. The other seven `AssetType` members boot clean but `DefinitionRegistry.exists()` is `False` for them.
- The runtime is at **Stage R1.5**: `CapabilityView`/`GovernanceProjection`/`DefinitionRegistry`/`BindingResolver` exist and are fully tested (M10), and exactly two production call sites — `ledger_validator._consult_runtime_capabilities()` (M11) and `asset_registry._consult_runtime_for_mint()` (M12) — run **read-only shadow consultations**: compute both the legacy answer and the runtime answer, log on disagreement via `_log.warning`, and **never raise, never gate, never alter the legacy result**. `enforcement_decisions.py`'s own docstring: *"This module makes no decision by itself and enforces nothing."*
- The two existing shadow consultations are coarse proxies, not per-instance checks: M11's dividend consultation shadows against `BindingResolver.resolve("EQUITY")` unconditionally (there is no way today to ask "what kind is *this* transaction's symbol," because `Transaction` carries a raw symbol string, not a resolvable `asset_id` — M9 TDD's own "cash is a column, not an asset" finding). M30 Design Area 1/3/4 below exist specifically to replace that coarse proxy with a real per-symbol answer.
- M29 found the highest-priority latent risk (**SR-1**) is not a branch anywhere — it is the *absence* of a gate at 9 call sites that assume `value = shares × price` and accept `DIVIDEND` unconditionally. This is the primary target of M30.
- M29 also found two lower-frequency but structurally distinct risks: `bootstrap_planner.py` hardcodes every ledger-only historical mint to `AssetType.EQUITY` (Design Area 5), and `optimizer/execution_penalty.py` runs a parallel, ungoverned `EQUITY|DR|ETF|INDEX` taxonomy that drives real execution behavior outside the Asset Definition Runtime entirely (Design Area 6).

---

## 2. Target Architecture

```
Current (every SR-1 call site, independently):

  Transaction / Holding
         │
         ▼
  value = shares × price          ◄── assumed, unconditional, 9 places
  DIVIDEND → cash += amount       ◄── assumed, unconditional, 4 places
         │
         ▼
  PortfolioSnapshot / LedgerFinding
```

```
M30 target (shadow stage — nothing here blocks anything yet):

  Transaction / Holding
         │
         ▼
  symbol/asset_id ──► capability_lookup_service.py  (impure: registry read)
         │                    │
         │                    ▼
         │            CapabilityView  (pure, in-memory, no DB — BindingResolver)
         │                    │
         │                    ▼
         │            capability_safety.py  (pure predicates)
         │                    │
         ▼                    ▼
  value = shares × price   compare against
  DIVIDEND → cash += amt   legacy assumption
         │                    │
         ▼                    ▼
  PortfolioSnapshot     ShadowFinding (additive field,
  (unchanged numerics)   log-only, never gates, never
                          changes a number) — same
                          discipline as M11/M12
```

The one-way arrow into "PortfolioSnapshot (unchanged numerics)" is the load-bearing property of this whole design: **every wire added in M30 is an observer, never a participant, in the arithmetic.** This is the same shape `OPTIMIZER_PHILOSOPHY.md` §5 insists on for its own pipeline ("later stages never mutate earlier stages' outputs") applied one layer down, and it is why M30 can ship without a migration, without a behavior change, and without a rollback plan more complex than "delete the optional call."

---

## 3. Capability Safety Architecture

### 3.1 The pure/impure split (Design Area 1)

`portfolio_metrics.py`'s existing contract is explicit and load-bearing (`ARCHITECTURE.md` §"Portfolio Metrics Engine", `PORTFOLIO_CALCULATION_RULES.md` §1 principle 1): **pure — no ORM, no DB session, no network access, no logging, no global state.** Resolving "what `AssetType` is symbol X" requires a registry lookup, which requires a DB session. Those two facts fix the shape of the design: resolution cannot happen inside `portfolio_metrics.py`. It must happen in the caller and be handed in, exactly the way `price_lookup: Mapping[str, float]` already is.

This is not a new pattern — it is the existing pattern, applied to a second kind of per-symbol fact. Two new modules, split along the same pure/impure line the codebase already draws:

**`backend/services/asset_definitions/capability_safety.py`** — pure, no DB, importable by `portfolio_metrics.py` itself (it already permits importing pure declaration types; `CapabilityView` has zero I/O).

```python
@dataclass(frozen=True)
class CapabilitySafetyAnswer:
    binding: str | None                      # AssetType.value if resolved, else None
    quantity_valuation_safe: bool | None      # None = unresolvable, treat as unknown
    dividend_flow_granted: bool | None
    resolved: bool

UNKNOWN_ANSWER = CapabilitySafetyAnswer(
    binding=None, quantity_valuation_safe=None, dividend_flow_granted=None, resolved=False,
)

def permits_quantity_valuation(view: CapabilityView) -> bool:
    """True when `quantity × price` is a valid valuation formula for this kind.

    Not simply `not unit_quantity_equals_value()` — Cash's own declaration proves
    why: quantity_equals_value=True means "one unit is worth one unit," which
    already makes shares×price correct in the degenerate case (price=1, always).
    The real disqualifier is Axis 4: a kind with valuation_question()==IDENTITY
    has no market price to multiply by at all (Cash's Capability Projection —
    "identity valuation, worth its face amount"). Both facts must be asked.
    """
    return not view.unit_quantity_equals_value() and view.valuation_question() != ValuationQuestion.IDENTITY

def grants_dividend_flow(view: CapabilityView) -> bool:
    return view.grants_flow(FlowType.DIVIDEND)
```

**`backend/services/asset_definitions/capability_lookup_service.py`** — impure (DB read), the *only* new module in this design that touches a session.

```python
def build_capability_safety_lookup(db: Session, symbols: Sequence[str]) -> Dict[str, CapabilitySafetyAnswer]:
    """Batch-resolve symbols to CapabilitySafetyAnswer. Never raises — an
    unresolvable symbol, an undefined AssetType, or a registry boot failure
    all collapse to UNKNOWN_ANSWER, exactly the never-raise discipline
    _consult_runtime_for_mint() and _consult_runtime_capabilities() already
    established (M11/M12). Callers get one dict; they never see an exception
    from this function as a distinct case from "unknown."
    """
```

Internally: reuse `registry_lookup.py`'s existing symbol→`AssetView` resolution (its TTL cache already exists — `ARCHITECTURE.md`'s Caching Strategy table has no entry for it today, worth confirming its cache window is safe for a per-run batch call, not re-deriving a second cache) to get each symbol's `AssetType`, then `BindingResolver.resolve(asset_type.value)`, catching `UnresolvedBindingError` and any `DefinitionRegistryError` from `DefinitionRegistry.build()` per-call, same as the two existing consultations. One `DefinitionRegistry` build per invocation of `build_capability_safety_lookup()`, not per symbol — batching this way is the direct fix for the N+1 the M11 code already avoids by building the registry once per `_consult_runtime_capabilities()` call.

This module is the **only** place in the entire design that performs symbol→kind identification. Every downstream consumer — `portfolio_metrics.py`, `ledger_validator.py`'s per-transaction check, `execution_plan.py` — receives only `CapabilitySafetyAnswer` values, never an `AssetType`, never a symbol-to-kind mapping of its own. This is the direct implementation of D5 ("engines consume declarations, never kinds") one layer removed from the two existing consultations: the *lookup service* identifies, once, in one place; everything downstream only ever asks a yes/no/unknown question.

### 3.2 Dependency graph

```
portfolio_snapshots.py ──┐
portfolio_rebuilder.py ──┤
snapshot_return_recovery.py ──┤──► capability_lookup_service.py ──► BindingResolver ──► CapabilityView
execution_plan.py ────────┤         (impure: registry_lookup.py)      (existing, R0)      (existing, R0)
agents/optimizer.py ──────┘
                                            │
ledger_validator.py ───────────────────────┤ (own call site — see §3.3, not via portfolio_metrics)
                                            ▼
                                   capability_safety.py (pure predicates)
                                            │
                                            ▼
                          portfolio_metrics.compute_period_metrics(
                              ..., capability_lookup: Mapping[str, CapabilitySafetyAnswer] | None = None
                          ) ──► PeriodMetrics.capability_shadow_findings: tuple[...] = ()   [additive]
```

No new module imports `services.asset_domain.AssetType` except `capability_lookup_service.py` (the identification boundary) — matching the existing discipline where only `asset_registry.py`, `library.py`, `ledger_validator.py`, `bootstrap_planner.py`, and `agents/optimizer.py` touch `AssetType` today. `capability_safety.py` imports only `CapabilityView` and `vocabulary.py`'s closed enums — no `AssetType`, no registry, no DB — so a future reviewer auditing D5 compliance (the same grep-based check `test_asset_definitions_enforcement.py` already runs for `governance.py`) can extend that check to this module with an identical assertion: **`capability_safety.py` and `portfolio_metrics.py` must never import `services.asset_domain` or `DefinitionRegistry`.**

### 3.3 Portfolio Metrics canonical path (Design Area 3)

`compute_period_metrics()` gains one new optional parameter, `capability_lookup: Mapping[str, CapabilitySafetyAnswer] | None = None`, defaulting to `None`. When `None` — every existing call site, unchanged — behavior is byte-identical to today; this is not a hypothetical backward-compatibility claim, it is the same guarantee `price_lookup` already gives when a caller omits it. When provided, for each `INITIAL_POSITION`/valuation-bearing transaction and each `DIVIDEND` transaction in the window, look up the transaction's symbol; if `resolved=False` (today, this will be the overwhelming majority — see the coverage caveat in §6), skip silently, exactly as if the lookup weren't provided at all. If resolved and the answer disagrees with the formula/acceptance the function is about to apply, append one `ShadowFinding` (a small frozen dataclass, symbol/check/legacy/runtime/detail — the same shape `RuntimeValidationFinding` already has, reused rather than reinvented per Reuse Before Create) to a new, additive `PeriodMetrics.capability_shadow_findings: Tuple[ShadowFinding, ...] = ()` field. **The numeric fields (`imported_asset_value`, `period_dividend_income`, etc.) are computed identically whether or not a finding is appended.** This mirrors `LedgerValidationReport.runtime_consultation` precisely: a sibling field, never merged into the value that already has callers depending on its exact numeric contract.

Because `portfolio_rebuilder.py` and `snapshot_return_recovery.py` already delegate to `compute_period_metrics()` (ADR-004), wiring the lookup into this one function is sufficient to cover three of M29's nine SR-1 call sites simultaneously — the same leverage ADR-004 already bought for formula consistency now pays off for shadow-check consistency. `portfolio_snapshots.py`'s own direct `mv = shares × price` sum (ARCH_SPEC §"PortfolioSnapshot columns", the live equity-value computation, distinct from the metrics-engine call) and `ledger_validator.py`'s independent `_replay_and_check()` loop are not reachable through `compute_period_metrics()` and need their own call to `build_capability_safety_lookup()` + `capability_safety.py` predicates, following the identical shape but as a local addition rather than a shared-function parameter (see §3.4 for the ledger validator specifically, since it already has a shadow-consultation call site to extend rather than a fresh one to add).

### 3.4 Dividend flow validation (Design Area 4)

**Required data:** a `Transaction.symbol → AssetType` resolution, which today only exists for symbols already minted in the registry. **Validation point:** two, not one — `ledger_validator._consult_runtime_capabilities()` already has a dividend shadow check (M11); it should be *upgraded* from its current EQUITY-hardcoded proxy to a real per-transaction check using `build_capability_safety_lookup()` over the DIVIDEND transactions' actual symbols, rather than adding a second, competing check. The second point is `portfolio_metrics.py` per §3.3, which is a different question (does today's *period* income figure include a flow the asset doesn't grant) from the ledger validator's question (is this *specific transaction* a defensible DIVIDEND record) — both are legitimate, neither subsumes the other, and this mirrors OPTIMIZER_PHILOSOPHY's own insistence that layers answering different questions stay distinct even when their inputs overlap.

**Historical transaction handling:** a DIVIDEND transaction recorded years ago against a symbol that (once resolvable) turns out not to grant a dividend flow is **never retroactively rejected or corrected** by this design. D8 ("definitions bind forward, never backward") and the platform's own ADR-002 ("Metrics never compensate for ledger corruption; validation belongs to Ledger Validator; repair belongs to Ledger Repair") both say the same thing from different directions: a shadow disagreement on a historical row is a **finding for a human to review**, routed through the same `ledger_repair_plan.py` pipeline that already exists for other detected anomalies — not a silent correction and not an automatic rejection. M30 stops at "surface the finding."

**Compatibility strategy:** identical to §3.3 — additive field, `None`-default parameter, zero change to any existing return value.

### 3.5 Bootstrap Planner Risk (Design Area 5)

The four options from the brief, evaluated:

| Option | Verdict | Reasoning |
|---|---|---|
| 1. Keep as explicit fallback | **Defensible as-is, but silent** | `EQUITY` is very likely statistically correct for this platform's actual historical holdings (M29 found zero non-equity/non-cash positions ever recorded). The defect isn't the guess — it's that the guess carries no marker distinguishing it from an evidenced fact. |
| 2. Introduce `UNKNOWN`/`UNCLASSIFIED` `AssetType` member | **Not recommended** | `AssetType` is reused per Reuse Before Create specifically *as* the canonical binding spelling (`library.py`'s own docstring: "Binding spellings reuse services.asset_domain.AssetType... rather than inventing a parallel vocabulary"). Adding a member changes what `mint()`, the registry, and every `AssetType` consumer must handle — and D9 ("the definition binding is as permanent as identity") means this ripples into minted, permanent state. A structural enum change to solve a provenance problem is a mismatch of tool to problem. |
| 3. Require additional evidence before minting | **Not recommended standalone** | Correct in principle, but `bootstrap_planner.py` exists precisely because ledger-only evidence is sometimes all that's available for a historical import; blocking the mint on stronger evidence that may never arrive would break the exact bootstrap flow this module is for. |
| 4. Quarantine before Stage R2 | **Recommended, combined with keeping the fallback (Option 1)** | Add a field to `AssetClaim` (or a sibling record, not a new enum member) recording *how* the type was determined — e.g. `type_provenance: "LEDGER_INFERRED" \| "EVIDENCED"`. This is a classification/metadata fact under D11/D12 (it never influences engine behavior, no engine branches on it), which is exactly the category the constitution says this kind of fact belongs in. A future R2 gate reads it to decide whether to exempt ledger-inferred mints from strict capability enforcement, or to surface them in a review queue — without touching the closed `AssetType` vocabulary at all. |

This is listed as **Open Decision #2** (§5) rather than a final answer, because it changes what gets persisted at mint time (however lightly) and D9's "permanent as identity" framing means even a low-stakes addition here deserves an explicit sign-off, not an inferred one.

### 3.6 Execution Taxonomy Boundary (Design Area 6)

This is the design area with the least clean answer, and the cleanest thing this document can do is say precisely where it forks, rather than resolve the fork by fiat.

**What the constitution actually says about DR.** `optimizer/execution_penalty.py`'s `DR` classification is not a disguised `AssetType` — checking `vocabulary.py` (the *definition* axis-7 vocabulary `CapabilityView.permits_relationship()` actually queries) shows `RelationshipKind` contains exactly `{SAME_ENTITY, WRAPS, SUCCESSOR_OF}`. There is no DR-equivalent member, and `vocabulary.py`'s own docstring flags this precisely: `RelationshipKind` is "deliberately distinct from `services.asset_domain.RelationshipType`... reconciling the two vocabularies is a Registry-domain question, out of scope." `RelationshipType.DEPOSITARY_RECEIPT_OF` already exists — but in `asset_domain.py`, the Registry's identity-linking vocabulary (already used by `listing_equivalence.py`), not in the Asset Definition Runtime's capability vocabulary at all. The constitution's own §5.2 boundary test agrees with this placement: *"'This contract's underlying is that listing' is the Relationships subdomain's recorded fact"* — DR-of is an instance-level edge between two identities, not a capability an Equity instance grants.

This means the honest **Option A** (Asset Definition → Execution Capability, DR flowing through `CapabilityView`) is not actually available today without a governed vocabulary extension to `RelationshipKind` first (constitution §8.1 Step 2) — a real, non-trivial decision, not a mechanical rewire. The honest **Option B** shape — DR resolved via the Registry's existing `RelationshipType` graph (`listing_equivalence.py`, `symbol_resolver.py`'s `is_dr()`), independent of `CapabilityView` — is buildable today with zero vocabulary changes, and is arguably *more* correct per the constitution's own boundary ruling, not merely more expedient.

**What the constitution says about the rest of the taxonomy:**
- **ETF** — per `asset_definitions.md` §9's own worked example, ETF is "Step 1" describable in the existing seven axes (venue-traded, discrete, cycle-settled, dividend/distribution flow, corporate-action events, dual valuation semantics) — a real `AssetType.ETF` definition is architecturally straightforward once someone authors it (M13's `enforcement_decisions.py` already scoped this: `GapType.MISSING_DEFINITION`, the lightest of the seven gaps).
- **Execution-risk profile itself (liquidity, spread, slippage baselines)** — constitution §5.3 explicitly rules this *out* of any definition: *"Liquidity — Rejected. Liquidity is weather, not climate: an observation about markets on a day, owned by Market Intelligence."* This is a firm answer, not a judgment call: no version of "reconcile the taxonomy with `AssetType`" should mean encoding spread/slippage baselines *into* a definition. They stay Execution/Market-Intelligence-owned, informed by (not derived from) the kind's declared acquisition/settlement semantics.
- **INDEX** — genuinely ambiguous from the code alone. It may denote index-tracking ETFs (redundant with the ETF migration above) or literal benchmark indices, which per `ARCHITECTURE.md`'s Market Regime Detection section (`^GSPC`, `^SET.BK`, `QQQ`) are already handled as non-holding reference data elsewhere in the codebase. If the latter, its presence in a *per-symbol portfolio execution classifier* may be a latent scope bug independent of any `AssetType` question. This needs a domain answer, not an architectural one (**Open Decision #4**).

**Recommended shape (not a final decision — see §5):** a per-execution **Execution Profile**, owned by the execution domain (not a projection of `CapabilityView`, not a new `AssetType`), synthesized from three independent inputs: (a) the resolved definition's declared acquisition/settlement semantics where available (`VENUE_TRADED`/`CYCLE_BASED` today for Equity — a real signal, just not the whole answer), (b) the Registry's relationship graph for DR-of edges (existing `RelationshipType.DEPOSITARY_RECEIPT_OF`, zero vocabulary change needed), and (c) live market observations (spread, ADV) that remain Market-Intelligence-owned per §5.3 and never migrate into a definition. This keeps `DR_MAX_POSITION_PCT`-style position caps where `OPTIMIZER_PHILOSOPHY.md` §2 Priority 2 already places risk/policy concerns — arguably `constraint_resolver.py`/`policy_engine.py`'s domain, not `execution_penalty.py`'s ad hoc constant, which is itself a candidate consolidation this design flags but does not scope.

---

## 4. Shadow Rollout Plan

Three stages, each independently shippable and independently revertible, following the exact "prove on one consumer, then fan out" discipline M11→M12 already used in this codebase.

### M30.1 — Foundation (no consumer wired)

**Scope:** `capability_safety.py` (pure predicates + `CapabilitySafetyAnswer`), `capability_lookup_service.py` (`build_capability_safety_lookup()`), full unit test coverage against the real `CASH_V1`/`EQUITY_V1` transcriptions plus the seven undefined-binding refusal cases (mirroring `test_asset_registry_runtime_consultation.py`'s existing seven-member sweep). **Risk:** none — nothing in the application calls these modules yet, the same "holstered" posture M10 shipped the runtime itself with. **Rollback:** delete two files; nothing else references them.

### M30.2 — Prove the pattern on one consumer

**Scope:** add the optional `capability_lookup` parameter and `capability_shadow_findings` field to `compute_period_metrics()`; wire exactly **one** caller — `portfolio_snapshots.py`, the live incremental engine, chosen because it is the lowest-blast-radius single caller (runs once per portfolio per day, not in a replay loop) and because M29 already flagged it as carrying two independent SR-1 instances (`mv = shares × price` at line 270-271/297-298, unconditional DIVIDEND handling). **Risk:** low — the new parameter defaults to `None` for every other caller, so `portfolio_rebuilder.py` and `snapshot_return_recovery.py` are provably unaffected by this stage; `portfolio_snapshots.py` itself only gains a log line on disagreement, never a changed number. **Rollback:** revert `portfolio_snapshots.py`'s one new call site; the now-dead optional parameter on `compute_period_metrics()` can stay (harmless, matches how `price_lookup` itself started as an option before every caller adopted it) or be reverted in the same commit.

### M30.3 — Fan out

**Scope:** wire the same lookup into `portfolio_rebuilder.py` and `ledger_validator.py`'s own `_replay_and_check()`/`_consult_runtime_capabilities()` (upgrading the M11 EQUITY-hardcoded dividend proxy per §3.4), each as its own reviewable change with its own full regression re-run — the exact granularity M11 and M12 shipped at. `execution_plan.py` and `agents/optimizer.py` (§3.2 of the M29 audit) follow once the pattern is proven stable across the ledger/snapshot engines; `snapshot_return_recovery.py` requires no separate work (inherits via `compute_period_metrics()`). **Risk:** individually low (identical log-only shape each time); aggregate risk is review fatigue across 4-5 similar-looking diffs, mitigated by sequencing them as separate PRs rather than one large one, matching `ENGINEERING_PRINCIPLES.md`'s "prefer improving existing code" in small, reviewable increments. **Rollback:** per-file, independent of the others — no stage in M30.3 depends on another stage in M30.3 having shipped.

**Explicitly not part of this rollout:** Design Areas 5 and 6 (bootstrap planner, execution taxonomy). Both require a product/architecture decision before any code changes (§5), and both touch higher-stakes surfaces than a log-only shadow check — one touches identity-minting state (D9), the other touches a live risk-control (`DR_MAX_POSITION_PCT`) that a wrong reconciliation could silently loosen.

---

## 5. Open Decisions

Decisions this document deliberately does not make, because they require product or architecture authority this audit doesn't have:

1. **Lookup batching/caching strategy.** Should `build_capability_safety_lookup()` share `registry_lookup.py`'s existing TTL cache, or maintain its own? A performance/architecture call, not a safety one — either answer is compatible with the design in §3.1.
2. **Bootstrap planner provenance marker (§3.5).** Recommended: keep the `EQUITY` fallback, add a non-enum `type_provenance` field. Requires sign-off because it changes what `AssetClaim` persists, however lightly, and D9 treats binding-adjacent facts as near-permanent.
3. **DR taxonomy routing (§3.6).** Route DR through the Registry's existing `RelationshipType.DEPOSITARY_RECEIPT_OF` graph (buildable today, zero vocabulary change) — or open a governed `RelationshipKind` vocabulary extension (constitution §8.1 Step 2) so `CapabilityView` can express DR-ness declaratively? The former is cheaper and arguably more correct per the constitution's own §5.2 ruling; the latter is more uniform with how every other execution-relevant fact is meant to flow. This is a real fork, not a formality.
4. **What "INDEX" means in `execution_penalty.py` (§3.6).** Domain question, not architectural: index-tracking ETF, or literal benchmark index that shouldn't be a per-symbol execution classification target at all?
5. **Graduation criteria for shadow → blocking.** Recommended: evidence-boxed, not time-boxed — SR-1 gating for a given `AssetType` only becomes a Stage-R2 candidate once that kind has a real definition (i.e., piggybacks on M13's existing `enforcement_decisions.py` roadmap rather than inventing a separate timeline). Needs explicit confirmation this is the intended relationship between the two workstreams.
6. **Shadow-finding persistence.** M30 defaults to log-only (no new table, no migration, matching the brief's constraints) — sufficient for a short shadow period, but trades away cross-run audit trail. Worth an explicit call if the shadow period is expected to run for months before an R2 decision is made.

---

## 6. Implementation Order

Ordered by risk reduction and dependency, not by document section:

1. **M30.1** (foundation modules + tests) — zero risk, unblocks everything else, no dependency on any Open Decision.
2. **Resolve Open Decision #2** (bootstrap planner) — cheap once decided (M29 estimated 1-2 days for the code change itself), fully independent of the SR-1 rollout, worth clearing early so it stops accumulating risk silently in the meantime.
3. **M30.2** (single-consumer proof on `portfolio_snapshots.py`) — highest-leverage validation of the whole pattern, including the telemetry format from Open Decision #6, before committing to it four more times.
4. **M30.3** (fan-out), one file at a time, in the order: `ledger_validator.py` (upgrades an existing, already-reviewed consultation rather than adding a new one — lowest incremental risk), `portfolio_rebuilder.py`, then `execution_plan.py`/`agents/optimizer.py`.
5. **Resolve Open Decisions #3/#4** (execution taxonomy) — can proceed in parallel with step 4, but must land *before* any code change to `execution_penalty.py`/`broker_fees.py` (M29's M-1/M-2 items) is attempted, since those changes are meaningless until the DR-routing fork is settled.
6. A note on **coverage**: `build_capability_safety_lookup()`'s findings are only as complete as the Registry's symbol population. If most historical `Transaction` rows reference symbols never minted into the registry, M30.2/M30.3 will initially produce very few findings — not because the platform is safe, but because most of the ledger is invisible to this check. This is not a defect in the design (an `UNKNOWN_ANSWER` fallback is the correct, D7-consistent behavior for an unresolvable symbol at shadow stage), but it is a real limit on how much confidence early shadow data should be given, and should be measured (what fraction of DIVIDEND/valuation-bearing transactions actually resolve) before any graduation decision (#5) leans on the shadow evidence.

---

## Success Criteria — Mapping

1. **Where capability checks live** — §3.1: pure predicates in `capability_safety.py`, resolution in `capability_lookup_service.py`, wired as an optional, additive parameter into `compute_period_metrics()` and as local additions at the two call sites that bypass it (§3.3, §3.4).
2. **How portfolio calculations stop assuming equity semantics** — not in M30 itself (M30 only observes and logs); the mechanism that will eventually do it is `permits_quantity_valuation()`, already designed and tested in M30.1, ready for an R2 decision to consume.
3. **How dividend flows become capability controlled** — same answer: `grants_dividend_flow()` exists and is shadow-wired by M30.3; actual control is an explicit future decision (§5, item 5), not this milestone's.
4. **How shadow validation works before enforcement** — §4: three staged, independently-revertible rollout steps, each strictly additive, none capable of changing a persisted number, following the exact discipline the M11/M12 shadow consultations already established and proved safe in production.
5. **How execution taxonomy remains separate from asset identity** — §3.6: DR is not, and per the constitution should probably not become, an `AssetType`; the recommended Execution Profile is explicitly synthesized from definition + relationship-graph + market-observation inputs, never a fourth parallel identity taxonomy, though the DR-routing question itself is left as an open fork (§5, item 3) rather than force-closed.
