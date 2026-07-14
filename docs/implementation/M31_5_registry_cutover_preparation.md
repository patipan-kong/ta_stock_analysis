# M31.5 — Execution Registry Cutover Preparation

**Date:** 2026-07-14

**Status:** Preparation complete; blocking cutover remains **NO-GO**

**Behavior mode:** `LEGACY_FALLBACK` by default. `FACTS_ONLY_SHADOW` and
`ENFORCE` are typed configuration values only and are intentionally inert in
M31.5.

## 1. Scope and invariants

M31.5 implements the remediation and observation foundations identified by
the M31.4 audit. It does not reject a transaction, remove an optimizer action,
filter an execution plan, alter funding arithmetic, change a fee, or retire
`execution_penalty_compat.py`.

The implementation preserves these invariants:

1. Registry identity, type, relationships, classifications, lifecycle, and
   tradability are the only authoritative support evidence.
2. Legacy ETF lists, DR/provider aliases, benchmark configuration, holdings,
   watchlists, and historical activity are review evidence, not authority.
3. No symbol regex, suffix, prefix, or spelling rule creates Registry data.
4. Resolver and adaptation failure remains non-raising and is now explicitly
   `REGISTRY_FAILURE` at the eligibility layer.
5. Preflight is read-only by default. Optional remediation requires both a
   manifest and explicit `--commit`; every instruction also requires
   `approved: true` and named evidence.
6. Native `asset_id` materialization remains reporting-only in this milestone.

## 2. Implementation map

| Component | Responsibility |
|---|---|
| `services/execution_registry_preflight.py` | Repeatable coverage, evidence, remediation-category, and native-ID readiness report. |
| `scripts/execution_registry_preflight.py` | Read-only-default CLI plus explicit manifest dry-run/commit modes. |
| `services/execution_registry_remediation.py` | Typed, evidence-required Registry writes through existing `registry_service` APIs. |
| `services/execution_cutover_config.py` | Central three-state configuration vocabulary and safe loader. |
| `services/execution_eligibility_observability.py` | Low-cardinality in-process counters and bounded diagnostic sampling. |
| `services/execution_eligibility.py` | Explicit `REGISTRY_FAILURE`, cutover-mode telemetry, and classification-agreement telemetry. |

No schema, migration, frontend, fee, funding, optimizer-policy, or execution
intent file was added.

## 3. Supported executable universe governance

The existing Registry representation is sufficient; no new table or enum is
needed. A symbol is a supported executable instrument only when all of the
following Registry evidence is present:

- identity resolves decisively to one `asset_id`;
- the Asset lifecycle status is `ACTIVE`;
- at least one current `PROVIDER_SYMBOL` identifier establishes the accepted
  execution-facing spelling;
- `Asset.asset_type` is valid and supplies the authoritative structural type;
- required market, exchange, currency, and display/canonical identity metadata
  is complete;
- `tradable=true` and execution facts produce role `TRADABLE`;
- the execution form is not `UNKNOWN`;
- a DR has exactly one outgoing `DEPOSITARY_RECEIPT_OF` relationship.

An index/benchmark reference is Registry-governed but is not in the executable
universe. The required representation is `AssetType.OTHER`, a current
`ASSET_CLASS=INDEX` classification with evidence source, and `tradable=false`;
execution facts then produce `REFERENCE + NOT_TRADABLE`.

Presence in a legacy list or operational table only creates a remediation
candidate. The preflight command labels those rows with their evidence source
and the missing Registry requirements; it does not convert them into facts.

### Existing representation limitation

The Registry service treats a new identifier of the same type as superseding
the prior current identifier. It therefore does not currently model multiple
simultaneously current `PROVIDER_SYMBOL` aliases for one asset through the
governed service. M31.5 can attach an explicitly approved current identifier,
but base/`.BK` dual-spelling support must be resolved by Registry governance or
by selecting one canonical accepted execution spelling before cutover. The
tool does not bypass the Registry service to create parallel aliases.

## 4. Preflight command

From `backend/`:

```text
python scripts/execution_registry_preflight.py
python scripts/execution_registry_preflight.py --workspace-id 1
python scripts/execution_registry_preflight.py --output preflight.json
python scripts/execution_registry_preflight.py --remediation-manifest reviewed.json --dry-run
python scripts/execution_registry_preflight.py --remediation-manifest reviewed.json --commit
```

`--commit` without `--remediation-manifest` is rejected. `--commit` and
`--dry-run` are mutually exclusive. Omitting both is read-only preflight plus,
when a manifest is supplied, rollback-only remediation preview.

Each report row contains:

- population and requested symbol;
- operational/configuration evidence;
- outcome (`ELIGIBLE`, `UNKNOWN_IDENTITY`, `AMBIGUOUS_IDENTITY`,
  `NOT_TRADABLE`, `REFERENCE_ONLY`, `REGISTRY_FAILURE`, or
  `INCOMPLETE_METADATA`);
- canonical symbol, `asset_id`, Registry `AssetType`, form, and role;
- relationship and current-identifier evidence;
- Registry fact/classification provenance;
- missing requirements and a deterministic remediation category.

Identity resolution runs in rolled-back savepoints so ambiguity adjudication
cannot leave a `RegistryFinding` behind. The generated report is plain data and
remains usable after rollback.

## 5. Registry coverage baseline

The command was run against the configured development PostgreSQL database on
2026-07-14 in default read-only mode. `RegistryFinding` was verified as zero
afterward. No remediation manifest was supplied and no persistent write was
performed.

| Population | Eligible | Other outcome | Coverage |
|---|---:|---:|---:|
| Current holdings | 19/21 | 2 UNKNOWN | 90.5% |
| Workspace watchlist | 18/87 | 69 UNKNOWN | 20.7% |
| Optimizer reachable, portfolio 2 | 18/87 | 69 UNKNOWN | 20.7% |
| Optimizer reachable, portfolio 3 | 19/88 | 69 UNKNOWN | 21.6% |
| Optimizer reachable, portfolio 4 | 18/87 | 69 UNKNOWN | 20.7% |
| Latest actionable allocations | 9/12 distinct | 3 UNKNOWN | 75.0% |
| Historical executable transactions | 21/25 distinct | 4 UNKNOWN | 84.0% |
| Configured ETF review population | 0/10 | 10 UNKNOWN | 0.0% |
| Configured DR/provider alias review population | 0/9 | 9 UNKNOWN | 0.0% |
| Default reference review population | 0/1 | 1 UNKNOWN | 0.0% |

The unresolved current holdings remain `GOOGL01.BK` and `GULF.BK`. The latest
unresolved actionable symbols remain `ASML01.BK`, `PLANB.BK`, and `STECON.BK`.

The configured-review totals differ intentionally from M31.4's exploratory
counts: M31.5 reports the nine literal configured DR alias keys, not inferred
base/`.BK` spelling pairs, and reports the default benchmark candidate that is
not already in the ETF-review population (`^SET.BK`). This avoids generating
candidate identities from spelling.

## 6. Remediation categories and candidates

The read-only run produced these distinct review sets:

- `REGISTER_OR_ATTACH_IDENTIFIER`: unresolved operational symbols, including
  the five current/actionable blockers named above;
- `REVIEW_AND_REGISTER_ETF`: `ARKK`, `EEM`, `GLD`, `IVV`, `QQQ`, `SPY`,
  `TLT`, `VTI`, `XLF`, and `XLK`;
- `REVIEW_DR_IDENTITY_AND_UNDERLYING`: the nine configured provider alias keys;
- `REVIEW_AND_REGISTER_REFERENCE`: `^SET.BK` from default benchmark
  configuration;
- `ADJUDICATE_IDENTITY`, `COMPLETE_REGISTRY_METADATA`,
  `REVIEW_TRADABILITY`, and `RESTORE_REGISTRY_INFRASTRUCTURE` when those typed
  outcomes occur.

These are candidates, not approved changes. No symbol in these lists is minted,
typed, linked, or made tradable by the report.

## 7. Evidence-required remediation contract

The version-1 JSON manifest uses explicit operations:

- `MINT_ASSET` — complete explicit Asset type/market/exchange/currency,
  tradability, execution metadata, and identifier;
- `MINT_ETF` — additionally requires explicit `asset_type=ETF`;
- `MINT_DR` — requires an existing authoritative `underlying_asset_id` and
  creates exactly one outgoing `DEPOSITARY_RECEIPT_OF` relationship;
- `MINT_INDEX_REFERENCE` — requires explicit `asset_type=OTHER` and
  `tradable=false`, then records `ASSET_CLASS=INDEX` with the evidence source;
- `ATTACH_IDENTIFIER` — attaches one explicit Registry identifier to an
  existing asset;
- `LINK_DR_RELATIONSHIP` — links existing receipt/underlying assets only after
  verifying the underlying exists and no conflicting DR relationship exists;
- `REGISTER_INDEX_REFERENCE` — accepts only an existing `OTHER`, non-tradable
  asset and records the current index classification.

Every instruction requires `instruction_id`, `approved: true`,
`evidence_source`, and `evidence_note`. Unapproved instructions are reported as
`SKIPPED_NOT_APPROVED`. Validation occurs before mutation. Dry-run mutations
run inside a rolled-back savepoint. Commit mode uses only existing Registry
service methods and invalidates the Registry read cache afterward.

Runtime symbol shape is never an input to remediation. Tests prove that a
DR-shaped symbol minted as an explicitly approved EQUITY receives no DR
relationship, while a non-DR-shaped symbol receives DR form only when an
approved `MINT_DR` instruction names an existing underlying asset.

## 8. Explicit Registry failure outcome

`ExecutionEligibilityOutcome` now includes `REGISTRY_FAILURE`. Pure evaluation
checks `ExecutionInstrumentFacts.resolution_error` before ordinary identity,
role, or tradability outcomes. Therefore:

- no matching Registry identity → `UNKNOWN_IDENTITY`, `registry_failure=false`;
- multiple identity candidates → `AMBIGUOUS_IDENTITY`;
- incomplete Registry metadata → ordinary unresolved facts, reported by
  preflight as `INCOMPLETE_METADATA`;
- resolver/adaptation infrastructure error → `REGISTRY_FAILURE`,
  `registry_failure=true`.

This is vocabulary and telemetry only. M31.3 consultation remains post-result,
post-arithmetic, or post-commit and exception-contained; no rejection was
added.

## 9. Durable/aggregatable shadow observability

The project has structured process logging but no established Prometheus,
StatsD, or equivalent metrics dependency. M31.5 therefore reuses operational
logging and adds process-local counters rather than introducing a table or
migration.

The counter key contains only these low-cardinality labels:

- boundary;
- eligibility outcome;
- resolution status;
- instrument form;
- execution role;
- cutover mode;
- Registry-failure boolean;
- legacy/new classification agreement (`AGREE`, `DISAGREE`, `UNKNOWN`).

Raw symbol and `asset_id` are structurally absent from metric keys. Each
consultation emits a structured low-cardinality metric log suitable for the
existing log aggregator. Rich diagnostics retain symbol and provenance but are
bounded to three samples for each of at most 100 low-cardinality keys per
process. The counter snapshot API is available for operations/tests without a
database dependency.

Optimizer telemetry supplies M31.2's `classification_agrees` value. Plan and
transaction boundaries report `UNKNOWN` agreement because they have no legacy
instrument-classification result at those boundaries.

Before `FACTS_ONLY_SHADOW`, operations must confirm that deployed logs are
retained and queried into a review artifact. Process-local counters reset on
restart; the structured log sink is the durable record.

## 10. Feature-flag contract

One central adapter reads `EXECUTION_ELIGIBILITY_CUTOVER_MODE`:

| Value | M31.5 meaning |
|---|---|
| `LEGACY_FALLBACK` | Default; current M31.2/M31.3 behavior. |
| `FACTS_ONLY_SHADOW` | Typed future value; telemetry label only in M31.5. |
| `ENFORCE` | Typed future value; telemetry label only in M31.5. |

Strict configuration loading rejects invalid non-empty values with
`ExecutionCutoverConfigurationError`. Runtime shadow telemetry catches that
configuration error, logs it, and safely selects `LEGACY_FALLBACK`; an invalid
value can never enable enforcement. The process caches the mode through this
one adapter. Pure facts/eligibility evaluation does not read environment
variables.

Focused tests set the mode to `ENFORCE` and prove an unregistered initial
position still commits and an unregistered execution-plan action remains in
the plan. Later milestones must explicitly wire behavior; the enum alone has
no authority.

## 11. Native `asset_id` readiness

| Table | Rows | Materialized | Exactly resolvable | Missing but resolvable | Unresolved | Ambiguous/failure/conflict |
|---|---:|---:|---:|---:|---:|---:|
| `portfolio_items` | 21 | 0 | 19 | 19 | 2 | 0 |
| `watchlist` | 87 | 0 | 18 | 18 | 69 | 0 |
| executable `transactions` | 52 | 0 | 41 | 41 | 11 rows | 0 |

The report includes row-level dry-run proposals for the 78 exactly resolvable
unmaterialized rows. It performs no update.

Materialization is recommended before enforcement for holdings and transaction
admission evidence because it reduces repeated symbol adjudication and records
which identity was accepted. It is not by itself an eligibility decision and
must not be backfilled until the existing Registry adjudication/governance
process approves the proposal. Watchlist materialization may follow after the
69 unresolved entries are reviewed. Rollback would set only rows changed by a
recorded backfill run back to their prior null value; a future implementation
needs a durable run manifest because M31.5 intentionally adds no write path.

## 12. Verification and behavior invariants

Focused M31.5 tests cover operational-population reporting, explicit Registry
failure, incomplete metadata, dry-run rollback, approved-only commit,
relationship-backed DR remediation, absence of regex-derived DR writes,
explicit ETF type, Registry-backed index reference, supported-universe
governance, safe feature configuration, low-cardinality telemetry, inert future
modes, compatibility retention, and absence of a blocking branch.

Verification results:

- combined M31.1/M31.2/M31.3/M31.5 focused suite: **58 passed**;
- M31 plus Registry/bootstrap group: **177 passed**, with two
  `test_registry_replay_parity.py` tests initially unable to create pytest's
  user-temp directory; both passed when rerun with `--basetemp` in the
  workspace, for **179 verified**;
- portfolio transaction/accounting/write-boundary group: **103 passed**;
- optimizer/execution group: **155 passed** after five pre-existing
  test-isolation failures in `test_optimizer_history_snapshot_injection.py`
  passed with the Registry Asset mapper imported, and four pre-existing stale
  `_consensus_engine(l2, l3)` failures remained in
  `test_optimizer_pipeline.py`:
  `test_consensus_rebalance_high_confidence`,
  `test_consensus_no_action_low_score`,
  `test_consensus_l1_parse_failure_propagation`, and
  `test_consensus_critical_flag_forces_rebalance`.

No production response schema, allocation, plan arithmetic, fee, transaction
admission result, or persistence lifecycle changed. `git diff --check` passes.

The live preflight was read-only; no remediation fixture or production record
was committed. The only writes exercised were isolated in-memory test database
fixtures proving explicit commit semantics.

## 13. Remaining blockers

`FACTS_ONLY_SHADOW` must not be enabled until all of the following are true:

1. Every current holding and optimizer-reachable supported symbol is Registry
   resolved with complete metadata.
2. The 10 ETF candidates are explicitly adjudicated and supported ETFs are
   Registry `ETF` assets.
3. Supported DRs have governed identities, current identifiers, and exactly one
   authoritative underlying relationship.
4. Supported benchmark indices resolve as non-tradable references.
5. Alias policy resolves the single-current-provider-identifier limitation.
6. Valid supported instruments no longer need compatibility to select a risk
   profile.
7. Durable structured telemetry has completed the approved observation window,
   with all disagreements and Registry failures reviewed.
8. Resolved EQUITY/ETF/DR optimizer outputs remain parity-clean under a future
   facts-only implementation.

`ENFORCE` additionally requires every M31.4 cutover precondition: guards moved
before persistence/arithmetic/commit, typed API errors, optimizer/plan exclusion
contracts, frontend compatibility, Registry outage policy, canary/rollback
drill, and an enforcement-specific approval. M31.5 satisfies none of those by
merely defining the mode.
