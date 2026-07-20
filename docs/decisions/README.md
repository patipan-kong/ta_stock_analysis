# Decisions

*This directory holds Architecture Decision Records (ADRs) — the permanent record of a specific choice made at a specific point in time, and why. Each ADR resolves exactly one question that could otherwise be re-litigated, re-discovered, or silently defaulted differently by two different engineers (or two different agent sessions).*

---

## Purpose

Most of what this platform knows about itself is documented as *standing description* — what the architecture is, how it works, what the plan for building it looks like. An ADR is different in kind: it is a *decision event*. It exists because a real fork in the road was found, both branches had a defensible case, and the project needs the choice — and the reasoning behind it — to survive past the conversation in which it was made.

An ADR is written once, at the moment a decision is made, and is not rewritten as understanding evolves. If a later decision supersedes an earlier one, the later ADR says so explicitly and links back; the earlier ADR is left standing as the historical record of what was decided and why, not silently edited or deleted.

---

## How this differs from the other `docs/` categories

The platform's documentation separates *four* kinds of claim. Confusing them is the most common way documentation rots — a decision gets buried inside an architecture doc where it looks like settled design instead of a dated choice, or a plan gets treated as permanent law when it was only ever a sequencing bet.

| Category | Answers | Time horizon | Example |
|---|---|---|---|
| **Architecture** (`docs/architecture/`) | *What is this system, structurally?* Domain boundaries, ownership of concepts, the shape something must have. | Durable — changes rarely, and only with a deliberate re-argument. | "An Asset has a permanent `asset_id` and a once-only `canonical_symbol`." |
| **Implementation** (`docs/implementation/`) | *How do we get the running system from here to the target architecture?* Milestones, sequencing, current-state investigation, risk. | Medium — valid for the life of one epic, then superseded or archived. | "M5 backfills the ledger before M6 touches analytics." |
| **Decisions** (`docs/decisions/`, this directory) | *What did we choose, at a specific fork, and why?* One question, one answer, one piece of reasoning. | Permanent as a historical record, even after superseded. | "Replay parity is measured against corrected accounting, not preserved defects (ADR-005)." |
| **Research** (`docs/research/`) | *What might we do, and what do we not yet know?* Open exploration, backlogs, ideas not yet committed to. | Disposable / speculative — no claim here binds anything until it graduates into architecture, a plan, or an ADR. | Entries in `FUTURE_EXPERIMENTS.md` or `IDEA_PARKING_LOT.md`. |

A useful test: **architecture** describes a shape, **implementation** describes a route, a **decision** explains a fork in that route, and **research** is everything still on the whiteboard.

---

## When something belongs here

Write an ADR when:

- An implementation or investigation effort (an M0 analysis, a design spike, a bug investigation) surfaces a genuine ambiguity that the architecture does not resolve and that could reasonably be decided more than one way.
- The choice, once made, needs to bind future work — so it must be discoverable and citable, not left as a conclusion buried in a paragraph of a planning document.
- Getting the choice wrong (or re-deciding it inconsistently later) has real cost — data correctness, migration safety, or an architectural boundary is at stake.

Do **not** write an ADR for:

- Routine implementation choices with no real alternative worth recording (that's ordinary code or, at most, a comment).
- Standing architectural design — that belongs in `docs/architecture/`, described as the system's shape, not as a dated choice.
- Open questions nobody has decided yet — those stay in the relevant implementation document's "Open Questions" section (or in `docs/research/`) until they are actually resolved.

## Numbering and format

ADRs are numbered sequentially (`ADR-001`, `ADR-002`, ...) and never renumbered or reused, even if superseded. `docs/engineering/DECISION_LOG.md` is the running narrative log these formal ADRs were extracted from and continues to hold the day-to-day decision history around them; new decisions are recorded here as standalone files going forward. Each ADR file states its own **Status** (e.g., Accepted, Superseded) and, at minimum, its Context, the Problem it resolves, the Decision itself, its Rationale, its Consequences, and the Alternatives Considered.

---

## ADR Index

| ADR | Summary |
|---|---|
| [ADR-001](ADR-001_TRANSACTION_LEDGER_SINGLE_SOURCE_OF_TRUTH.md) | The transaction ledger is the platform's single source of truth and is immutable; every other representation of portfolio state is a disposable derivation reproducible solely by replaying it. |
| [ADR-002](ADR-002_NO_COMPENSATION_FOR_LEDGER_DEFECTS.md) | Portfolio Metrics (and any downstream consumer) never compensates for ledger or data-quality defects — it fails loud rather than silently absorbing drift; validation and repair belong exclusively to the Ledger Validator and Ledger Repair. |
| [ADR-003](ADR-003_TWO_TIMELINE_RULE.md) | `transaction_date` governs replay-order/portfolio-state questions; `created_at` governs audit and window-membership, and only in incrementally-built engines — neither date substitutes for the other. |
| [ADR-004](ADR-004_ONE_IMPLEMENTATION_PER_RULE.md) | Every calculation or business rule has exactly one authoritative implementation shared by all consumers; no engine may reimplement, special-case, or cache a parallel version of a rule that already exists. |
| [ADR-005](ADR-005_REPLAY_CORRECTNESS_BASELINE.md) | Replay parity is measured against correct accounting, not preserved implementation defects; known correctness defects must be repaired before golden replay baselines are captured. |
| [ADR-006](ADR-006_M34_EXTERNAL_GOVERNANCE_DEPENDENCY.md) | The governance authority required to constitute and operate the M34 Authorization Gate is an intentional external dependency that remains unratified; M34 stays internally complete and authorization-blocked until qualifying external evidence is accepted. |
