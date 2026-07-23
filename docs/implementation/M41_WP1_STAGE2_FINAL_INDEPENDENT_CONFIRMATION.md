# M41-WP1 Stage 2 — Final Independent Confirmation

**Date:** 2026-07-23

**Confirmation role:** Independent Confirmation Board

**Artifact confirmed:** [M41-WP1 Stage 2 — Market Measure Definition, Method
Version, and Applicability Contract
Specification](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md)

**Final Required Corrections response verified:**
[M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md)

**Previous Independent Confirmation:**
[M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md)

**Architecture status:** Confirmed and frozen — not reopened

**M41-WP1 Stage 1 status:** Confirmed and frozen — not reopened

**Implementation authority:** `NONE`

---

## Executive Summary

This confirmation considered only the unresolved portions of
`M41-WP1-S2-IR-1` through `M41-WP1-S2-IR-4` recorded by the previous
Independent Confirmation.

The final correction pass resolves the subject-shape contradiction in
`IR-1` and applies one dependency ordering model consistently through every
location required by `IR-3`. It also resolves the registry-invariant and
framework-versus-production-admission portions of `IR-4`.

Confirmation cannot complete because two previously identified requirements
remain unresolved. The Method Requirement grammar closes syntax but does not
completely define the evaluation semantics of the permitted operator/operand
combinations, so evaluation is not mechanically decidable for every
grammar-conforming rule. In addition, admission predicate 12 does not enforce
the fail-closed applicability consequence required by §7.5. These are
unresolved portions of the existing `IR-2` and `IR-4` items, not new
findings.

---

## Confirmation Results

### M41-WP1-S2-IR-1 — Resolved

Sections 5.4 and 12 now state one consistent boundary. Section 5.4 closes the
declared subject-shape field to a non-empty subset of exactly the three
shapes confirmed by Stage 1. Section 12 no longer defers that vocabulary; it
defers only construction, serialization, identity, binding, and canonical
ordering of an actual Measure Subject record to M41-WP2.

The prior internal contradiction is eliminated. Stage 2 neither adds a
fourth shape nor redefines the three confirmed shapes.

### M41-WP1-S2-IR-2 — Not fully resolved

Section 7.4a now supplies a closed prefix grammar, a finite connective and
comparator set, closed operand names, prerequisite-category restrictions,
and a byte-level canonical representation. Section 7.4 also closes permitted
references, and §11 re-applies the five-part ownership gate against those
restricted references. The prohibited Ledger, Portfolio, Wealth, and
judgment inputs remain mechanically excluded because no corresponding
operand is constructible.

The evaluation semantics are not completely closed, however. The grammar
permits operator/operand combinations whose result is not defined, including
comparisons such as `(= SubjectShape 1)` and existence tests over integer
literals. It does not define:

- the concrete value and comparison domain of `SubjectShape`;
- the concrete value and comparison domain of
  `Dependency(<dependency-identifier>)`;
- the operand types accepted by `EXISTS` and by each comparator; or
- the result of a syntactically valid but type-incompatible combination.

Consequently, parsing and canonical-form checking are mechanically
decidable, but evaluation to `TRUE` or `FALSE` is not mechanically decidable
for every string the grammar admits. The previous confirmation's
mechanical-decidability requirement remains unresolved. The five-part
ownership gate itself remains mechanically checkable because the permitted
reference set is closed.

### M41-WP1-S2-IR-3 — Resolved

Section 6.4 defines exactly one ordering model: ascending code-point order by
dependency identifier. Section 6.3 applies it to Method Version identity,
§6.4 applies it to required fields, §8.2 predicate 8 applies it at admission,
and §9.2 invariant 7 requires the registry to preserve it unchanged.

No competing dependency ordering model remains in the reviewed
specification.

### M41-WP1-S2-IR-4 — Not fully resolved

Section 8.2 predicate 11 now enforces the §5.6 Market Measure Definition
revision constraints. Section 8.2a continues to separate framework-record
admission from Formula, Method, named-indicator, reference-calculation, and
other production-calculation admission.

Section 9.2 now contains all four registry properties required by the
previous confirmation:

- unconditional canonical-identity uniqueness;
- full referential closure;
- preservation of the single dependency ordering model; and
- deterministic content equivalence.

Section 8.2 predicate 12 does not completely enforce §7.5. It checks binary
`TRUE`/`FALSE` to `MET`/`UNMET` mapping and specification-time declaration,
but it does not require an `UNMET` result to make the declaring Method
Version inapplicable, and it does not prohibit fallback, substitution, or a
partial-applicability consequence. The §7.5 fail-closed consequence
identified by the previous confirmation therefore remains unenforced by the
admission predicate.

Predicate 12 also relies on §7.4a's assertion that every grammar-conforming
rule evaluates to one binary result; the unresolved evaluation-semantics
closure under `IR-2` prevents that assertion from being mechanically
established for every admitted rule.

---

## Repository Validation

- The frozen Architecture and WP1 Stage 1 authorities were used only as
  governing context and were not reopened or edited by this confirmation.
- The final correction pass introduces predicate syntax only as ordinary
  non-canonical language; no new governed vocabulary is admitted.
- No M41-WP2 artifact exists in the repository; WP2 has not begun.
- `docs/GLOSSARY.md`, Decision Log artifacts, and `graphify-out/` have no
  current Git status entry.
- Graphify was queried read-only for repository context and was not
  refreshed.
- Before this confirmation document was created, the worktree had no
  unstaged changes. The repository retains pre-existing staged and untracked
  M41 documentation artifacts; this confirmation does not alter their
  staging state.
- `git diff --check` and `git diff --cached --check` report no whitespace
  errors.
- This confirmation document is the only repository file created or
  modified by the Independent Confirmation Board. No implementation,
  runtime, provider, persistence, API, catalog, Glossary, Decision Log,
  Graphify, or WP2 artifact was created or modified.

---

## Final Determination

NOT CONFIRMED
