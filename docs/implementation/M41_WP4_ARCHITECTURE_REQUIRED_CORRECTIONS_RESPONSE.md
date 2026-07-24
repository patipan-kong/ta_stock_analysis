# M41-WP4 — Architecture Required Corrections Response

**Document role:** Architecture Review Board (fresh session)

**Responds to:** M41-WP4 Independent Architecture Review — `APPROVED WITH
REQUIRED CORRECTIONS`

**Response date:** 2026-07-24

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP4 — Result, State, and Provenance Model

**Resulting proposal status:** `READY FOR INDEPENDENT ARCHITECTURE
CONFIRMATION`

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Production-method authority:** `NONE`

**Executable-validation authority:** `NONE`

---

## 0. Purpose and Scope of This Response

The independent architecture review returned `APPROVED WITH REQUIRED
CORRECTIONS` and issued exactly two required corrections, `RC-1` and `RC-2`,
plus two explicitly optional advisory observations, `AO-1` and `AO-2`.

This response resolves both required corrections by editing only prose in
[M41_WP4_ARCHITECTURE_PROPOSAL.md](M41_WP4_ARCHITECTURE_PROPOSAL.md). It does
not redesign the architecture, introduce scope, change ownership, add governed
vocabulary, alter any authority boundary, or modify any frozen artifact. Both
corrections are internal-consistency and citation-precision fixes; neither
changes what WP4 owns, what it consumes, or what it produces.

The architecture was **not** rejected. Only these two corrections were required
before architecture confirmation.

---

## 1. RC-1 Resolution — Calculation Temporal Claim timestamp vs. Result identity

### 1.1 The finding

The reviewer identified that three statements in the proposal could not all be
true simultaneously:

- Result identity is derived from the canonical bytes;
- canonical serialization includes the timestamp / temporal-claim encoding; and
- Result identity must exclude computation time.

Under the frozen `M34-D-0005`, the authoritative timestamp of a `Calculation`
Canonical Temporal Claim **is** the calculation instant. If that timestamp is
part of the canonical bytes, and identity is a function of the canonical bytes,
then identity cannot simultaneously exclude computation time.

### 1.2 The resolution

The proposal's §6.7 (Component G) is corrected to specify **two distinct byte
views** of the Result and to state the governing rule between them, rather than
treating "the canonical bytes" as a single undifferentiated basis:

1. the **canonical Result serialization** — the complete, round-trippable
   encoding. It *does* carry the `Calculation` Canonical Temporal Claim
   including its calculation-instant timestamp, because that timestamp is
   authoritative under `M34-D-0005` and belongs to the Result's lineage; and

2. the **Result identity basis** — the identity-determining subset of those
   same canonical fields (the frozen WP1–WP3 coordinates and the outcome/value
   content). The identity basis **excludes** the `Calculation` Canonical
   Temporal Claim's calculation-instant timestamp, together with host time,
   request time, retrieval time, provider order, cache state, map-iteration
   order, and presentation labels.

The corrected text fixes the governing architectural rule explicitly: **the
`Calculation` Canonical Temporal Claim timestamp is carried on the Result —
serialized, round-tripped, and part of its lineage — but does not participate
in Result identity.** Two Results built from identical frozen WP1–WP3
coordinates and identical outcome/value content are the same Result — same
identity, same hash — even when their calculation-instant timestamps differ.

The §8.3 golden-vector matrix "Identity independence" row is tightened to name
the `Calculation` Canonical Temporal Claim's calculation-instant timestamp
explicitly among the operational coordinates that do not affect identity, so the
required proof matches the corrected §6.7 rule.

### 1.3 Why this resolves the inconsistency without redesign

The three original statements are now mutually consistent: identity is a
function of the **identity basis** (not of the full serialization), the full
serialization still carries the temporal-claim timestamp for round-trip and
lineage, and identity still excludes computation time because the
calculation-instant timestamp lives outside the identity basis.

No architectural scope changed:

- **Result identity is not redesigned** — it remains a deterministic function
  of canonical fields that excludes every operational coordinate; the
  correction only names which subset of the canonical fields is
  identity-determining, resolving an ambiguity that was already implied by the
  proposal's own "identity independence from every operational coordinate"
  language (§1 item 7) and its existing identity-independence golden vector.
- **The Canonical Temporal Claim is not redesigned** — its authoritative
  timestamp remains the calculation instant per frozen `M34-D-0005`; WP4 still
  only binds and carries it.
- **The Measurement Window is not redesigned** — it remains the distinct
  input-selection boundary of Component E, neither substituted for the temporal
  claim nor part of identity.
- **No new semantics are created** — no new field, noun, outcome value, or
  state token is introduced; the correction is a partition of existing bytes
  into serialization vs. identity basis, which Stage B was already obligated to
  specify.

### 1.4 Sections modified for RC-1

- §6.7 (Component G) — replaced the single-view "canonical bytes" description
  with the two-view serialization / identity-basis distinction and the explicit
  carried-but-not-identity-participating rule.
- §8.3 (golden-vector matrix), "Identity independence" row — named the
  `Calculation` Canonical Temporal Claim calculation-instant timestamp
  explicitly.

---

## 2. RC-2 Resolution — partial-output deferral citation

### 2.1 The finding

The proposal's §6.9 (Component I) attributed the partial-output deferral to
"WP3 §4.4." The authoritative references are **WP3 §6.1** and the **WP3 §12.1
note**.

### 2.2 The resolution

§6.9 is corrected to cite "the case WP3 §6.1 and its §12.1 note left to the
Result contract" in place of "the case WP3 §4.4 left to the Result contract."

This is a citation-precision fix only. The deferred responsibility itself — WP4
as sole owner of partial-output / partial-result composition — is unchanged, as
is every rule in Component I. No semantic change accompanies the corrected
citation.

### 2.3 Sections modified for RC-2

- §6.9 (Component I) — corrected the WP3 cross-reference from `§4.4` to `§6.1`
  and the `§12.1` note.

---

## 3. Advisory Observations — disposition

The two advisory observations were explicitly optional and were stated not to
change architectural scope. Their disposition:

- **AO-1** (clarify `PARTIAL` Degraded State vs. partial-output composition):
  **acknowledged, not adopted in this response.** The existing proposal already
  separates the two concerns — the outcome/degraded-state interaction matrix is
  Component D and partial-output/partial-result composition is Component I, and
  §6.9 already requires that partial composition "interacts with the
  no-value-on-failure rule and the outcome/degraded-state matrix so that a
  partial Result is never an undisclosed full success or an undisclosed
  failure." Any further elaboration is a Stage B drafting concern, not an
  architecture-level correction. Adopting it here would be optional
  amplification with no gate effect.
- **AO-2** (optionally include the reason-representation field in the Stage A
  semantic inventory): **acknowledged, not adopted in this response.** §4
  already scopes a reason *representation* field (composing frozen coordinates,
  adding no governed noun) and §7.1 already inventories "one row per component
  in §6"; whether to surface reason-representation as its own Stage A row is a
  Stage A authoring choice within the existing scope, not an architecture
  correction.

Neither advisory changes scope, ownership, vocabulary, authority, review
strategy, stage decomposition, or closeout conditions, and neither is required
for confirmation.

---

## 4. Exact Sections Modified

| Document | Section | Change type | Nature |
|---|---|---|---|
| `M41_WP4_ARCHITECTURE_PROPOSAL.md` | §6.7 (Component G) | RC-1 | Prose: partition canonical bytes into serialization view vs. identity basis; state carried-but-not-in-identity rule for the calculation-instant timestamp |
| `M41_WP4_ARCHITECTURE_PROPOSAL.md` | §8.3 golden-vector matrix, "Identity independence" row | RC-1 | Prose: name the `Calculation` Canonical Temporal Claim calculation-instant timestamp among identity-irrelevant operational coordinates |
| `M41_WP4_ARCHITECTURE_PROPOSAL.md` | §6.9 (Component I) | RC-2 | Citation: `WP3 §4.4` → `WP3 §6.1` and its `§12.1` note |

No other section of the proposal was modified. No other document was modified.

---

## 5. Confirmations

- **Both required corrections are fully resolved.** RC-1 is resolved by the
  §6.7 two-view distinction and the §8.3 vector tightening; RC-2 is resolved by
  the §6.9 citation correction.
- **No architectural scope changed.** WP4 owns, consumes, and produces exactly
  what the reviewed proposal specified. No component was added, removed, or
  re-scoped.
- **No ownership changed.** Every ownership-matrix cell (§3.2, §5.1) is
  unchanged.
- **No authority boundary changed.** The §0 precedence order, the §5.2 five-part
  gate, and all upstream-authority citations are unchanged.
- **No new governed vocabulary was introduced.** WP4's vocabulary posture
  (§2.1) is unchanged: no new noun of WP4's invention; Measure Value still
  relies on WP1's confirmed `ADMIT`; Provenance / Canonical Temporal Claim /
  Degraded State remain reused; Calculation Temporal Claim remains `REJECT`.
- **Review strategy, stage decomposition, and closeout conditions are
  unchanged** (§7, §10, §12).
- **No frozen artifact was modified.** M41 Architecture, WP1, WP2, WP3, the
  Glossary, the Decision Log, the Implementation Index, and Graphify output are
  untouched.
- **No semantic expansion occurred.** Both corrections are internal-consistency
  and citation fixes; no rule, field, outcome value, state token, or golden
  vector's meaning changed.
- **Implementation authority remains `NONE`**, as do Runtime, Provider,
  Persistence, API, Production-method, and Executable-validation authority.

---

## 6. Resulting Status

With `RC-1` and `RC-2` resolved and no advisory adopted in a scope-changing way,
the M41-WP4 Architecture Proposal is:

**READY FOR INDEPENDENT ARCHITECTURE CONFIRMATION**

This response performs no Independent Confirmation. It stops after resolving the
required corrections, as instructed. Independent Confirmation, if it proceeds,
is a separately authorized activity.
