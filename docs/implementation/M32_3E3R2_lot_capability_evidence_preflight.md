# M32.3E3R2 — Lot Capability Evidence Contract and Read-only Preflight

**Date:** 2026-07-15

**Status:** Implemented as a strictly read-only governance foundation. Capability projection updates remain unavailable, and M32 canonical planning remains **NO-GO**.

## Scope

R2 adds an immutable external-evidence contract, strict review-manifest parser, authority-trust boundary, batch-safe Registry collector, deterministic JSON preflight report, and read-only CLI. It does not update `Asset.lot_size` or `Asset.fractional_support`, create an evidence table, add a migration, mutate a Registry row, invalidate the Registry cache, or add a commit branch.

M32.3E1/E2 consumers are unchanged: `lot_size=None` remains incomplete and never defaults to one.

## Semantic definition

`Asset.lot_size` means the listing's positive integer **standard-board order quantity increment**, expressed in the Registry unit, for an explicit effective period. For Equity assets the unit is `SHARE`; a value of 100 means standard-board quantities are whole 100-share increments.

It is not a broker order increment, minimum order quantity, settlement unit, execution-policy lot, odd-lot rule, alternate-board rule, symbol convention, or market-wide default. `fractional_support` is a separate explicit listing fact about non-integral Registry units; it is not evidence that a selected broker offers fractional trading.

## Evidence contract

`services.execution_lot_capability.LotCapabilityEvidence` is frozen and versioned. It requires:

- decisive `asset_id` and explicit `RegistryIdentitySnapshot` with canonical symbol and exact current identifiers;
- governed `SHARE`, `STANDARD_BOARD_EXECUTION`, and `QUANTITY_INCREMENT` vocabulary;
- explicit positive integer `lot_size` and exact boolean `fractional_support`;
- source ID/type/locator/record key/version, publication/retrieval time, authority, bounded provenance, effective period, reviewer, and approval state; and
- optional supersession/rollback references.

All timestamps are timezone-aware. `evidence_ref` is a deterministic hash of normalized immutable content; a supplied reference must match exactly. `VERIFIED` evidence can remain a draft, but `APPROVED` evidence must also be `VERIFIED`; confidence and approval are independent facts.

## Source authority boundary

`LotCapabilityAuthorityTrust` takes a caller-injected tuple of approved `source_id` / `authority` / official source-type bindings. It reads no environment and defaults to empty. R2 permits only `EXCHANGE_MASTER`, `LISTING_NOTICE`, and `OFFICIAL_INSTRUMENT_MASTER` types.

An HTTPS locator, market/exchange string, AssetType, ticker spelling, provider payload, historical quantity, fee profile, UI precision, or Asset Definition permission is not authority. Untrusted evidence reports `APPROVAL_REQUIRED`; it is never selected automatically.

## Manifest and dry-run

The review-only manifest contains `manifest_version`, `manifest_id`, and `UPDATE_LOT_CAPABILITY` instructions. Every instruction has:

- `asset_id`, explicit `expected_current` identity/capability/timestamp snapshot;
- a `proposed` unit/scope/semantics/lot/fraction/effective-time payload that exactly matches the evidence;
- complete `LotCapabilityEvidence`; and
- explicit prior-value rollback snapshot and implication.

The parser rejects implicit/coerced booleans or quantities, missing source/review/effective/provenance fields, naive timestamps, duplicate instruction/evidence references, multiple instructions for one asset, effective overlap, unresolved supersession references, and invalid `APPROVED`/`VERIFIED` combinations. Future-effective and expired evidence is preserved for review but cannot be treated as current.

R2 performs an in-memory prospective before/after comparison only. It resolves by `asset_id`, checks exact identity and expected current state, then reports `WOULD_REVIEW` or `EXPECTED_CURRENT_MISMATCH`. It has no Registry remediation call, ORM mutation, evidence-row creation, cache invalidation, or `--commit` branch.

## Collector and outcomes

`build_lot_capability_preflight()` loads Assets, current identifiers, capability projections, Asset Definition permissions, and supplied manifest evidence in bounded batch queries. It builds the Asset Definition Runtime once per report and asks only whether lot/fractional refinements are permitted. Definitions cannot provide a value; a consultation failure is non-raising and quarantined.

Current holdings and `BUY`/`SELL`/`INITIAL_POSITION` quantities appear only under `NON_AUTHORITATIVE_CANDIDATE_EVIDENCE`. The collector/parser contains no GCD, minimum, common-multiple, suffix, exchange, AssetType, or symbol derivation.

The report uses `READY_FOR_REVIEW`, `MISSING_EVIDENCE`, `UNVERIFIED_DEFAULT`, `IDENTITY_MISMATCH`, `CONFLICT`, `STALE_SOURCE`, `FUTURE_EFFECTIVE`, `EXPIRED_EVIDENCE`, `INVALID_VALUE`, `DEFINITION_REFINEMENT_NOT_PERMITTED`, `APPROVAL_REQUIRED`, and `QUARANTINED`. `READY_FOR_REVIEW` does not permit a write. Mixed records quarantine; there is no highest-confidence-wins behavior. Bootstrap `fractional_support=False` reports `UNVERIFIED_DEFAULT` until governed evidence arrives, while absent lot is a separately listed missing requirement.

## Deterministic artifact and CLI

The report builder receives `generated_at`; it does not read a clock. JSON contains separate raw and governed coverage, outcomes, per-asset identity/evidence/definition/candidate data, manifest decisions, bounded source references, and `no_writes_performed=true`.

From `backend/`:

```text
python -m scripts.execution_lot_capability_preflight
python -m scripts.execution_lot_capability_preflight --generated-at 2026-07-15T00:00:00+00:00
python -m scripts.execution_lot_capability_preflight --manifest reviewed.json --output lot-preflight.json
```

`--commit` is recognized only to fail explicitly as unsupported. It cannot silently enable a mutation path.

## Current readiness baseline

| Coverage | Result |
| --- | ---: |
| Registry assets | 21 |
| Positive `lot_size` projection | 0 / 21 |
| Raw `fractional_support=False` projection | 21 / 21 |
| Governed lot/fractional evidence | 0 / 21 |
| Automatically remediable assets | 0 / 21 |

The default trust list is empty, so no current capability value is promoted. Existing bootstrap false values remain `UNVERIFIED_DEFAULT`.

## Security and provenance

Report output contains bounded locators, record keys, versions, and provenance/checksum strings, never unrestricted source documents or secrets. Exact identity snapshots prevent evidence for one listing being transferred to a similar symbol. A future write milestone needs append-only evidence storage and an atomic Registry projection update; a checked-in manifest alone is not enough to explain environment-specific capability state.

## M32.3E3R3 prerequisites

1. A named authority trust list and external per-listing capability records.
2. Named human steward/review and conflict-adjudication process.
3. A reviewed R2 wave with exact identity/effective-period evidence for every proposed asset.
4. An additive append-only evidence migration, guarded Registry update service, atomic idempotence, supersession, and reversal semantics.
5. Tests proving a later committed update changes only capability projection/evidence and has no identity, plan, fee, holding, transaction, or ledger effect.

## Explicit non-goals

No Registry update, evidence table, migration, commit mode, rollback execution, provider/session work, canonical plan, funding change, API/frontend work, transaction/ledger change, M31 enforcement, compatibility retirement, or ExecutionIntent work is included.

## Verification

Focused R2 tests cover frozen/deterministic evidence, strict values/time, parser checks, identity/current-projection checks, authority trust, future effectiveness, read-only candidate evidence, raw/governed coverage, zero `RegistryFinding` creation, report determinism, and explicit CLI refusal of `--commit`. Broader Registry, Definition, and M32 policy/evidence regressions are run with the implementation handoff. No production data was changed and no commit/push was performed.

Implementation verification results:

- focused R2 suite: **13 passed**;
- R2 + M31 Registry/remediation + Asset Definition + M32.3E1/E2 regression group: **102 passed**;
- Python syntax compilation and `git diff --check` passed;
- read-only development CLI preflight: 21 assets, 0 positive lots, 21 raw
  false fractional values, 0 governed evidence records, and 21
  `UNVERIFIED_DEFAULT` outcomes; and
- final read-only development query: 21 null lots, 21 false fractional values,
  0 positive lots, and `RegistryFinding=0`.

The initially selected `C:\tmp` pytest base directory was inaccessible in this
Windows environment. The same tests passed using a workspace-local
`--basetemp`; this was environmental and not a test regression.
