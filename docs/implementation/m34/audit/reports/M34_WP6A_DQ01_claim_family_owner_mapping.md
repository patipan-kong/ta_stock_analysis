# M34-WP6A - DQ-01 Claim-Family Owner Mapping

**Date:** 2026-07-19

**Status:** Complete and canonical for interpretation of the frozen WP1 audit
labels in M34. This artifact implements `M34-D-0001`; it does not amend WP1,
rename a domain, or make an audit label a constitutional alias.

**Current gate:** WP6 remains unauthorized under `M34-D-0012`. M34.1 remains
NO-GO.

## 1. Authority and mapping rule

This mapping is governed by `M34-D-0001` and the later, more specific
decomposition rulings `M34-D-0002` through `M34-D-0011`.

The mapping unit is the semantic concept for which WP5 recorded a
`PROVISIONAL_MAPPING`. Each row has exactly one constitutional semantic owner.
When a frozen claim-family label groups independently owned inputs,
evaluations, or presentation, the row maps only the identified concept and
references the approved decomposition. It never appoints one owner over a
grouped response that the ARB decomposed.

The frozen WP1 labels remain corpus and audit classifications only:

- `PORTFOLIO` is not a constitutional domain;
- `ANALYTICS` is not a universal alias for Portfolio Intelligence;
- `PORTFOLIO_INTELLIGENCE` is not a universal alias for either Portfolio
  Intelligence or Decision Intelligence;
- `AI_EVALUATION` is not a universal alias for Trust & Evaluation;
- `MARKET_DATA` is not a universal alias for Market Intelligence outside the
  exact mapped concept; and
- `EXPERIENCE` does not acquire business truth through composition.

## 2. Canonical claim-family mapping

| Claim family | Frozen WP1 candidate label(s) | Mapped semantic concept | Constitutional owner | Mapping boundary and required decomposition |
| --- | --- | --- | --- | --- |
| `SA08` | Portfolio | Portfolio equity value and total value/NAV | Portfolio Intelligence | Ledger & Accounting facts and Market Intelligence observations remain inputs; see `M34-D-0002`. |
| `SA09` | Portfolio / Analytics | Unrealized P/L | Portfolio Intelligence | Ledger & Accounting owns cost/quantity facts; Market Intelligence owns price observations. |
| `SA10` | Portfolio / Analytics | Allocation, sector allocation, and concentration as portfolio-derived measures | Portfolio Intelligence | Asset Foundation classification and any DQ-04 Analytical Grouping retain their separate authority under `M34-D-0004`. |
| `SA12` | Analytics | Portfolio return and investment performance | Portfolio Intelligence | Ledger & Accounting owns accounting inputs; Market Intelligence owns observations. |
| `SA13` | Analytics | Benchmark comparison, alpha, and indexed/equity curves | Portfolio Intelligence | Market Intelligence owns benchmark observations; portfolio strategy supplies referenced benchmark context. |
| `SA15` | Analytics | Portfolio drawdown, volatility, concentration, and portfolio-risk measures | Portfolio Intelligence | Instrument-Level Derived Risk remains Decision Intelligence under `M34-D-0010`. |
| `SA18` | Analytics | Monthly returns and quantitative portfolio-performance statistics | Portfolio Intelligence | The mapping covers portfolio-derived measures only. |
| `SA19` | Analytics / Portfolio Intelligence | Factor exposure, Portfolio DNA, style drift, and per-stock factor scores as portfolio analysis | Portfolio Intelligence | Asset identity/classification and Market observations retain source authority. |
| `SA20` | Portfolio Intelligence / Market Data | Investment Judgment represented by technical, fundamental, news, and signal interpretation | Decision Intelligence | This row does not own Market Observations, Asset identity/classification, Evaluation, or Presentation; use the mandatory `M34-D-0010` decomposition. |
| `SA22` | Analytics | Contribution and contributor rankings as portfolio-derived measures | Portfolio Intelligence | Canonical vocabulary must distinguish contribution, P/L ranking, and attribution before admission. |
| `SA23` | Analytics / AI Evaluation presentation | Return attribution, effect waterfall, and residual/unexplained measure | Portfolio Intelligence | Trust & Evaluation may independently evaluate or explain results; Experience only renders them. |
| `SA26` | Portfolio Intelligence / AI Evaluation | Recommendation, belief, ideal weights, and consensus as decision knowledge | Decision Intelligence | Trust & Evaluation owns subsequent grades and evaluation; M32/M33 authority remains unchanged. |
| `SA30` | Portfolio Intelligence / AI Evaluation | Decision record and Decision Memory as Decision Intelligence concepts | Decision Intelligence | Legacy artifacts remain `STOPPED_AUTHORITY` under `M34-D-0008`; evaluation views remain Trust & Evaluation. |
| `SA31` | AI Evaluation / Analytics | Shadow, Ideal, AI, and user portfolio counterfactual trajectories and Gaps A/B | Trust & Evaluation | Ledger & Accounting and Portfolio Intelligence retain actual-fact and actual-measure authority. |
| `SA32` | AI Evaluation | Recommendation grades, evaluation lenses, scorecard, and maturity states | Trust & Evaluation | The evaluated recommendation remains Decision Intelligence input. |
| `SA33` | AI Evaluation / Analytics | Human-versus-AI comparison, scoreboard, return delta, and regret evaluation | Trust & Evaluation | Actual and counterfactual inputs retain their source-domain owners. |
| `SA34` | AI Evaluation | Opportunity cost and divergence/deferral evaluation | Trust & Evaluation | Legacy decision inputs inherit `STOPPED_AUTHORITY` where applicable. |
| `SA35` | AI Evaluation / Portfolio Intelligence | Confidence calibration and calibration history | Trust & Evaluation | Decision Intelligence owns the confidence-bearing judgment being evaluated. |
| `SA37` | AI Evaluation | Trust report and evaluative verdict | Trust & Evaluation | Operational source statuses remain independently owned and the Operations composite remains presentation-only under `M34-D-0009`. |

## 3. Mapping invariants

1. Each mapped semantic concept has exactly one constitutional owner.
2. A mapped owner owns the identified concept only, not its inputs,
   provenance, evaluation, transport, persistence, or presentation.
3. A source table, route, service, type, cache, or page never appoints an
   owner.
4. Experience Platform owns rendering and the bounded interaction concepts
   approved by the ARB; it acquires no business truth through composition.
5. Mixed frozen claim families must be expanded using the semantic mapping
   before WP6 verifies individual fields.
6. `SA27` through `SA30` retain every `STOPPED_AUTHORITY` constraint in
   `M34-D-0008`.
7. The temporal dimensions of all mapped claims use `M34-D-0005`.
8. This table cannot be generalized into an alias between a WP1 label and a
   constitutional domain.

## 4. Completeness and exclusions

All 19 `PROVISIONAL_MAPPING` families named by DQ-01 are present exactly once
in section 2. No additional claim family is mapped by this artifact.

This artifact does not:

- map the 9 WP5 `ALIGNED` families, which already had direct authority;
- resolve the 7 `CONFLICTED`, 2 `STOPPED_AUTHORITY`, or 3
  `UNKNOWN_OWNERSHIP` families independently of their approved DQ rulings;
- replace the semantic decomposition artifact;
- create or approve Glossary entries;
- admit a claim family to WP6;
- modify the Platform Architecture, a Domain Constitution, or frozen
  WP1-WP5A evidence; or
- authorize implementation, runtime work, Portfolio Home, M34.1, or an
  M32/M33 reopening.

## 5. Traceability

- Governing decision: `M34-D-0001`.
- Portfolio and scope decompositions: `M34-D-0002`, `M34-D-0003`.
- Classification and temporal constraints: `M34-D-0004`, `M34-D-0005`.
- Vocabulary admission rule: `M34-D-0006`.
- Configuration, legacy, Operations, instrument, and Watchlist constraints:
  `M34-D-0007` through `M34-D-0011`.
- WP6 gate: `M34-D-0012`.
- Frozen evidence: `M34-E-0039`, `M34-E-0040`, `M34-E-0043`,
  `M34-E-0044`, `M34-E-0045`, `M34-E-0048`, `M34-E-0049`, and
  `M34-E-0050`.

WP6 remains unauthorized. M34.1 remains NO-GO.
