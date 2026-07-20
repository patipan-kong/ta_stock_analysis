# M34-WP6A - WP6 Admission Manifest

**Date:** 2026-07-19

**Status:** Corrected claim-family classification under `M34-D-0006`, pending
fresh independent architectural approval and checkpoint review. `SA27` and
`SA28` are deferred under `M34-R-0019`; `SA29` and `SA30` are narrowed under
`M34-R-0020` so that neither indirectly admits an excluded ownerless concept.
The manifest does not authorize WP6.

**Current gate:** `WP6_BLOCKED` under `M34-D-0012`. M34.1 remains NO-GO.

## 1. Admission rule

Every one of the 40 frozen WP5 claim families appears exactly once in one of
the two manifests below.

`WP6_INCLUDED` means the produced governance artifacts contain an approved
semantic boundary, one owner for each decomposed concept, and canonical
vocabulary sufficient to submit that family for independent review. It does
not mean WP6 is authorized.

`WP6_EXCLUDED` means at least one DQ-06 prerequisite remains missing. An
excluded family cannot support `READY_FOR_PORTFOLIO_HOME_SLICE` and cannot be
silently omitted from M34 readiness.

## 2. WP6_INCLUDED

| Claim family | Approved semantic owner or decomposition | Effective vocabulary basis | Permitted WP6 scope | Decision basis |
| --- | --- | --- | --- | --- |
| `SA01` | Ledger & Accounting; Portfolio Intelligence; Wealth Intelligence; Experience Platform, each for the DQ-02 concept | Portfolio Identity; Accounting Scope; Portfolio Strategy Metadata; Goal Target; Current Selection | Verify each decomposed concept independently | `M34-D-0002`, `M34-D-0006` |
| `SA02` | Ledger & Accounting for membership/aggregation; Wealth Intelligence for exposure | Portfolio Membership; Cross-Portfolio Aggregation; Cross-Portfolio Exposure | Verify decomposition and contributing-scope provenance | `M34-D-0003`, `M34-D-0006` |
| `SA05` | Ledger & Accounting | Ledger; Canonical Ledger Event | Verify transaction and ledger-event meaning | `M34-D-0006` |
| `SA07` | Market Intelligence | Market Observation; Canonical Temporal Claim | Verify observation kind, source, time, and degraded state | `M34-D-0005`, `M34-D-0010` |
| `SA11` | Asset Foundation for classification; Market Intelligence for evidence; Portfolio Intelligence for approved Analytical Grouping | Asset Classification; Market Classification Evidence; Analytical Grouping | Verify explicit kind and provenance of each sector-related value | `M34-D-0004`, `M34-D-0006` |
| `SA16` | Exactly one producing constitutional domain per temporal claim; Experience presentation only | Canonical Temporal Claim; Event Type; Producing Domain; Degraded State; Presentation Label | Verify event/source qualification and non-normative presentation labels | `M34-D-0005`, `M34-D-0006` |
| `SA17` | Ledger & Accounting for the derived historical state | Portfolio Snapshot; Derivation; Ledger | Verify snapshot meaning without promoting it over Ledger truth | `M34-D-0006` |
| `SA20` | Asset Foundation, Market Intelligence, Decision Intelligence, Trust & Evaluation, and Experience Platform under DQ-10 | Asset; Asset Classification; Market Observation; Investment Judgment; Instrument-Level Risk; Consensus; Analysis History; Evaluation | Verify each decomposed field and provenance independently | `M34-D-0001`, `M34-D-0010` |
| `SA21` | Decision Intelligence for judgment/risk/consensus/history; source domains for identity and observations | Market Observation; Investment Judgment; Instrument-Level Risk; Consensus; Analysis History; Provenance | Verify instrument judgments separately from evidence and portfolio risk | `M34-D-0010` |
| `SA25` | Portfolio Intelligence, Wealth Intelligence, and Decision Intelligence under DQ-07; Persona has no independent rule authority | Portfolio Strategy Metadata; Goal Target; Decision Policy; Portfolio Limits; Sector Limits; Persona | Verify decomposed concepts and reference-only Persona | `M34-D-0002`, `M34-D-0007` |
| `SA26` | Decision Intelligence | Recommendation Snapshot; Consensus | Verify recommendation/belief record semantics without execution or approval authority | `M34-D-0001`, `M34-D-0008` |
| `SA29` | Trust & Evaluation owns Plan-versus-Actual Comparison; Ledger & Accounting retains ownership of actual transaction facts | Plan-versus-Actual Comparison | Verify only the Trust-owned comparison boundary and its use of Ledger-owned actual facts; any Execution Detail or legacy projection field is opaque excluded evidence that WP6 must not interpret, verify, normalize, or promote | `M34-D-0008` |
| `SA30` | Decision Intelligence owns the Decision Memory concept under the claim-specific `M34-D-0001` mapping | Decision Memory | Verify only the Decision Memory reference-composition boundary and its DQ-08 non-authority; Legacy Decision Records are opaque excluded artifacts and are not verification targets or sources of decision meaning | `M34-D-0001`, `M34-D-0008` |
| `SA31` | Trust & Evaluation | Shadow Portfolio; Ideal Portfolio; AI Portfolio; Gap A; Gap B | Verify counterfactual-track distinctions and source provenance | `M34-D-0001`, `M34-D-0006` |
| `SA32` | Trust & Evaluation | Recommendation Grade; Evaluation | Verify independent belief/execution/outcome evaluation lenses | `M34-D-0001`, `M34-D-0010` |
| `SA33` | Trust & Evaluation | Gap B; Evaluation | Verify human-versus-AI comparison as evaluation, not authority | `M34-D-0001`, `M34-D-0006` |
| `SA34` | Trust & Evaluation | Opportunity Cost; Evaluation | Verify counterfactual meaning and input provenance | `M34-D-0001`, `M34-D-0006` |
| `SA38` | Experience Platform | Watchlist Membership; User Preference State; Interaction State | Verify interaction preference and all explicit non-implications | `M34-D-0011` |

### 2.1 Included-set conditions

- `SA29` and `SA30` are never admitted to positive execution, approval,
  planning, authorization, intent, or actor-attribution verification.
- `SA29` does not admit `Execution Detail`; `SA30` does not admit `Legacy
  Decision Record`. Those concepts cannot enter either family's effective
  vocabulary, semantic scope, provenance interpretation, lifecycle
  verification, or negative-guarantee verification.
- `SA27` and `SA28` remain `STOPPED_AUTHORITY` but are excluded because no
  constitutional semantic owner is currently approved for either exact
  concept.
- Every temporal dimension uses `M34-D-0005`.
- Every mixed family expands into the concepts in
  `M34_WP6A_semantic_mapping.md`; a family-level label never transfers
  ownership.
- Independent approval and a later gate remain mandatory.

## 3. WP6_EXCLUDED

| Claim family | Missing artifact or canonical coverage | Constitutional owner(s) | Remaining governance work | Readiness consequence |
| --- | --- | --- | --- | --- |
| `SA03` | No canonical Holding or Position Quantity entry | Ledger & Accounting | Approve and synchronize exact holding/quantity vocabulary | Blocks complete verification of “What do I own?” |
| `SA04` | No canonical Cash Balance or Cash Utilization entries | Ledger & Accounting for balance; Portfolio Intelligence for utilization | Approve the decomposition and both terms | Blocks complete cash and deployment meaning |
| `SA06` | No exact Cost Basis, Realized P/L, Fee, or Tax vocabulary for the claim | Ledger & Accounting | Approve and synchronize accounting terms | Blocks complete P/L and accounting-read readiness |
| `SA08` | No canonical Portfolio Value, Equity Value, or NAV term for this portfolio-derived measure | Portfolio Intelligence | Approve the valuation noun and distinguish it from market-observation NAV | Blocks “What is it worth?” readiness |
| `SA09` | No canonical Unrealized P/L term | Portfolio Intelligence | Approve its exact basis and term | Blocks complete current P/L readiness |
| `SA10` | Allocation and Concentration remain unregistered even though classification/grouping terms exist | Portfolio Intelligence | Approve allocation and concentration vocabulary | Blocks allocation and concentration correctness review |
| `SA12` | No canonical Portfolio Return or Investment Performance term | Portfolio Intelligence | Approve period, basis, and return/performance vocabulary | Blocks performance readiness |
| `SA13` | No canonical Benchmark Comparison, Alpha, Indexed Curve, or Equity Curve terms | Portfolio Intelligence; Market Intelligence owns benchmark observations | Approve derived comparison vocabulary and input boundary | Blocks benchmark-comparison readiness |
| `SA14` | External Flow, Manual Adjustment, Non-Performance Event, and decomposition vocabulary are incomplete | Ledger & Accounting for events; Portfolio Intelligence for decomposition | Approve event/decomposition distinctions and terms | Blocks explanation of non-performance changes |
| `SA15` | No canonical Portfolio Risk, Drawdown, Volatility, or Concentration terms | Portfolio Intelligence | Approve exact portfolio-risk vocabulary | Blocks risk-readiness claims |
| `SA18` | No canonical Monthly Return or quantitative-statistic vocabulary | Portfolio Intelligence | Approve metric-specific canonical terms | Blocks quantitative performance verification |
| `SA19` | No canonical Factor Exposure, Portfolio DNA, or Style Drift terms | Portfolio Intelligence | Approve exact factor-analysis vocabulary | Blocks factor-analysis readiness |
| `SA22` | No canonical Contribution or Contributor Ranking terms | Portfolio Intelligence | Distinguish contribution, P/L ranking, and attribution canonically | Blocks contributor and contribution claims |
| `SA23` | No canonical Attribution, Effect, Residual, or Unexplained Amount terms | Portfolio Intelligence | Approve the decomposition vocabulary | Blocks attribution readiness |
| `SA24` | No canonical Market Regime or Regime Attribution terms | Market Intelligence for regime observation; Portfolio Intelligence for attribution | Approve the two-concept vocabulary and provenance | Blocks regime-context and regime-attribution readiness |
| `SA27` | No explicitly approved constitutional semantic owner for the exact Execution Plan Projection concept; `STOPPED_AUTHORITY` is a classification, not an owner | `UNKNOWN_OWNERSHIP` | Retain every DQ-08 negative guarantee and obtain a separate approved owner designation before any future admission | Admission is premature; blocks SA27 semantic verification while preserving non-authority |
| `SA28` | No explicitly approved constitutional semantic owner for the exact Legacy Decision Record concept; `STOPPED_AUTHORITY` is a classification, not an owner | `UNKNOWN_OWNERSHIP` | Retain every DQ-08 negative guarantee and obtain a separate approved owner designation before any future admission | Admission is premature; blocks SA28 semantic verification while preserving non-authority |
| `SA35` | No canonical Confidence Calibration term | Trust & Evaluation | Approve calibration vocabulary and its judged input boundary | Blocks calibration readiness |
| `SA36` | Station Health, Committee Status, and Translation Status lack concrete constitutional-domain bindings for their current instances | One responsible producing constitutional domain per concrete status | Name and approve each concrete owner binding; retain DQ-05 provenance | Blocks complete Operations Center semantic readiness |
| `SA37` | No canonical Trust Report or Verdict term; operational/evaluative split is not fully registered | Trust & Evaluation for evaluation; source domains for operational inputs | Approve trust-report/verdict vocabulary and source-status boundary | Blocks trust-summary readiness |
| `SA39` | Concrete Model Selection and Analysis Source Selection settings lack producing/consuming domain bindings | One producing or consuming constitutional domain per concrete setting | Publish the exhaustive setting-to-domain binding | Blocks Settings semantic readiness |
| `SA40` | No approved term-by-term System Guide synchronization manifest | Experience Platform for presentation; every described concept retains its source owner | Map every governed guide term to the effective Glossary and owner | Blocks using the Guide as synchronized trust evidence |

## 4. Coverage proof

```text
WP5 claim families:  40
WP6_INCLUDED:        18
WP6_EXCLUDED:        22
Unaccounted:          0
Duplicated:           0
Currently authorized: 0
```

The readiness consequence of every exclusion is blocking for a full M34
product-readiness conclusion in its affected question or surface. No excluded
family may support `READY_FOR_PORTFOLIO_HOME_SLICE` unless a later ARB ruling
expressly changes that consequence after the missing governance is completed.

## 5. Traceability

- Admission policy: `M34-D-0006`.
- Current gate: `M34-D-0012`.
- Claim-owner interpretation:
  `M34_WP6A_DQ01_claim_family_owner_mapping.md`.
- Decomposition and provenance: `M34_WP6A_semantic_mapping.md`.
- Vocabulary synchronization:
  `M34_WP6A_vocabulary_synchronization.md`.
- Canonical terms: `docs/GLOSSARY.md`.
- Bounded SA27/SA28 admission correction: `M34-R-0019`.
- Bounded SA29/SA30 semantic-containment correction: `M34-R-0020`.
- Frozen claim population: WP5 `SA01` through `SA40`, supported by
  `M34-E-0048` through `M34-E-0050`.

## 6. Non-authorization statement

This manifest does not approve itself, authorize full or partial WP6, change
an M34 exit, authorize M34.1, or permit implementation or runtime work.
Independent Review Log approval and a checkpoint are still required. M32 and
M33 remain closed.
