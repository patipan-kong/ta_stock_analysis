# M41-WP4 Stage A — Independent Review

**Document role:** Independent Governance Reviewer (fresh session)

**Reviews (only):**
[`M41_WP4_STAGE_A_VOCABULARY_AND_SEMANTIC_SURFACE_REGISTER.md`](M41_WP4_STAGE_A_VOCABULARY_AND_SEMANTIC_SURFACE_REGISTER.md)

**Review date:** 2026-07-24

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP4 — Result, State, and Provenance Model

**Stage:** A — Vocabulary Sufficiency and Semantic Surface Register

**Mandate limit:** This review determines only whether Stage A is ready to
become frozen authority. It does not rewrite the register, redesign the
architecture, or design Stage B. The frozen M41 Architecture, WP1, WP2, WP3,
and the confirmed-and-frozen WP4 Architecture are treated as authoritative and
were consulted, not re-reviewed.

**Final determination:** **APPROVED**

**Implementation authority:** `NONE`

---

## 1. Method

The register makes a large number of exact citations into frozen authority.
An independent review that accepted those citations on faith would be
worthless, so each load-bearing claim was verified directly against its source:

| Claim in Stage A | Verified against | Result |
|---|---|---|
| Stage A must produce one surface per §6 component | WP4 Architecture §7.1 (frozen) | Confirmed — §6 defines nine components A–I; the register's `ID / frozen component` column traces every surface A–M to one of them. |
| Surface M (reason representation) is a deferred WP4 responsibility | WP3 Closeout §"Deferred Responsibilities", line 124 | Confirmed — "reason-code representation" is expressly deferred to WP4. |
| Computation Outcome is exactly four values | `GLOSSARY.md#computation-outcome` | Confirmed — `SUCCEEDED` / `INSUFFICIENT_INPUT` / `DEPENDENCY_UNRESOLVED` / `FAILED`; owned by Market Intelligence; "a reason may explain an outcome but does not introduce judgment." |
| Degraded State is six values | `GLOSSARY.md#degraded-state` | Confirmed — `UNKNOWN`, `UNAVAILABLE`, `DELAYED`, `STALE`, `PARTIAL`, `CONFLICTING`; governed by `M34-D-0005`. |
| Calculation Temporal Claim remains `REJECT`, carried forward | WP1 Candidate Register §6.9 | Confirmed — full-overlap rejected duplicate, "not reintroduced under a new name." |
| Measure Value is an already-confirmed WP1 `ADMIT` | WP1 Candidate Register §6.6 + confirmation chain | Confirmed — registered `ADMIT`, relied on (not re-admitted) by WP4. |
| §6.7 two-view (serialization vs. identity basis) is frozen | WP4 Architecture §6.7 + RC-1 + Independent Architecture Confirmation | Confirmed — the corrected two-view distinction is present and frozen; the register cites it as "corrected WP4 Architecture §6.7 / RC-1." |
| Partial composition deferral cites WP3 §6.1 + §12.1 | WP4 Architecture §6.9 (post-RC-2) and WP3 Stage B §6.1, §12.1 | Confirmed — headings exist; RC-2 corrected the citation from the earlier erroneous §4.4. |
| WP3 handoff is fixed at §14.6 / closeout | WP3 Stage B §14.6, WP3 Closeout | Confirmed — sections exist and hand off exactly the four coordinates the register enumerates. |
| Provenance is owned at capture by Connectivity & Ingestion | WP4 Architecture §5.1; Platform Architecture §6.4 (cited) | Confirmed — register treats WP4 as carrier only. |

No cited coordinate was found to be misquoted, widened, or invented.

---

## 2. Objective-by-objective determination

| # | Review objective | Finding |
|---|---|---|
| 1 | Preserves every frozen authority | **PASS** — §1.1 states the exact precedence order; §6 consumes WP1/WP2/WP3 by citation with an explicit "prohibited WP4 action" column per source. |
| 2 | Respects constitutional precedence | **PASS** — §1.1 subordinates the register, in order, to platform/Asset Foundation → M34/M39/M40 → M41 Architecture → WP1 → WP2 → WP3 → confirmed WP4 Architecture, with a conflict-yields-to-higher rule. |
| 3 | No architectural redesign | **PASS** — the register composes frozen coordinates; it adds no component, re-scopes none, and defers all field/shape/byte/matrix design to Stage B (§1.2, §1.3, §9). |
| 4 | No semantic expansion | **PASS** — §3.3 records candidate inventory `none`; every label resolves to `REUSE`, prior confirmed `ADMIT`, carried `REJECT`, or ordinary language. |
| 5 | No hidden implementation requirement | **PASS** — §8 confirms serialization, hashing, and reason representation must be explicit Stage B syntax and may not delegate semantics to a library, locale, clock, or default. |
| 6–10 | No runtime / provider / persistence / API / production authority | **PASS** — asserted in the header and re-proven at §1.3, §4.2, §5.1, and §10; no service, resolver, registry, endpoint, or catalog record is created. |
| 11 | No executable-validation authority | **PASS** — §7 performs Golden Vector *planning* only; Golden Vector is classified "Ordinary language only" (documentation/data-fixture evidence, not an executable artifact); "No executable runner, harness, or reference implementation is authorized." |

---

## 3. Vocabulary review

Every entry in §3.1 and §3.2 was checked for correct disposition class.

- **No governed term silently introduced.** The §3.2 ordinary-language table
  correctly classifies composition, closure, the interaction matrix, identity,
  identity basis, serialization, hash stability, round-trip determinism,
  lineage completeness, handoff, partial composition, reason representation,
  Golden Vector, and validation language as `Ordinary language only`, each with
  a stated reason it carries no independent owner. The governed-concept test in
  §2.1 is applied correctly: normativity, serialization, or vector inclusion do
  not by themselves create governed vocabulary.
- **No governed term silently widened.** Each `REUSE` row in §3.1 pins the term
  to its frozen owner and adds a boundary clause (e.g., Market Measure umbrella
  "not widened"; Computation Outcome "no fifth value"; Degraded State "existing
  six values only"; Provenance "carriage is not recapture").
- **No rejected vocabulary reappears under another name.** `Calculation
  Temporal Claim` and the `M40 Producing Domain specialization` are both carried
  as `REJECT` (§3.1), and §8's negative corpus forbids a renamed equivalent.
  Verified against WP1 §6.9.
- **No new candidate is actually required.** The register's proof (§3.4) — that
  every WP4 statement is an exact reference, the confirmed Measure Value
  `ADMIT`, or an ordinary rule joining those within Market Measure Result — is
  sound. The one reserved possibility, a narrower "Measure Provenance" (WP1
  §6.8), is correctly declined as unnecessary and overlapping (§3.3).

---

## 4. Ownership review

- **Exactly one owner per surface.** §4 assigns a single semantic owner to each
  of A–M, and §5.1 restates the assignment as a singular-ownership table with an
  "overlap finding" of `None` on every row.
- **No ownership overlap.** The register keeps four boundaries explicit and
  correct: composition vs. classification (WP4 vs. WP3), serialization vs.
  identity (full bytes vs. identity basis), temporal Window vs. temporal Claim
  (WP3 input-selection vs. WP4 Result claim), and capture vs. carriage
  (Connectivity & Ingestion vs. Market Intelligence).
- **Carriage / serialization / validation are not ownership.** §2.3 states the
  principle ("Carriage is not capture. Composition is not ownership transfer.
  Serialization is not semantic ownership. Validation is not authority to
  redefine."), and §5.2 excludes serializer, hasher, reviewer, storage, cache,
  UI, and runtime as non-owners. Surface E's dual mention (grammar owner vs.
  Result-event-meaning owner) is a binding/ownership distinction, not a dual
  owner, and matches WP4 Architecture §5.1.

---

## 5. Boundary review

WP1, WP2, WP3, and WP4-Architecture boundaries are preserved. §6.1–§6.4 present
per-source consumption tables in which every row pairs an exact coordinate with
an explicit **prohibited WP4 action** (no re-derivation, no reinterpretation,
no fork of `MSB1`/`OIM1`/Window/numeric bytes, no reclassification, no ownership
transfer). Each of §6.1, §6.2, §6.3 closes with the sentence "This is exact
citation, not re-derivation, reinterpretation, or ownership transfer." The
handoff surface K is explicitly citation-only and rejects recomputation, repair,
and alternate paths. This satisfies the requirement that Stage B consume
upstream authority only by exact citation.

---

## 6. Semantic Surface Register completeness

The inventory is complete. All nine frozen components are covered, with the
Component-G bundle correctly decomposed:

| Frozen component (Arch §6) | Register surface(s) |
|---|---|
| A — Result composition/identity | A (composition) + contributes to G (identity) |
| B — Measure Value | B |
| C — Success/failure closure | C + M (subordinate reason representation) |
| D — Outcome/degraded-state matrix | D |
| E — Canonical Temporal Claim binding | E |
| F — Provenance carriage / lineage | F |
| G — Identity / serialization / hash / round-trip | G, H, I, J |
| H — WP3→WP4 handoff | K |
| I — Partial composition | L |

Every surface row in §4 carries all eight required attributes — governing term,
sole semantic owner, authoritative source, exact upstream dependency, downstream
dependency, disposition, ownership boundary, and Stage B dependency. §4.1
(governed-dependency determination) and §4.2 (five-part gate) apply cleanly, and
correctly hold that no new governed dependency arises and the WP1 Method Version
declared dependency-version list remains the sole calculation-dependency
inventory.

Surface M is properly subordinate: classified `Ordinary language only`, owned by
Market Intelligence for representation only, bounded so a reason "explains but
never reclassifies an Outcome," and carrying **no separate governed noun and no
separate vector family**. Its addition is squarely within the discretion the
WP4 Architecture Corrections Response left open (AO-2: "a Stage A authoring
choice within the existing scope"), and it does not elevate reason
representation into a mandatory governed obligation.

---

## 7. Golden Vector planning review

§7 performs planning only. It creates no vector, allocates the proof
responsibility already fixed by WP4 Architecture §§8.2–8.3, and assigns each
surface a Stage B author, an independent reviewer, and a governing authority
that "cannot be changed by the vector." Surface M is correctly scoped to "within
the applicable success/non-success vectors; no separate vector family is
required." No Stage B vector is prematurely specified, and no executable runner
is authorized. This is compliant planning, not design.

---

## 8. Negative corpus and consistency

§8 enumerates the prohibited constructs (fifth Outcome, new Degraded State,
renamed Calculation Temporal Claim, specialized Producing Domain, `Snapshot
Creation` Result, widened/recaptured Provenance, ungoverned "Measure Provenance,"
new reason taxonomy, second dependency manifest, forked upstream bytes,
inferred Observation identity, laundered derived values, portfolio/judgment/
execution meaning, and any executable artifact) and states that none appears.
Independent inspection of the register confirms none appears.

Internal, terminology, authority, dependency, ownership, and stage-allocation
consistency all hold. The document uses "surfaces A–L plus M" uniformly across
§4, §3.4, §10, and §11, and the header authority block (all `NONE`) is
consistent with every downstream assertion.

---

## 9. Required Corrections

**None.** No finding rises to the level of a required correction. The register
preserves every frozen authority, introduces no semantic expansion, and grants
no operational authority.

---

## 10. Advisory Observations (non-blocking — no response required)

- **AO-1 — "twelve required surfaces" phrasing (§4 intro).** The register
  describes surfaces A–L as "the twelve required surfaces," whereas the frozen
  WP4 Architecture §7.1 required "one row per component in §6," and §6 defines
  nine components. The register's own `ID / frozen component` column already
  makes the nine-to-twelve decomposition explicit and traceable, so no reader is
  actually misled, and Component G's split into four surfaces is a legitimate
  authoring decomposition. This is an editorial nuance only; a one-clause note
  that "twelve" is the author's decomposition of the nine frozen components would
  remove any momentary ambiguity. **Not required for confirmation.**

- **AO-2 — surface M framing (§4 / §7 row M).** The register is careful to keep
  reason representation permissive and subordinate ("where Stage B requires it,"
  "no separate vector family"). This correctly mirrors the architecture's
  permissive stance (Arch §4: WP4 "*may* specify a reason representation field").
  No change is needed; this observation records that the reviewer checked for,
  and did not find, an over-elevation of the optional reason field into a
  mandatory obligation.

Both advisories are optional and change no disposition, owner, boundary, or
authority.

---

## 11. Final Determination

**APPROVED.**

Explicitly:

- **Stage A may proceed to confirmation.**
- **No architectural redesign occurred.** The register composes frozen
  coordinates and designs no Stage B contract.
- **No semantic expansion occurred.** Candidate inventory is `none`; every label
  is `REUSE`, a prior confirmed `ADMIT`, a carried `REJECT`, or ordinary
  language.
- **No authority changed.** Precedence, ownership, and upstream citations are
  preserved; no Glossary, Decision Log, Index, Graphify, or frozen artifact is
  touched.
- **Implementation authority remains `NONE`**, as do runtime, provider,
  persistence, API, production-method, and executable-validation authority.

End of Independent Review.
