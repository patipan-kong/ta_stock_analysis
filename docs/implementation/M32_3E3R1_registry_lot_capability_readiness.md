# M32.3E3R1 — Registry Lot Capability Governance Audit and Remediation Design

**Audit date:** 2026-07-15

**Decision:** **NO-GO for applying any lot or fractional-capability update.**
The repository and configured development Registry contain no authoritative,
capability-specific source for any of the 21 current assets. A narrowly scoped
preflight/evidence-governance implementation may proceed; commit capability
must remain unavailable until external authoritative records are supplied and
human-adjudicated.

**Scope:** Audit and design only. No Registry row, provider, execution plan,
transaction, fee, API, frontend, migration, or production behavior was
changed. Database queries were read-only and sessions were rolled back. No
commit or push was performed.

## 1. Executive summary

The current schema has the right projection fields but not a governed update
path:

- `Asset.lot_size` is nullable and all 21 development assets contain `None`.
  Raw positive-lot coverage is therefore **0/21 (0.0%)**.
- `Asset.fractional_support` is `False` on all 21 rows, but those values were
  produced by `AssetClaim`'s default during ledger bootstrap. Neither the
  Asset row nor its bootstrap checkpoint names a fractional-capability source.
  Raw value coverage is 21/21, but **governed evidence coverage is 0/21**.
- Every asset has exactly one current `PROVIDER_SYMBOL` identifier sourced as
  `ledger:historical` and one successful bootstrap checkpoint. That evidence
  supports the stored spelling/bootstrap history; it says nothing about board
  lots or fractional execution.
- All observed holding and executable-transaction quantities are integral and
  most are multiples of 100. They are records of what users or legacy paths
  entered, not proof of what the venue permits. Native `asset_id` is also null
  on the measured operational rows, so the quantity inventory is an exact
  symbol join rather than identity-bound capability evidence.
- Yahoo Chart and the repository's provider DTOs expose price, time, session,
  currency, venue-like descriptive metadata, and identifiers. They expose no
  reviewed lot-size or fractional-order capability.
- The Asset Definition Runtime permits Equity instances to declare lot and
  fractional refinements. It does not supply the value. Permission to refine
  is not evidence of a particular refinement.
- M31.5/M31.6 remediation can set `lot_size` and `fractional_support` while
  minting, but it cannot update an existing Asset's instance facts. Its
  manifest has only source/note/approval fields, and it does not persist an
  append-only capability evidence record or rollback chain.

No subset can be remediated safely now. The common SET/THB/EQUITY shape does
not authorize a blanket rule, and no symbol, quantity pattern, provider
payload, or general market convention may fill the gap.

The recommended next milestone is a read-only evidence/preflight foundation,
followed—only after governance approval—by an append-only capability-evidence
record and an atomic Registry projection update. External authoritative input
and named human review are required before the first commit-enabled manifest.

## 2. Semantic definition of `lot_size`

### 2.1 Authoritative meaning

For the current listing-based Asset identity, `Asset.lot_size` should mean:

> The positive integer quantity increment, expressed in the Asset's Registry
> unit, required for an order in the listing's standard execution venue/order
> book for the stated effective period.

For the current Equity assets, the Registry unit is one share. A value of 100
would therefore mean standard-board quantities must be integer multiples of
100 shares. The value is an instance fact attached to `asset_id`, not an
AssetType default and not a symbol rule.

This definition matches the behavior of M32.3E1: derived quantities are
floored to a multiple of `lot_size`, and a full liquidation that is not
aligned remains exceptional rather than silently rounded. It also narrows the
architecture's earlier phrase “minimum tradable/transactable increment” to
the step/increment semantics the implementation actually consumes.

### 2.2 What it does not mean

| Candidate meaning | Decision | Reason |
| --- | --- | --- |
| Exchange board lot | **Yes, with scope.** | This is the intended standard-venue/listing increment when an authoritative per-listing source supplies it. |
| Broker order increment | **No.** | Broker/channel restrictions can be stricter or support alternate order types. They belong to a future Broker/Execution capability contract, not the provider-independent Asset fact. |
| Minimum trade quantity | **No.** | A minimum and a step are different constraints. One order may require `minimum_quantity=100` while increments above it differ. The current scalar is consumed as a step. |
| Settlement unit | **No.** | Settlement denomination/cycle is a separate post-trade fact. It must not be inferred from order-entry constraints. |
| Execution-policy lot | **No.** | Policy may consume the Registry increment and impose stricter rules, but must not write its judgment back as an Asset fact. |

Odd-lot or alternate-board trading exposes a limitation of the scalar field:
one listing can have more than one valid execution channel. M32 v1 is scoped
to the standard board. Evidence that describes only an odd-lot board, a
broker's internal fractional service, or a conditional order type cannot
populate `Asset.lot_size`. A listing with mixed/variable rules remains
quarantined until a structured venue/order-capability contract exists.

### 2.3 Meaning of `fractional_support`

`Asset.fractional_support` is the Registry's instance fact that quantities of
the Asset may be represented/transacted as non-integer Registry units. It is
not proof that the currently selected broker accepts a fractional order.

The Equity definition says fractional refinement is permitted; it does not say
an individual listing is fractional. A broker's fractional-share service is a
channel capability and would require separate execution evidence. For M32 v1,
only an explicitly evidenced `fractional_support=False` is accepted. A default
`False`, missing source, conflicting source, or provider/broker-only claim is
incomplete.

### 2.4 Ownership boundary

```text
Official listing/venue instrument evidence
        -> Registry steward adjudication
        -> Asset capability evidence history
        -> Asset.lot_size / fractional_support current projection
        -> ExecutionInstrumentFacts
        -> Execution policy judgment

Broker/channel restrictions ---------------------> future execution capability
Asset Definition refinement permission ----------> validation only
Historical holdings/transactions ----------------> review evidence only
```

The Registry describes the listing-level fact. Asset Definitions validate
that the bound kind permits the refinement. Execution Policy decides how to
use it. Providers and brokers are witnesses, not Registry authority.

## 3. Current 21-asset coverage

### 3.1 Database result

| Check | Result |
| --- | ---: |
| Current Assets | 21 |
| Active / tradable | 21 / 21 |
| Asset type | 21 EQUITY |
| Market / exchange / currency | 21 Thailand / SET / THB |
| Positive integer `lot_size` | 0 / 21 (0.0%) |
| `lot_size=None` | 21 / 21 (100.0%) |
| Raw `fractional_support=False` | 21 / 21 (100.0%) |
| Fractional value with capability-specific provenance | 0 / 21 (0.0%) |
| Current identifiers | 21 `PROVIDER_SYMBOL`; one per asset |
| Identifier source | 21 `ledger:historical` |
| Capability evidence rows | No model/table exists |
| Relationships / classifications relevant to lot | 0 |

All 21 assets were minted in bootstrap run
`f75cce7e-513c-44ca-b799-5d94a4b27260` on 2026-07-09. The bootstrap planner
constructs `AssetClaim` without lot/fraction arguments, so it receives
`fractional_support=False` and `lot_size=None` from dataclass defaults. The
checkpoint records the identity mint result and identifier count, not the
authority for those capability values.

### 3.2 Interpretation

- **Lot readiness:** 0/21.
- **Fractional semantic readiness:** 0/21 despite the 21 stored false values.
- **Automatic remediation readiness:** 0/21.
- **Potential batch scope after external review:** possibly all or a subset,
  but only if an approved authority explicitly covers each named listing and
  its effective period. “All are SET” is not itself such evidence.

`lot_size=None` remains incomplete. It cannot mean one, no constraint, or an
unknown-but-probably-standard board lot. Likewise, the existing `False`
cannot be promoted from a bootstrap default to verified capability evidence
without adjudication.

## 4. Evidence-source inventory

| Source | Present now | What it establishes | Lot/fraction authority | Disposition |
| --- | --- | --- | --- | --- |
| `Asset` current fields | Yes | Current Registry projection | None: source/version/reviewer absent | Gap to remediate, not evidence |
| Asset identifiers | One current `PROVIDER_SYMBOL` per asset, source `ledger:historical` | Stored symbol evidence | No | Retain only for joining/adjudication |
| Bootstrap checkpoint | One MINTED row per asset | Mint attempt, raw/canonical symbol, currency | No | Audit provenance only |
| Asset classifications/relationships | None relevant | Sector/index/identity links when present | No lot dimension exists | Not a capability write path |
| Asset Definition Equity v1 | Present | Discrete units; lot/fraction refinements are permitted | No value | Validation gate only |
| Market/exchange strings | `Thailand` / `SET` on all assets | Current Registry listing description | No per-listing rule/effective record | Cannot derive a blanket lot |
| Yahoo Chart / yfinance | Live price/quote metadata; no lot field | Market observations and descriptive provider metadata | No | Must not be extended into a lot heuristic |
| Holdings | 19/21 assets have current exact-symbol rows | Current ledger-derived quantity | No | Candidate review evidence only |
| BUY/SELL/INITIAL_POSITION history | All 21 have at least one exact-symbol row; all quantities integral | Previously accepted input quantities | No | Cannot prove minimum or increment |
| Frontend precision / transaction schema | Float quantities, UI/storage conventions | Representation accepted by legacy software | No | Explicitly prohibited inference |
| M31.5 remediation manifest | Present | Approved identity-oriented mint/link/classification instructions | Insufficient for existing capability updates | Extend with a separate operation/contract |
| M31.6 wave dossier | Present | Exact-match identity and operational review evidence | No | Reuse the quarantine discipline, not its identity operations |
| Official exchange instrument/security master | Not present in repository/database | Candidate per-listing standard-board rules | **Potentially authoritative** after review | Required external input |
| Issuer/listing notice changing board lot | Not present | Candidate dated exception/change evidence | **Potentially authoritative** after review | Required for exceptions/supersession |
| Broker capability/order-rule feed | Not integrated | Channel-specific accepted order increments/fractional service | Broker authority only | Future Execution/Broker capability, not Registry lot source |

An acceptable external source must identify the listing decisively—preferably
through a stable official identifier as well as symbol—state the quantity
unit and standard-board increment, state fractional eligibility or explicitly
exclude it, include an effective date/version, and be attributable to the
exchange, issuer/listing authority, or another governance-approved official
instrument master. General educational pages or undocumented “common market
knowledge” are insufficient.

## 5. Asset-by-asset readiness table

Common facts for every row below:

- asset type `EQUITY`, status `ACTIVE`, tradable `true`;
- listing `Thailand / SET / THB`;
- current identifier type `PROVIDER_SYMBOL`, current `true`, source
  `ledger:historical`;
- `lot_size=None`, raw `fractional_support=false`;
- no capability-specific authority or evidence version/date;
- automatic remediation **No**;
- human adjudication requires the fields in §7.3.

`H` is the current exact-symbol holding quantity; `T` is the distinct
historical executable transaction quantity set. These are candidate-only
observations, not authority. Operational rows have null native `asset_id` and
were joined through the exact current Registry identifier.

| Asset ID | Canonical symbol | Current identifier | Market / exchange / currency | Current lot / fractional | Authoritative capability evidence | Candidate evidence requiring review | Auto-safe | Human disposition |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 22 | `AAPL01.BK` | `AAPL01.BK` | Thailand / SET / THB | `None` / `false` | None | H 1,600; T 100, 500, 1,000 | No | Obtain listing-bound official lot/fraction record; review wrapper/listing scope without inferring from symbol |
| 23 | `ADVANC.BK` | `ADVANC.BK` | Thailand / SET / THB | `None` / `false` | None | H 100; T 100 | No | Obtain listing-bound official record |
| 24 | `AMZN01.BK` | `AMZN01.BK` | Thailand / SET / THB | `None` / `false` | None | H 1,500; T 300, 500, 700, 1,000 | No | Obtain listing-bound official lot/fraction record; review wrapper/listing scope without inferring from symbol |
| 25 | `AMZON01` | `AMZON01` | Thailand / SET / THB | `None` / `false` | None | H —; T 500 | No | First confirm evidence addresses this exact listing/spelling; then adjudicate lot/fraction |
| 26 | `AOT.BK` | `AOT.BK` | Thailand / SET / THB | `None` / `false` | None | H 5,000; T 5,000 | No | Obtain listing-bound official record |
| 27 | `BANPU.BK` | `BANPU.BK` | Thailand / SET / THB | `None` / `false` | None | H 6,700; T 6,700 | No | Obtain listing-bound official record |
| 28 | `BDMS.BK` | `BDMS.BK` | Thailand / SET / THB | `None` / `false` | None | H 7,800; T 7,800 | No | Obtain listing-bound official record |
| 29 | `BH.BK` | `BH.BK` | Thailand / SET / THB | `None` / `false` | None | H 600; T 100, 500 | No | Obtain listing-bound official record |
| 30 | `CPALL.BK` | `CPALL.BK` | Thailand / SET / THB | `None` / `false` | None | H 300; T 300 | No | Obtain listing-bound official record |
| 31 | `ICHI.BK` | `ICHI.BK` | Thailand / SET / THB | `None` / `false` | None | H 3,000; T 3,000 | No | Obtain listing-bound official record |
| 32 | `KBANK.BK` | `KBANK.BK` | Thailand / SET / THB | `None` / `false` | None | H 700; T 100, 800 | No | Obtain listing-bound official record |
| 33 | `KGI.BK` | `KGI.BK` | Thailand / SET / THB | `None` / `false` | None | H 5,000; T 5,000 | No | Obtain listing-bound official record |
| 34 | `META01.BK` | `META01.BK` | Thailand / SET / THB | `None` / `false` | None | H 4,000; T 4,000 | No | Obtain listing-bound official lot/fraction record; review wrapper/listing scope without inferring from symbol |
| 35 | `MICRON.BK` | `MICRON.BK` | Thailand / SET / THB | `None` / `false` | None | H —; T 1,000 | No | Obtain record for this exact listing; do not transfer evidence from asset 36 |
| 36 | `MICRON01.BK` | `MICRON01.BK` | Thailand / SET / THB | `None` / `false` | None | H 3,000; T 1,000 | No | Obtain record for this exact listing; do not transfer evidence from asset 35 or infer wrapper form |
| 37 | `NVDA01.BK` | `NVDA01.BK` | Thailand / SET / THB | `None` / `false` | None | H 3,500; T 500, 1,000 | No | Obtain listing-bound official lot/fraction record; review wrapper/listing scope without inferring from symbol |
| 38 | `OR.BK` | `OR.BK` | Thailand / SET / THB | `None` / `false` | None | H 3,100; T 3,100 | No | Obtain listing-bound official record |
| 39 | `PIS.BK` | `PIS.BK` | Thailand / SET / THB | `None` / `false` | None | H 85,000; T 85,000 | No | Obtain listing-bound official record |
| 40 | `SCB.BK` | `SCB.BK` | Thailand / SET / THB | `None` / `false` | None | H 2,300; T 300, 400, 1,300, 2,300 | No | Obtain listing-bound official record |
| 41 | `TOA.BK` | `TOA.BK` | Thailand / SET / THB | `None` / `false` | None | H 1,000; T 1,000 | No | Obtain listing-bound official record |
| 42 | `TOP.BK` | `TOP.BK` | Thailand / SET / THB | `None` / `false` | None | H 100; T 100 | No | Obtain listing-bound official record |

The transaction sample is compatible with several possible increments (for
example 1, 10, 50, or 100 in many rows). A greatest-common-divisor or minimum
observed quantity would only describe this sample. It cannot decide the
exchange rule and is therefore deliberately absent from the proposed write
logic.

## 6. Safe versus unsafe remediation categories

### Safe only after evidence arrives

| Category | Conditions | Result |
| --- | --- | --- |
| `VERIFIED_PER_LISTING` | One approved authoritative record decisively identifies one `asset_id`, unit, standard-board increment, fractional state, effective time, and source version | Eligible for reviewed manifest instruction |
| `VERIFIED_AUTHORITY_BATCH` | One signed/versioned authority dataset explicitly enumerates every included listing and capability value | Each row still becomes its own instruction/evidence record; no market-level derivation |
| `ALREADY_CURRENT_AND_EVIDENCED` | Current projection equals the approved evidence and its evidence record exists | Idempotent `ALREADY_APPLIED`; no Asset mutation |
| `APPROVED_SUPERSESSION` | Newer authoritative record explicitly changes an existing value with effective date | Append new evidence, supersede prior evidence, update current projection atomically |

### Unsafe and quarantined

- AssetType-, `.BK`-, exchange-name-, currency-, broker-convention-, symbol-,
  prefix-, suffix-, or numeric-pattern derivation.
- `lot_size=None => 1`, `fractional_support missing => false`, or a blanket
  `SET => 100` rule not backed by an approved authority that explicitly covers
  every included listing.
- Inferring a lot from holdings, transaction quantities, UI precision,
  storage precision, fee schedule, historical successful writes, or provider
  price payloads.
- Transferring evidence between apparently related symbols or assets, such as
  `MICRON.BK` and `MICRON01.BK`.
- Treating the Asset Definition's “permits refinement” as the refinement value.
- Using a broker's channel rule as the provider-independent listing fact.
- Applying a source whose unit, execution board, identity, effective period,
  or authority is missing.
- Applying mixed or conflicting sources. The asset receives
  `QUARANTINED_CONFLICT`; no “highest confidence wins” automation is allowed.

## 7. Manifest and evidence design

### 7.1 Why existing tooling is insufficient

`execution_registry_remediation.py` supports mint, attach identifier, link DR,
and register index-reference operations. It has no update operation for
existing universal fields, and `asset_repository.py` has no guarded capability
update. Its version-1 manifest records only a general evidence source/note and
approval boolean. After a commit, the database retains only the projected
values and `Asset.updated_at`; it cannot answer which source/version/reviewer
authorized them or what exact prior capability state should be restored.

Classifications are not a safe substitute. `lot_size` and
`fractional_support` are load-bearing universal instance facts, not taxonomy
values, and `ClassificationDimension` has no lot/fraction dimension.

### 7.2 `LotCapabilityEvidence` contract

A frozen versioned contract should be the input to preflight and the durable
record of an accepted decision:

```text
LotCapabilityEvidence
  contract_version
  evidence_ref                       # deterministic content hash
  asset_id
  registry_identity_snapshot         # canonical symbol + current identifiers
  unit                               # e.g. SHARE
  scope                              # STANDARD_BOARD_EXECUTION
  lot_semantics                      # QUANTITY_INCREMENT
  lot_size                           # positive integer; None remains incomplete
  fractional_support                # explicit boolean, never defaulted
  source_id
  source_type                        # EXCHANGE_MASTER / LISTING_NOTICE / approved equivalent
  source_locator
  source_record_key
  source_version
  source_published_at
  source_retrieved_at
  authority
  confidence                         # VERIFIED / CONFLICTED / INSUFFICIENT
  effective_from
  effective_to
  provenance                         # bounded source/checksum/transform chain
  reviewed_by
  reviewed_at
  approval_state                     # DRAFT / APPROVED / REJECTED / QUARANTINED
  approval_note
  supersedes_evidence_ref
  rollback_of_evidence_ref
```

`confidence=VERIFIED` and `approval_state=APPROVED` are both required for a
projection update. Confidence describes the evidence; approval describes the
governance decision. Neither implies the other.

### 7.3 Manifest instruction

```json
{
  "manifest_version": 1,
  "manifest_id": "m32-3e3r2-set-lot-wave-1",
  "instructions": [
    {
      "instruction_id": "lot-asset-32-v1",
      "operation": "UPDATE_LOT_CAPABILITY",
      "asset_id": 32,
      "expected_current": {
        "canonical_symbol": "KBANK.BK",
        "lot_size": null,
        "fractional_support": false,
        "asset_updated_at": "<exact Registry value>"
      },
      "proposed": {
        "unit": "SHARE",
        "scope": "STANDARD_BOARD_EXECUTION",
        "lot_semantics": "QUANTITY_INCREMENT",
        "lot_size": "<authoritative positive integer>",
        "fractional_support": "<authoritative boolean>",
        "effective_from": "<source effective time>"
      },
      "evidence": {
        "source_id": "<governed source id>",
        "source_type": "EXCHANGE_MASTER",
        "source_locator": "<document or dataset locator>",
        "source_record_key": "<exact listing record>",
        "source_version": "<version/date>",
        "source_published_at": "<timestamp>",
        "source_retrieved_at": "<timestamp>",
        "authority": "<issuing authority>",
        "confidence": "VERIFIED",
        "provenance": ["<checksum>", "<reviewed extraction description>"]
      },
      "review": {
        "reviewed_by": "<named steward>",
        "reviewed_at": "<timestamp>",
        "approval_state": "APPROVED",
        "approval_note": "<why this exact record governs this asset>"
      },
      "rollback": {
        "prior_lot_size": null,
        "prior_fractional_support": false,
        "implication": "M32 live evidence becomes incomplete again; no ledger or plan row changes"
      }
    }
  ]
}
```

Strings are shown for proposed values only to emphasize that the manifest must
require explicit presence; the parser should produce typed integer/boolean
values and reject coercive values such as `"yes"`, `0`, negative numbers, or
omitted booleans.

Every instruction requires the user-requested fields: `asset_id`, `lot_size`,
`fractional_support`, evidence source/version/date, authority, confidence,
reviewer/approval, provenance, effective time, and rollback snapshot.

### 7.4 Durable provenance and schema implication

A migration is not required for the read-only collector, contract parser, or
dry-run validator. It **is required before commit capability** if the Registry
is to preserve the requested provenance and rollback chain inside its own
authority boundary.

The minimum additive table is an append-only
`asset_lot_capability_evidence` record containing the contract fields above,
prior projected values, `manifest_id`, `instruction_id`, `recorded_at`, and a
unique `(manifest_id, instruction_id)` key. `Asset.lot_size` and
`fractional_support` remain the current fast read projection. One Registry
service transaction appends evidence and updates only those two columns.

This avoids overloading classifications and avoids making a checked-in JSON
file the only explanation for live database state. If governance explicitly
accepts a repository manifest plus immutable deployment artifact as the
durable record, the table could be deferred, but that would weaken the
Registry's ability to explain environment-specific state and is not
recommended.

## 8. Read-only preflight, dry-run, commit, and rollback governance

### Read-only preflight (default)

1. Load Assets, current/historical identifiers, current capability projection,
   Asset Definition refinement permissions, and accepted capability evidence.
2. Report raw coverage separately from governed-evidence coverage.
3. Collect holdings/transactions only into a clearly labeled candidate-evidence
   section; never calculate or propose a lot from them.
4. Match external records by explicit identifiers/record keys. Do not strip
   suffixes or generate aliases.
5. Emit one of `READY`, `MISSING_EVIDENCE`, `UNVERIFIED_DEFAULT`,
   `IDENTITY_MISMATCH`, `CONFLICT`, `STALE_SOURCE`, `INVALID_VALUE`, or
   `DEFINITION_REFINEMENT_NOT_PERMITTED`.
6. Leave conflicting/mixed evidence in quarantine and emit no approved
   instruction.

### Manifest dry-run

- Dry-run is the default; `--commit` without `--manifest` is rejected.
- Parse all required fields strictly and verify source checksums/record locators.
- Resolve by `asset_id`, then compare the exact identity snapshot and
  `expected_current` projection to prevent stale-review application.
- Require a positive integer lot and explicit boolean fractional value.
- Ask the Asset Definition Runtime only whether the instance refinements are
  permitted. It does not choose values.
- Detect overlapping effective periods, conflicting accepted evidence, future
  effective records, duplicate instructions, and different instructions for
  one asset.
- Execute the same service path in a nested transaction, render the before/
  after/evidence result, invalidate no durable state, and roll back.

### Commit

- Commit remains disabled until the evidence table/service and tests exist.
- Later, require explicit `--commit`, an approved manifest, and all-or-nothing
  validation before the first mutation.
- Lock/check each Asset against `expected_current`; a concurrent change aborts
  the entire manifest.
- Atomically append evidence and update only `lot_size`,
  `fractional_support`, and `updated_at` through the Registry service.
- Do not touch canonical/display identity, identifiers, type, market,
  exchange, currency, tradability, fees, holdings, transactions, plans, or
  histories.
- Invalidate the Registry read cache after successful commit.
- Reapplying the same manifest returns `ALREADY_APPLIED`. Same values with a
  different/unrecorded authority are not silently considered applied; the
  evidence decision must be appended or quarantined explicitly.

### Rollback

Rollback is a new approved `REVERT_LOT_CAPABILITY` instruction referencing the
accepted evidence record. It appends a reversal record and restores that
record's exact prior projection; it never deletes evidence or rewrites ledger
history. For the current assets the prior projection would be
`lot_size=None`, `fractional_support=False`. The operational implication is
that M32 capability readiness returns to incomplete. No data migration of
plans or transactions is needed because none stores or consumes an
authoritative lot snapshot today.

Future-effective evidence must be staged, not projected early. Expired or
superseded evidence must never be selected by “latest row wins” without an
explicit effective-period rule.

## 9. Tests required

### Contract and parser

- Frozen, deterministic `LotCapabilityEvidence` and content reference.
- Every required source, authority, review, provenance, effective, and
  rollback field is mandatory.
- Reject missing/implicit boolean, `None`, zero, negative, non-integral lot,
  unsupported unit/scope/semantics, naive or invalid times, invalid confidence,
  and unapproved instructions.
- Reject duplicate instruction/evidence references and overlapping effective
  periods.

### Negative authority tests

- AssetType, SET/exchange, `.BK`, numeric suffix, symbol regex, broker
  convention, frontend precision, holding quantity, transaction GCD/minimum,
  fee profile, provider price metadata, or Definition refinement permission
  cannot produce a manifest update.
- No `None => 1` and no missing fractional value => `False` path exists.
- Evidence for one `asset_id` cannot update a similar symbol/relationship.
- Mixed/conflicting evidence yields quarantine and no mutation.

### Preflight and database tests

- Read-only report distinguishes raw and governed coverage.
- All 21 current assets report `MISSING_EVIDENCE`/`UNVERIFIED_DEFAULT` against
  the captured development fixture.
- Resolver/query is batch-safe and does not create Registry findings.
- Dry-run uses the exact commit path, rolls back projection/evidence rows, and
  invalidates no unrelated state.
- Commit is all-or-nothing, guarded by exact expected current values, and
  writes only capability projection plus one evidence record.
- Reapplication is idempotent; conflicting reapplication fails.
- Supersession and rollback append evidence and restore exact prior values.
- Asset Definition permission is enforced for both lot and fractional
  refinements without letting Definitions supply a value.

### Regression boundaries

- ExecutionInstrumentFacts projects the accepted values without heuristics.
- Missing evidence remains incomplete in M32.3E2/E1.
- Identity, eligibility, fee quotes, legacy execution plans, funding,
  transactions, ledger/replay, APIs, and frontend payloads remain unchanged.
- Registry cache invalidation occurs only after a real commit.
- Static tests prove no ticker/suffix/exchange/quantity classifier exists in
  the collector, parser, validator, or updater.

## 10. Go / No-Go recommendation

| Decision | Result | Evidence |
| --- | --- | --- |
| Apply lot updates to any current asset now | **NO-GO** | 0/21 authoritative lot evidence |
| Treat current `fractional_support=False` as governed | **NO-GO** | 21 values came from bootstrap defaults; 0 capability-specific provenance records |
| Apply blanket SET lot | **NO-GO** | Market/exchange strings do not constitute per-listing/effective authority |
| Infer from holdings/transactions | **NO-GO** | Observations cannot prove permitted minimum/increment and are not natively identity-bound |
| Implement read-only contract/preflight | **GO** | Additive and incapable of changing runtime state |
| Implement commit-enabled remediation immediately | **NO-GO** | No external evidence; no existing update service or durable evidence history |
| Begin human/external evidence collection | **GO** | Required to unblock every asset |

No subset can be safely remediated now. Even assets with observed 100-share
transactions do not carry evidence that 100 is the valid standard-board
increment, and assets with larger quantities do not establish whether smaller
quantities are permitted.

## 11. Exact blockers to applying updates

1. No official per-listing lot/fraction dataset or reviewed listing notice is
   present for any of the 21 assets.
2. The current false fractional values are unproven bootstrap defaults.
3. `Asset` has no capability-specific source, version, authority, confidence,
   reviewer, effective-period, or prior-value history.
4. Existing Registry remediation cannot update existing universal fields.
5. Existing Registry service/repository has no guarded instance-fact update.
6. The promised Asset Definition validation at instance-fact update is not
   implemented; current mint enforcement only consults the binding and does
   not validate these values.
7. The single integer `lot_size` cannot represent multiple boards/order types;
   evidence must explicitly match the standard-board v1 scope.
8. Provider payloads do not expose governed lot/fraction capability.
9. Operational rows have null native `asset_id`; exact-symbol joins are useful
   for review but weaker than identity-bound evidence.
10. No approved authority trust list, source-version/checksum procedure, named
    Registry steward, or conflict-adjudication record exists for this fact.
11. No append-only projection-update/rollback evidence mechanism exists.
12. M32 also remains independently blocked by provider session evidence and
    the other M32.3E3 canonical-plan gates; lot remediation alone would not
    authorize canonical planning.

Human/external authoritative input is therefore required for every current
asset. At minimum, adjudication must provide: exact `asset_id`/listing record,
unit, standard-board increment, explicit fractional state, official source and
record key, authority, version/published/retrieved dates, effective period,
confidence, source checksum/provenance, named reviewer, approval time/state,
and rollback acknowledgment.

## 12. Recommended implementation milestone

Proceed with **M32.3E3R2 — Lot Capability Evidence and Read-only Preflight**:

1. Add the immutable `LotCapabilityEvidence` and strict manifest parser.
2. Add a read-only collector covering Assets, identifiers, Definition
   refinement permission, current projections, external supplied evidence,
   and separately labeled operational candidate evidence.
3. Add conflict/quarantine rules and deterministic JSON reporting.
4. Add dry-run validation with no commit branch and no production consumer.
5. Establish the approved authority/source-record/checksum and steward-review
   procedure, then collect evidence for a small reviewed wave.

Only after that wave is approved should **M32.3E3R3 — Governed Capability
Projection Update** add the strictly required append-only evidence migration,
Registry service update, explicit commit mode, idempotence, supersession, and
rollback. M32.3E2 must continue treating missing/unverified lots as incomplete
throughout. M32.3E4 remains NO-GO until its independent readiness gates pass.

## Verification record

### Repository audit

Audited:

- `backend/models/asset.py` and the Registry foundation migration;
- `backend/services/asset_domain.py`, `asset_registry.py`,
  `asset_repository.py`, `registry_service.py`, `registry_lookup.py`, and
  `execution_instrument_facts.py`;
- Registry bootstrap/planner/checkpoint and symbol-market convention paths;
- M31.5 remediation/preflight and M31.6 evidence-wave tooling/manifests;
- Asset Definition vocabulary, Equity v1 declaration, runtime capability
  projection, and instance-refinement design;
- Yahoo Chart/yfinance provider DTOs, quote-envelope adapters, and market
  cache ownership;
- holdings, transaction schema, M32.3E1 quantity policy, and M32.3E2
  capability readiness;
- Registry/Asset Foundation architecture and provenance/adjudication rules;
  and
- repository-wide instrument-master, board-lot, order-increment, and
  fractional-capability configuration searches.

No existing instrument/security master or lot-size configuration was found.

### Development database

Read-only rolled-back queries enumerated all 21 Assets, identifiers,
classifications, relationships, bootstrap/migration checkpoints, current
holdings, and BUY/SELL/INITIAL_POSITION quantities. The exact coverage and
asset-level observations are reported above. No Registry or operational row
was changed. A final corrected ORM query (with the Registry `Asset` mapper
loaded) reported `RegistryFinding count=0`.

### Tests and repository checks

The focused Registry/remediation, Asset Definition, M32.3E1 policy, and
M32.3E2 live-evidence group completed with **89 passed** and no failures:

```text
tests/test_execution_registry_preparation_m31_5.py
tests/test_execution_registry_remediation_m31_6.py
tests/test_asset_definitions_conformance.py
tests/test_asset_registry.py
tests/test_execution_policy_m32_3e1.py
tests/test_execution_live_evidence_m32_3e2.py
```

Warnings were existing SQLAlchemy/datetime deprecations and an inaccessible
pytest cache path. `git diff --check` passed for tracked state; explicit
no-index whitespace checks passed for both untracked M32.3E3 documents, and
the new R1 document has no trailing whitespace. No production code or data was
changed. No commit or push was performed.
