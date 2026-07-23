# M41-WP1 Stage 2 — Market Measure Definition, Method Version, and Applicability Contract Specification Independent Confirmation

**Date:** 2026-07-23

**Confirmation role:** Independent Confirmation Board

**Artifact confirmed:** [M41-WP1 Stage 2 — Market Measure Definition, Method
Version, and Applicability Contract Specification](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md)

**Required Corrections response verified:**
[M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md)

**Governing Independent Review:**
[M41_WP1_STAGE2_INDEPENDENT_REVIEW.md](M41_WP1_STAGE2_INDEPENDENT_REVIEW.md)

**Architecture status:** Confirmed and frozen — not reopened

**M41-WP1 Stage 1 status:** Confirmed and frozen — not reopened

**Implementation authority:** `NONE`

---

## Executive Summary

The corrected Stage 2 specification was checked only against Required
Corrections `M41-WP1-S2-IR-1` through `M41-WP1-S2-IR-4` from the governing
Independent Review. Several requested corrections are present: canonical
terminology is substantially restored; the output-coordinate, semantic
version, and dependency field formats are supplied; the worked examples and
cross-reference are corrected; the witnessed-versus-computed rule is stated;
the future framework/production admission distinction is explicit; and
additional registry invariants are recorded.

Independent Confirmation cannot complete, however, because the revised text
does not fully close four requirements already stated by the Independent
Review. These are unresolved portions of `IR-1`, `IR-2`, `IR-3`, and `IR-4`;
they are not new findings or architectural recommendations.

---

## Confirmation Results

### M41-WP1-S2-IR-1 — Not fully resolved

Canonical terminology, the closed output-coordinate representation, the
semantic-version format, the dependency-declaration format, and the expanded
worked example are present.

The exact subject-shape correction remains internally contradictory.
Section 5.4 supplies the three closed Stage 1 shapes, but section 12 still
states that “Measure Subject's exact subject-shape vocabulary” is deferred to
M41-WP2. The governing review identified that same deferral as the reason the
Stage 1 evidence was incomplete. Consequently, the revised specification
both supplies and expressly disclaims supplying the required exact
subject-shape vocabulary.

### M41-WP1-S2-IR-2 — Not fully resolved

Sections 5.5, 8.2, and 11 now state the witnessed-versus-computed invariant,
including Event Type `Observation` for source-reported M39 Observation
claims and Event Type `Calculation` with Producing Domain `Market
Intelligence` for Method Version outputs. Section 11 also records renewed
gate results.

The Method Requirement evaluation-rule representation is not yet
mechanically closed. Section 7.4 permits “ordinary existence, comparison,
and boolean-combination logic” without defining an exact predicate grammar,
operator set, operand/value representation, or canonical form, and section
7.8 instantiates the field as natural-language prose. A mechanical validator
therefore cannot decide from the concrete field value alone whether the rule
uses only the permitted constructs. The field-level mechanical-decidability
requirement in `IR-2` item 3, and thus the section 11 revalidation dependent
on it, remains unresolved.

### M41-WP1-S2-IR-3 — Not fully resolved

Sections 6.3 and 6.4 define one dependency-list ordering rule; section 8.2
predicate 8 and the worked example use it. Section 5.6 now states the
identity consequence of a subject-shape change, and the worked-example
cross-reference now points to section 7.8.

The required consistent application to the future registry invariants is
missing. Section 9.2 invariant 7 requires dependency references to resolve,
but it neither requires the dependency list to use section 6.4's ascending
code-point order nor cross-references that ordering model. This leaves the
specific registry-invariant portion of `IR-3` item 1 unresolved.

### M41-WP1-S2-IR-4 — Not fully resolved

Section 8.2 removes “at minimum” and provides ten predicates. Section 8.2a
separates framework-record admission from Formula, Method, named-indicator,
reference-calculation, and other production-calculation admission. Section
9.2 adds identity, referential-closure, and deterministic-content language.

The admission predicate set is labeled exhaustive but does not enforce every
applicable invariant in sections 5–7 as the governing correction requires.
In particular, it contains no predicate applying the Market Measure
Definition revision rules in section 5.6 and no predicate enforcing the
Method Requirement evaluation invariants in section 7.5, including the
binary `MET`/`UNMET` result and fail-closed inapplicability consequence.

The canonical-identity registry invariant is also incomplete as written.
Section 9.2 invariant 6 rejects two records sharing an identity only when
they carry different field content; it does not prohibit two admitted
records with the same canonical identity and identical content. It therefore
supplies conflicting-duplicate rejection but not the unconditional
canonical-identity uniqueness required by `IR-4` item 3.

---

## Repository Validation

- The Architecture and Stage 1 governing artifacts were used only as frozen
  authority and were not edited by this confirmation.
- No M41-WP2 artifact exists in the repository; WP2 has not begun.
- `docs/GLOSSARY.md`, the M34 Decision Register, and `graphify-out/` have no
  current Git status entry.
- Graphify was queried read-only for repository navigation and was not
  refreshed.
- The worktree has no unstaged changes. The repository retains pre-existing
  staged and untracked M41 documentation artifacts; this confirmation does
  not alter their staging state.
- `git diff --check` and `git diff --cached --check` report no whitespace
  errors.
- This confirmation document is the only repository file created by the
  Independent Confirmation Board. No implementation, runtime, provider,
  persistence, API, production catalog, Decision Log, Glossary, or Graphify
  artifact was created or modified.

---

## Final Determination

NOT CONFIRMED
