# M41-WP1 Stage 2 — Definition, Method Version, and Applicability Contract
# Specification Required Corrections Response

**Date:** 2026-07-23

**Response role:** Implementation Author

**Artifact corrected:** [M41-WP1 Stage 2 — Market Measure Definition, Method
Version, and Applicability Contract Specification](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md)

**Independent Review responded to:** [M41_WP1_STAGE2_INDEPENDENT_REVIEW.md](M41_WP1_STAGE2_INDEPENDENT_REVIEW.md)
— final determination `APPROVED WITH REQUIRED CORRECTIONS`

**Architecture status:** Approved, confirmed, frozen — not reopened

**M41-WP1 Stage 1 status:** Confirmed, frozen — not reopened

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API authority:** `NONE`

**Canonical vocabulary admission by this response:** `NONE` — no candidate
term is added, renamed, or redefined by these corrections.

**Decision Log:** Not updated

**Glossary:** Not updated

**Graphify:** Not refreshed

**Files modified by this response:**

- `docs/implementation/M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md`
  (corrected in place)

**Files created by this response:**

- `docs/implementation/M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md`
  (this document)

No other repository file was modified.

---

## Scope discipline

This response resolves exactly the four Required Corrections the Independent
Review recorded — `M41-WP1-S2-IR-1` through `M41-WP1-S2-IR-4` — against
exactly the corrected artifact named above. It does not reopen the M41
architecture, does not reopen the M41-WP1 Stage 1 register, does not admit,
rename, or redefine any candidate vocabulary, does not modify ownership, and
does not expand M41's scope. It does not begin Independent Confirmation of
the corrected artifact and does not begin M41-WP2.

---

## M41-WP1-S2-IR-1 — Complete the remaining Stage 1 contract evidence

**Resolution:**

1. **Governed shorthand replaced.** Every governed use of bare "Definition"
   meaning Market Measure Definition was replaced with the full canonical
   name "Market Measure Definition" throughout the corrected artifact —
   in the title, workflow-stage line, document-role line, reliance-boundary
   text, §5.3's identity list, §5.4's field table, §5.5, §5.6, §5.8's
   worked example (including its field label), §6.3's identity list, §6.4's
   field table, §6.7's immutability invariants, §6.9's worked example,
   §7.8's worked example, §8.2's predicates, §8.4's non-exercise statement,
   §9.1–§9.2's registry invariants, §10's cross-contract consistency
   statements, and §15's completion criteria. The existing Asset Foundation
   terms "Asset Definition" and "Definition Version" were left unmodified
   everywhere they name that distinct, existing concept (e.g., §4.2, §5.7,
   §6.6, §6.8, §8.2 predicate 6, and the expanded §5.8 worked example's
   non-substitutability discussion).
2. **Exact field-level subject-shape representation supplied.** §5.4's
   "Declared subject shape" field is now closed to a non-empty subset of
   exactly the three closed shapes the confirmed Stage 1 register already
   names at
   [§6.4 (Measure Subject)](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#64-measure-subject):
   a single canonical Asset identity reference; an ordered, canonical
   reference set of two or more Asset identities; or an explicit
   market-context parameter set with no Asset identity reference. This
   reuses vocabulary Stage 1 already fixed for Measure Subject by citation;
   it does not define Measure Subject's own identity, ordering, or binding
   rules, which remain M41-WP2's obligation.
3. **Closed output-coordinate-meaning representation supplied.** §5.4's
   "Required output coordinate meaning" field is now closed to an explicit
   citation of exactly one of the four already-admitted `GLOSSARY.md`
   Valuation Semantics questions — `Identity`, `Continuous quotation`,
   `Periodic NAV`, `Appraisal-on-event` — cited by exact name only, with
   restatement, paraphrase, and "equivalent declared meaning" language
   removed. This reuses existing closed vocabulary; it admits none.
4. **Worked example expanded.** §5.8's worked example now includes an
   explicit "Identity, ownership, version-axis, and non-substitutability
   demonstration" subsection that walks through all four properties Stage 1
   required a worked example to demonstrate, contrasting the illustrative
   Market Measure Definition's identity, ownership, and revision-indicator
   version axis against Asset Definition and Definition Version by name.
5. **Exact Method Version formats supplied.** §6.4 now fixes the semantic
   version identifier as an explicit `MAJOR.MINOR.PATCH` triple of
   non-negative integers (no leading zeros other than a standalone `0`, no
   other separator or suffix), and fixes declared dependency versions as a
   list of `(dependency identifier, exact dependency version)` pairs with no
   duplicate identifiers, ordered by the single ordering model
   `M41-WP1-S2-IR-3` establishes (see below). §6.3's identity list and
   §6.9's worked example were updated to match.

**Result:** All five items closed. No new vocabulary was admitted; every
closed representation reuses either an existing `GLOSSARY.md` closed term
set (Valuation Semantics) or an already-confirmed Stage 1 closure (Measure
Subject's three shapes), or fixes an ordinary field-syntax format for a
term Stage 1 already left format-level detail to this stage.

---

## M41-WP1-S2-IR-2 — Make the frozen M40 constitutional boundary mechanically operative

**Resolution:**

1. **Explicit Event Type statements added.** §5.5 now states, as a named
   "Witnessed-versus-computed invariant," that a source-reported claim
   remains an M39 Observation carrying Event Type `Observation`, and that
   every output actually produced by invoking a Method Version is a
   Calculated Market Measure carrying Event Type `Calculation` and
   Producing Domain `Market Intelligence` — citing the existing `GLOSSARY.md`
   entries for these terms (§4.2), not redefining them.
2. **Recasting foreclosed structurally.** The same §5.5 invariant states
   that the Bound umbrella concept field (§5.4) states only the general
   semantic category a Market Measure Definition falls under in the
   abstract and MUST NOT be read as authority to reclassify what a specific
   Method Version's realized output actually is; no Market Measure
   Definition/Method Version combination may recast a source-reported claim
   as a platform calculation or vice versa. The §5.8 worked example's Bound
   umbrella concept value was changed from `Market Measure` to `Calculated
   Market Measure`, consistent with that example being carried forward into
   the §6.9 Method Version example (which is inherently computational).
3. **Output-coordinate and evaluation-rule representations closed.** §5.4's
   output-coordinate field is closed per `IR-1` item 3 above. §7.4's
   evaluation rule field is now restricted to predicates built only from
   three named, exhaustive reference categories — the declaring Method
   Version's bound Market Measure Definition's declared subject shape; the
   declaring Method Version's declared dependency versions; and the frozen
   M40 M39 Observation evidence category — combined only with ordinary
   existence, comparison, and boolean logic. Because no Ledger, Portfolio,
   Wealth Intelligence, judgment, evaluation, reputation, confidence, or
   suitability value is a permitted reference, the exclusion is now
   structural rather than a prose blacklist, making the five-part
   ownership-boundary gate mechanically decidable at the field level for
   this contract, as recorded in the added §10 bullet.
4. **Section 11 revalidated.** §11's introduction now states explicitly
   that it reflects the closed representations from these corrections. All
   three tables (§11.1–§11.3) were re-worded against the corrected field
   text (closed subject-shape and output-coordinate representations, closed
   dependency format, structurally closed evaluation-rule representation).
   A supplementary witnessed-versus-computed boundary check was added under
   §11.1 and §11.2, explicitly labeled as a separate check and not a sixth
   part of the frozen five-part gate, so the gate's own five-part structure
   is unchanged.

**Result:** All four items closed. The frozen M40 five-part gate itself was
not altered; its field-level application in §11 was strengthened, and a
separate, explicitly-labeled witnessed-versus-computed check was added
alongside it.

---

## M41-WP1-S2-IR-3 — Resolve identity and evolution consistency

**Resolution:**

1. **One dependency ordering model defined.** §6.4 now defines the single
   ordering model this document uses everywhere: declared dependency
   versions and declared Method Requirement sets are canonically ordered
   lists — dependency versions by dependency identifier, Method
   Requirements by requirement key — each in ascending code-point order,
   with no duplicate identifiers/keys permitted.
2. **Used consistently everywhere.** §6.3's canonical identity, §6.4's
   required fields, §8.2 predicate 8 (dependency resolution and
   uniqueness), and §9.2's registry invariants (referential closure,
   predicate 7) all now reference this same model by cross-reference to
   §6.4, rather than independently describing ordering. §6.9's worked
   example was updated to an empty ordered list with an explanatory note
   that an empty list is trivially in order, removing the prior
   unordered-set-brace rendering.
3. **Subject-shape identity consequence stated.** §5.6's revision
   invariants now include an explicit bullet: a revision that adds,
   removes, or otherwise changes the declared subject shape subset MUST be
   a new Market Measure Definition identifier, not a revision, because a
   bound Method Version's applicability may depend on the exact
   subject-shape subset its binding was specified against.
4. **Cross-reference corrected.** §6.9's worked example now cites `§7.8`
   (the actual Method Requirement worked example) instead of the incorrect
   `§7.6`.

**Result:** All four items closed. Dependency ordering, subject-shape
identity consequences, and the miscited cross-reference are now
unambiguous and internally consistent.

---

## M41-WP1-S2-IR-4 — Complete the future admission gate and future registry invariants

**Resolution:**

1. **Closed, exhaustive admission predicate set.** §8.2's "at minimum"
   language was removed. The predicate list now has ten closed predicates:
   field completeness; identity uniqueness; binding integrity; requirement
   well-formedness (including the evaluation rule's structural reference
   closure); the ownership-boundary gate; the non-conflation check (now
   including the exact version-format check); witnessed-versus-computed
   compliance; dependency resolution and uniqueness; cross-contract
   compatibility between a Method Version's dependencies/requirements and
   its bound Market Measure Definition's declared subject shape, output
   coordinate meaning, and permitted input categories; and Deterministic
   Calculation compliance.
2. **Framework-versus-production admission distinguished.** New §8.2a
   states explicitly that a future gate's `ADMITTED` result for a candidate
   Market Measure Definition or Method Version admits only that framework
   specification record and does not, by itself or in combination with any
   other admission, admit a Formula, named indicator, reference
   calculation, Method, or other production calculation — that requires
   separate, additional, future authority this document does not specify.
   §13's Authority Non-Leakage section was updated to state this
   non-implication explicitly.
3. **Registry invariants completed.** §9.2 now includes three additional
   invariants beyond the original four: canonical-identity uniqueness
   (rejecting, not merging, a colliding identity under different content);
   referential closure (every admitted Method Version's Market Measure
   Definition, dependency, and Method Requirement references must resolve
   within the registry); and deterministic content-equivalence (identical
   admitted-record inputs must build byte-identical registry content,
   mirroring the Deterministic Calculation property applied to the registry
   itself).

**Result:** All three items closed. The future gate and future registry
sections remain specification-only — no gate is built or run, no registry
is built or persisted, and the production Market Measure
Definition/Method Version catalog remains empty throughout M41 (§8.4, §9.3,
M41 proposal §7).

---

## Validation Performed

- **Semantic consistency:** The corrected §5.4, §6.4, §7.4 field
  representations were checked against §5.1, §6.1, and §7.2's unmodified
  exact meanings; no correction altered a Stage-1-confirmed exact
  definition.
- **Constitutional consistency:** §11's revalidated five-part gate tables
  and the new witnessed-versus-computed checks were checked against the
  frozen M40 five-part gate structure and the M40 Glossary entries for
  Market Measure, Calculated Market Measure, Event Type, and Producing
  Domain; no contract text conflicts with those frozen meanings.
- **Stage 1 consistency:** The added subject-shape citation (§5.4) was
  checked verbatim against register §6.4's three-shape closure; no Stage 1
  entry was reopened, renamed, or reinterpreted.
- **Ownership consistency:** §5.2, §6.2, and §7.3 (Market Intelligence,
  unchanged) were checked against Stage 1's recorded ownership; no
  correction altered ownership of any candidate.
- **Terminology consistency:** A full sweep for bare "Definition" shorthand
  was performed (see `IR-1` item 1); no remaining instance conflates Market
  Measure Definition with Asset Definition or Definition Version.
- **Contract completeness:** §5.4, §6.4, and §7.4 were checked against
  register §6.1–§6.3's future contract acceptance evidence obligations; all
  previously open-ended representations are now closed.
- **Identity consistency:** §5.6, §6.3, §6.4, §8.2, and §9.2 were checked
  for a single, consistently applied dependency-ordering model and complete
  identity-consequence coverage for every Market Measure Definition field.
- **Future gate completeness:** §8.2's ten predicates were checked against
  every invariant in §5.5–5.7, §6.5–6.8, and §7.5–7.7 to confirm each is
  covered.
- **Registry invariant completeness:** §9.2's eight invariants were checked
  to confirm canonical-identity uniqueness, referential closure, and
  deterministic content-equivalence are now present alongside the original
  four.
- **Repository consistency:** No file outside the two listed above was
  modified; `GLOSSARY.md`, the Decision Log, the M41 architecture, and the
  Stage 1 register were confirmed unchanged.
- **Internal cross references:** All relative links in the corrected
  artifact and in this response were checked to resolve to files present on
  disk, including the newly added self-references to
  `M41_WP1_STAGE2_INDEPENDENT_REVIEW.md` and this response document.
- **Markdown:** Heading hierarchy in the corrected artifact was checked and
  remains sequential (H1, H2 `## 1.`–`## 15.`, H3 nested correctly,
  including the new `### 8.2a`); this response document's own heading
  hierarchy is sequential.
- **`git diff --check`:** Run against the corrected artifact once staged;
  result was a single benign LF-will-be-replaced-by-CRLF notice
  (line-ending normalization consistent with the repository's existing
  convention), with no whitespace errors.

---

## Final Status

This response document resolves `M41-WP1-S2-IR-1` through `M41-WP1-S2-IR-4`
in full against
[M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md),
whose header now records status
`REQUIRED_CORRECTIONS_APPLIED_PENDING_INDEPENDENT_CONFIRMATION`.

Per the explicit stop condition governing this response: Independent
Confirmation of the corrected artifact is not begun by this document, and
M41-WP2 is not begun.
