# M41 — Independent Architecture Review Board Assessment

**Review date:** 2026-07-23

**Reviewer role:** Independent Architecture Review Board; not the proposal
author and not the self-review author.

**Artifacts reviewed:**

- [M41 Architecture Proposal](M41_ARCHITECTURE_PROPOSAL.md)
- [M41 Architecture Proposal Self-Review Response](M41_ARCHITECTURE_PROPOSAL_REVIEW_RESPONSE.md)

**Governing authority cross-checked:** [Platform Architecture](../architecture/platform_architecture.md),
[Canonical Glossary](../GLOSSARY.md), the M34 Decision Register decisions
`M34-D-0004`, `M34-D-0005`, and `M34-D-0010`, the frozen M39 closeout and
specification corpus, and the complete M40 architecture, admission,
reconciliation, closeout-review, correction, and independent-confirmation
chain.

**Review scope:** Constitutional soundness, architectural consistency,
repository compatibility, milestone boundary, work-package governance,
acceptance evidence, scope and authority containment. This review creates no
implementation, runtime, provider, persistence, API, public-exposure,
production-method, or work-package authority.

**Repository mutation scope:** This review document is the only intended
change. The proposal, its response, the Decision Log, frozen M29–M40
artifacts, Graphify output, and implementation are not modified.

---

## 1. Executive Assessment

The proposed **specification-only** M41 boundary is directionally correct and
repository-compatible. Separating Definition/Method, input-manifest,
determinism, and result/provenance specifications from the first Registry and
Kernel implementation avoids combining unresolved semantics with executable
authority. The WP1 → WP2 → WP3 → WP4 dependency order is coherent, and
deferring Registry, Resolver, Kernel, integration, providers, persistence,
API, and Experience adoption preserves the M39/M40 freeze.

The proposal is not ready for unconditional approval. Independent review
found five required corrections:

1. it reuses one rejected M40 specialization and treats two already-canonical
   terms as possible new registrations;
2. it lacks an explicit candidate-vocabulary admission gate before new M41
   nouns are relied upon;
3. it does not carry the frozen M40 five-part ownership boundary and
   witnessed-versus-computed distinction into mechanically testable M41 exit
   criteria;
4. it does not state with sufficient precision that M41 specifies a future
   method-admission mechanism but admits no concrete production Definition,
   Method Version, formula, or method; and
5. its evidence and closeout sequence leaves specification-only vector
   validation ambiguous and omits an explicit independently approved
   closeout gate before the Graphify refresh.

These defects are correctable without changing the recommended milestone
boundary or adding implementation scope.

---

## 2. Constitutional and Frozen-Decision Assessment

### 2.1 What is constitutionally sound

- The proposal acknowledges the Platform Architecture, Canonical Glossary,
  Asset Foundation constitutions, M34 decisions, and frozen M39/M40 corpora as
  higher authority.
- It grants no operational authority and correctly treats technical design
  approval as non-transitive.
- It preserves Market Intelligence ownership of bounded descriptive market
  facts while excluding portfolio meaning, judgment, evaluation, execution,
  and presentation authority.
- It consumes M39 Observation evidence by immutable reference and does not
  authorize mutation, persistence, retrieval, or provider access.
- It preserves the existing Canonical Temporal Claim and the distinction
  between Computation Outcome and Degraded State in its stated intent.
- It does not create a new domain, amend a constitution, reopen an ADR, or
  claim code as precedent.

### 2.2 Required constitutional corrections

#### RC-1 — Frozen vocabulary is contradicted inside the proposal

**Severity:** High

Proposal §6 includes “Calculation Temporal Claim usage,” even though proposal
§1 correctly records **Calculation Temporal Claim** as a rejected M40
specialization and §10 says the negative corpus must not reappear. The correct
frozen construction is the existing **Canonical Temporal Claim** qualified by
Event Type `Calculation` and Producing Domain `Market Intelligence`.

Proposal §8 also gives “Input Manifest” and “Provenance” as examples of
distinct new registrable nouns. **Observation Input Manifest** is already one
of the eight effective M40 admissions. **Provenance** already exists in the
Canonical Glossary and is reserved load-bearing vocabulary under Platform
Architecture V3. Neither may be re-admitted or redefined by M41.

This is a direct V1/V3 and frozen-negative-corpus defect, not merely an
editorial inconsistency.

**Required correction:**

- replace “Calculation Temporal Claim usage” with explicit reuse of the
  existing Canonical Temporal Claim for Event Type `Calculation`;
- remove Input Manifest and Provenance from examples of new terms;
- state that Observation Input Manifest and Provenance are reused with their
  frozen meanings;
- if a narrower lineage structure is needed, treat its name as a candidate
  specialization and prove that it refines rather than redefines Provenance;
  and
- run the negative-corpus check against the proposal itself as well as future
  work-package artifacts.

#### RC-2 — New-noun registration is procedural but not admission-governed

**Severity:** High

The proposal requires same-change Glossary synchronization, which satisfies
only the timing portion of V2. It does not require a complete candidate
inventory or an independent admit/reject/rename decision before terms such as
Market Measure Definition, Method Version, Measure Subject, Method
Requirement, Measurement Window, Measure Value, or a specialized lineage term
are relied upon.

M40's frozen review history is explicit that synchronization is not a
substitute for admission. Ownership, overlap, negative-corpus, temporal
grammar, and constitutional-boundary proofs were admission-blocking.
Automatically registering every newly introduced noun would allow a work
package to create canonical language by drafting it.

**Required correction:**

- make WP1 begin with a candidate-vocabulary and ownership register;
- for each candidate, require exact definition, single owner, existing-term
  overlap analysis, V1–V3 disposition, M34/M39/M40 compatibility, and
  `ADMIT`, `REUSE`, `RENAME`, or `REJECT` outcome;
- prohibit downstream reliance until independent constitutional review
  approves the disposition and any required correction is independently
  confirmed; and
- synchronize only admitted terms, while linking all uses of existing terms
  to their canonical definitions.

#### RC-3 — Frozen M40 ownership proofs are referenced but not made M41 gates

**Severity:** High

M40's architecture corrections were approved because they supplied a
mechanically testable five-part boundary: permitted subject, permitted
inputs, output meaning, prohibited portfolio/ledger/life inputs, and
prohibited judgment semantics. They also froze the distinction between a
witnessed/provider-reported statistic represented through M39 Observation
semantics and a platform-computed statistic represented as a Calculated
Market Measure.

M41 excludes several neighboring domains and mentions a negative corpus, but
its WP deliverables and acceptance criteria do not expressly re-run those
mechanical tests against every Definition, Method Requirement, subject,
manifest, result coordinate, and example. General “no reinterpretation”
language is weaker than the admission-blocking mechanism whose approval made
the M40 boundary sound.

**Required correction:**

- carry the frozen five-part M40 boundary into WP1–WP4 validation and
  milestone acceptance;
- require every candidate Definition and result coordinate to pass it;
- require every input class to prove it is M39 evidence, Asset Foundation
  reference data, an explicit invocation parameter, or a governed
  calculation dependency;
- require the witnessed-versus-computed/Event Type distinction to remain
  explicit; and
- make any failure an admission blocker routed to the existing owning domain,
  not a review recommendation.

---

## 3. Milestone Boundary, Scope, and Authority

### 3.1 Correct milestone boundary

The boundary after specification WP4 and before executable Registry/Resolver/
Kernel work is sound. The four specifications form one coherent contract
layer:

1. WP1 defines what a governed measure and method specification is.
2. WP2 binds it to exact subjects and immutable M39 evidence.
3. WP3 closes all ambient semantic choices.
4. WP4 defines the immutable outcome and lineage produced under those rules.

Removing WP4 would leave no implementable result contract. Pulling Registry
or Kernel work into M41 would cross from specification into implementation.
Deferring integration design until a Kernel exists is also reasonable.

### 3.2 Scope completeness

Subject to RC-1 through RC-3, the semantic areas are complete for a
framework-level specification: identity, applicability, evidence selection,
canonical serialization, time, calendar, units, currency, adjustment,
missing/conflicting evidence, arithmetic, dependencies, outcome, temporal
claim, identity, and lineage are all represented.

The proposal correctly does not require a provider, historical custody,
runtime Observation source, or concrete formula merely to specify these
contracts.

### 3.3 Scope exclusions and authority leakage

#### RC-4 — Designing method admission is not clearly separated from
exercising it

**Severity:** Medium

WP1 includes a “method-admission gate” and “production-empty default,” while
the document header withholds production-method authority. The intended
reading is defensible: M41 specifies the future gate. The proposal does not,
however, explicitly prohibit admitting a concrete Market Measure Definition,
Method Version, formula, reference method, or production method as a
documentation-only act. That omission matters because semantic admission can
leak authority even when no code exists.

The phrase that a future milestone can implement without “re-litigating
semantics” is valid only for the framework contracts. A future concrete
method still needs its own formula, owner, dependency, conformance, and
production-admission decision.

**Required correction:**

- state that M41 specifies but does not exercise the production
  method-admission gate;
- require the admitted production Definition/Method catalog to remain empty;
- classify formulas, named indicators, illustrative methods, and reference
  calculations as non-admitted examples or normative framework vectors only;
  and
- state that future Registry/Kernel implementation authority does not itself
  admit any production method.

With that correction, the explicit exclusions are otherwise strong and
prevent provider, persistence, API, Experience, Asset Registry, Portfolio,
optimizer, execution-intent, and implementation leakage.

---

## 4. Dependency and Architectural Consistency Assessment

The dependency direction is correct:

- Asset Foundation supplies identity and exact Definition Version evidence
  without surrendering ownership.
- M39 supplies immutable Observation meaning and identity without becoming a
  runtime dependency authorization.
- M34-D-0005 supplies the complete temporal/degraded-state grammar.
- M34-D-0010 keeps descriptive market facts separate from judgment,
  evaluation, and presentation.
- M40 supplies the effective vocabulary and negative corpus.
- Provider architecture remains a witness boundary and is not encoded into
  core contracts.

WP ordering is acyclic and appropriately fail-closed. WP2 depends on WP1;
WP3 depends on the exact method and manifest contracts; WP4 depends on all
three. Registry and Kernel correctly remain downstream.

The proposal should make Asset Foundation and the frozen M40 ownership tests
explicit WP acceptance dependencies, as required by RC-3, but it does not
otherwise reverse a constitutional dependency.

---

## 5. Work Packages, Acceptance Evidence, and Governance

### 5.1 Work-package structure

Four numbered specification work packages followed by an unnumbered
milestone closeout matches the M39/M40 artifact pattern. Independent review
before opening the next package is appropriate. Required corrections must be
resolved and independently confirmed; an author response alone is not gate
closure.

WP3 is broad, but the grouped concerns all control deterministic semantic
interpretation. Splitting it is optional if review size becomes
unmanageable; compressing or partially approving unresolved semantics is not.

### 5.2 Acceptance criteria and closeout

#### RC-5 — Evidence mode and final-governance sequence are underspecified

**Severity:** Medium

M41 is explicitly specification-only, yet WP3 must prove behavior through
golden vectors and WP4 must demonstrate hash stability and serialization
round-trips. Those are valid specification techniques only if the proposal
defines what may be created and how the evidence is verified without
silently authorizing executable contract modules or a reference kernel.

The closeout sequence is also incomplete. Required evidence names a closeout
document but no independent closeout review or correction-confirmation
artifact. M40's actual closeout required independent review and a further
correction/confirmation step. In addition, the proposal says Graphify is
refreshed “at closeout” while citing an M40 closeout whose own header and
repository-state section say the refresh was `NOT_PERFORMED`. Refreshing
before the final closeout review and correction gate would encode an
unapproved corpus.

**Required correction:**

- define golden vectors as documentation/data fixtures with canonical input
  bytes, expected output bytes, derivation rationale, provenance, and
  independent recomputation evidence;
- state whether non-production validation scripts are excluded or require
  separate authority; do not leave this implicit;
- make canonical serialization byte rules themselves a WP deliverable so
  “hash stability” and “round-trip” are objectively reviewable;
- require independent review of `M41_EPIC_CLOSEOUT.md` and independent
  confirmation of any required correction;
- require Decision Log reconciliation at its explicitly approved
  reconciliation point; and
- perform the Graphify refresh only after the closeout and all required
  corrections are independently approved, never merely because WP4 or the
  first closeout draft exists.

This correction does not authorize a refresh during the present review.

---

## 6. Future Extensibility and Hidden Risks

### 6.1 Extensibility strengths

- Immutable Definition and Method versions support evolution without mutable
  “latest” semantics.
- Explicit dependency fingerprints allow calendars, unit systems, arithmetic
  policies, and future engines to evolve independently.
- Ordered multi-Asset subjects avoid an equity-only or single-symbol core.
- Provider-blind manifests permit later provider, historical-service, and
  custody work without contaminating semantic identity.
- Empty production admission and deferred adoption keep future rollout
  fail-closed.

### 6.2 Hidden risks after required corrections

| Risk | Classification | Required treatment |
| --- | --- | --- |
| A specialized lineage contract silently redefines reserved Provenance | Constitutional/authority | RC-1 candidate-specialization and V3 proof |
| Framework Definition identity is confused with Asset Definition identity | Boundary/naming | WP1 must use unambiguous canonical names and preserve Asset Foundation ownership |
| Applicability becomes an Asset capability grant | Authority leakage | WP1 must state it is a Market Intelligence method predicate only |
| A golden vector becomes an implicitly admitted method | Production authority | RC-4 classification and empty production catalog |
| Canonical bytes are underspecified across languages | Reproducibility | RC-5 exact encoding, decimal, ordering, Unicode, and version rules |
| “Complete lineage” requires unavailable runtime custody | Scope leakage | Specify reference requirements without claiming Observation storage or retrieval exists |
| Outcome reason codes drift into quality or trust assessment | Domain leakage | Keep execution outcome mechanical; Trust & Evaluation retains correctness and quality |
| `State` becomes a third axis beside Outcome and Degraded State | Vocabulary ambiguity | WP4 must either remove the generic label or define it solely as existing axes |

None requires moving Registry, Kernel, integration, or runtime work into M41.

---

## 7. Review Matrix

| Review dimension | Assessment |
| --- | --- |
| 1. Constitutional compliance | Conditional; RC-1 and RC-2 required |
| 2. Preservation of M29–M40 decisions | Broadly preserved; RC-1 and RC-3 close direct frozen-corpus gaps |
| 3. Correct milestone boundary | Pass |
| 4. Scope completeness | Pass for framework specification after required corrections |
| 5. Scope exclusions | Strong; RC-4 must close concrete-method admission ambiguity |
| 6. Architectural consistency | Pass after frozen ownership gates are made mechanical |
| 7. Dependency correctness | Pass with RC-3 acceptance dependency clarification |
| 8. Governance compliance | Conditional; RC-2 and RC-5 required |
| 9. Repository convention consistency | Work-package numbering passes; final closeout/Graphify sequence requires RC-5 |
| 10. Work Package structure | Pass |
| 11. Acceptance criteria | Conditional; RC-3, RC-4, and RC-5 required |
| 12. Future extensibility | Strong |
| 13. Hidden architectural risks | Identified and controllable |
| 14. Scope leakage | Controlled after RC-4 and RC-5 |
| 15. Authority leakage | Controlled after RC-1, RC-2, and RC-4 |

---

## 8. Self-Review Response Assessment

The self-review correctly fixed title consistency, future-milestone wording,
and closeout numbering. Those are useful repository-convention corrections.
It did not independently test the proposal's core architectural assumptions
and expressly declined to reopen them, so it cannot substitute for this
review.

One authority-signaling phrase must also be corrected: the response calls the
milestone boundary “approved in the original proposal.” The proposal's own
headers say `NOT_APPROVED`, and an author self-review cannot grant approval.
The phrase must read “proposed in the original proposal” or equivalent.

This wording correction is included under the governance disposition and
does not change the milestone boundary.

---

## 9. Repository Validation and Scope Confirmation

- Existing Graphify output was queried for navigation; no Graphify update or
  refresh was run.
- The two reviewed M41 input artifacts were not modified.
- No implementation artifact, work-package artifact, Decision Log entry,
  constitution, frozen M29–M40 artifact, or production file was created or
  changed by this review.
- The relative targets cited by the M41 proposal were checked against the
  repository.
- The working tree reported the two reviewed M41 input documents as untracked
  before this review. Therefore the proposal's literal “main branch is clean”
  statement was not independently reproducible from the available working
  tree, although no tracked implementation or frozen-artifact modification
  was observed. This is a repository-state observation, not a reason to alter
  the architectural outcome.

---

## 10. Final Outcome

The specification-only M41 boundary is architecturally sound, but the five
required corrections must be applied and independently confirmed before WP1
may begin. They can be resolved without modifying any frozen M29–M40
decision, expanding M41 into implementation, or changing the four-work-package
structure.

APPROVED WITH REQUIRED CORRECTIONS
