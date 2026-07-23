# M41-WP1 Stage 2 — Final2 Required Corrections Response

**Date:** 2026-07-23

**Response role:** Implementation Author

**Governing Final Independent Confirmation:**
[M41_WP1_STAGE2_FINAL_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_FINAL_INDEPENDENT_CONFIRMATION.md)
— Final Determination `NOT CONFIRMED`

**Prior Independent Confirmation (superseded by nothing; the Final
Independent Confirmation confirmed two of its four items and left two
open):**
[M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md)

**Prior Required Corrections responses (superseded by nothing; this
document adds to them, not over them):**
[M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md),
[M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md)

**Corrected artifact:**
[M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md)

**Architecture status:** Confirmed and frozen — not reopened by this
response.

**M41-WP1 Stage 1 status:** Confirmed and frozen — not reopened by this
response.

**M41-WP1 Stage 2 status:** Author COMPLETE; Independent Review COMPLETE;
first Required Corrections COMPLETE; Independent Confirmation
`NOT CONFIRMED`; final Required Corrections COMPLETE; Final Independent
Confirmation `NOT CONFIRMED` (two items resolved, two items unresolved);
this document completes the final2 Required Corrections for the two
remaining unresolved items only.

**Implementation authority:** `NONE`

**Runtime authority:** `NONE`

**Production method authority:** `NONE`

**Provider authority:** `NONE`

**Persistence authority:** `NONE`

**API and public-exposure authority:** `NONE`

**Canonical vocabulary admission by this response:** `NONE` — §7.4b's
domain and semantics prose (e.g., "well-formed," "resolved," "not
well-formed") is ordinary descriptive language, not a proposed candidate
noun; no grammar production, operand, comparator, or connective token was
added to, removed from, or renamed in §7.4a.

**`GLOSSARY.md`:** Not modified.

**Decision Log:** Not updated.

**Graphify:** Not refreshed.

**Files modified:**
[M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md)

**Files created:** this document.

No other repository file was modified or created by this response.

---

## Scope discipline

The Final Independent Confirmation's Executive Summary and per-item
Confirmation Results state explicitly that `M41-WP1-S2-IR-1` and
`M41-WP1-S2-IR-3` are `Resolved`, and that the two remaining findings —
against `M41-WP1-S2-IR-2` and `M41-WP1-S2-IR-4` — are unresolved *portions
of those existing items*, not new findings and not architectural
recommendations. This response:

- resolves only the two remaining unresolved portions identified for
  `M41-WP1-S2-IR-2` and `M41-WP1-S2-IR-4`;
- does not reopen `M41-WP1-S2-IR-1` or `M41-WP1-S2-IR-3`, both of which the
  Final Independent Confirmation already recorded as resolved;
- does not reopen Architecture or Stage 1;
- does not redesign any contract;
- does not introduce new governed vocabulary;
- does not modify ownership;
- does not modify `GLOSSARY.md`, the Decision Log, or Graphify; and
- does not begin M41-WP2.

---

## M41-WP1-S2-IR-2 — Evaluation-rule semantics closure

**Finding (Final Independent Confirmation).** §7.4a's grammar, connective
set, comparator set, and closed operand names, together with §7.4's
prerequisite-category restrictions and §7.4a's byte-level canonical form,
make parsing and canonical-form checking mechanically decidable. Evaluation
to `TRUE`/`FALSE`, however, was not closed: the grammar admitted
operator/operand combinations whose result was undefined — for example
`(= SubjectShape 1)` or an `EXISTS` test over an integer literal — because
the specification did not fix (a) the concrete value and comparison domain
of `SubjectShape`; (b) the concrete value and comparison domain of
`Dependency(<dependency-identifier>)`; (c) the operand types each comparator
and `EXISTS` accept; or (d) the result of a syntactically valid but
type-incompatible combination.

**Resolution.**

1. A new §7.4b ("Operand value domains and expression semantics") was added
   to the specification immediately after §7.4a, before §7.5. It coins no
   candidate noun and adds, removes, or renames no grammar production,
   operand, comparator, or connective already fixed by §7.4a — the grammar
   itself is unchanged.
2. §7.4b fixes exactly one value domain per operand: `SubjectShape` is an
   enumerated domain of the three closed shape names §5.4 already names,
   valued as the shape the invocation's actual Measure Subject instantiates;
   `Dependency(<dependency-identifier>)` is a presence domain (resolved / not
   resolved, per §6.4's declared dependency versions and §8.2 predicate 8's
   dependency resolution), not a numeric or enumerated domain;
   `ObservationEvidenceCount` and `<integer-literal>` are both the
   non-negative-integer domain already implied by §7.4 and §7.4a.
3. §7.4b fixes the exact result of every `EXISTS` atom for each of the four
   operand kinds: `EXISTS(SubjectShape)` is `TRUE` iff the invocation's
   actual Measure Subject's shape is a member of the declaring Method
   Version's bound Market Measure Definition's declared subject shape subset
   (§5.4); `EXISTS(Dependency(...))` is `TRUE` iff that dependency
   identifier's operand is resolved for the invocation;
   `EXISTS(ObservationEvidenceCount)` and `EXISTS(<integer-literal>)` are
   always `TRUE`, because both operands' values are always defined.
4. §7.4b fixes comparator legality and result: a comparator atom is
   well-formed only if both operands are drawn from the non-negative-integer
   domain (`ObservationEvidenceCount` or `<integer-literal>`, in any
   combination); a comparator atom naming `SubjectShape` or
   `Dependency(...)` — domains this document defines no ordering or equality
   relation over — is grammar-conformant under §7.4a but not well-formed.
   §8.2 predicate 4 was updated to reject such an atom at admission, on the
   same "checkable from the field's concrete string value alone" basis as
   grammar conformance, exactly as it already rejected an ungrammatical
   string. This is the defined result of every type-incompatible expression
   the grammar's syntax otherwise admits: a fixed rejection at admission,
   never an undefined or implementation-invented runtime result. A
   well-formed comparator atom evaluates using ordinary integer comparison.
5. §7.4b fixes `AND`/`OR`/`NOT` as ordinary boolean connectives over their
   sub-predicates' already-determined results.
6. §8.2 predicate 4 ("Requirement well-formedness") was reworded to cite
   §7.4b's operand-domain well-formedness check alongside §7.4a's grammar
   conformance and canonical form.
7. §11.3's "Output meaning" row and §7.4a's own closing paragraph were left
   consistent with §7.4b: the binary `TRUE`/`FALSE` guarantee now rests on
   §7.4a's grammar together with §7.4b's semantics, not on grammar closure
   alone.

**Result.** Every grammar-conformant evaluation rule string now has a fully
defined, mechanically decidable outcome: it is either well-formed and
evaluates, for any concrete invocation state, to exactly one of `TRUE` or
`FALSE` (mapping to `MET`/`UNMET`, §7.5), or it is not well-formed and is
rejected at admission before any evaluation is attempted. No
grammar-conformant string is left with an undefined or
implementation-invented result. No new governed vocabulary was introduced;
the grammar itself was not redesigned.

---

## M41-WP1-S2-IR-4 — Predicate 12 completeness

**Finding (Final Independent Confirmation).** §8.2 predicate 12 checked only
the binary `TRUE`/`FALSE`-to-`MET`/`UNMET` mapping and specification-time
declaration. It did not require that an `UNMET` result render the declaring
Method Version inapplicable, and it did not prohibit fallback, substitution,
or a partial-applicability consequence — the §7.5 fail-closed consequence
therefore remained unenforced by the admission predicate. The finding also
noted predicate 12 relied on an evaluation-semantics closure that `IR-2`
had not yet supplied.

**Resolution.**

1. §8.2 predicate 12 was rewritten into four explicit sub-requirements,
   each restating one applicable §7.5 invariant rather than leaving it
   implicit:
   - (a) binary `TRUE`/`FALSE` evaluation, now grounded in §7.4a's grammar
     together with §7.4b's operand value domains and expression semantics
     (closed by this response's resolution of `IR-2`, above) — no third
     value constructible;
   - (b) binary `MET`/`UNMET` mapping, with no confidence score or
     partial-satisfaction value admitted;
   - (c) an `UNMET` result for any one Method Requirement in the
     candidate's declared set renders the candidate Method Version
     inapplicable to that invocation in its entirety, and the candidate's
     fields and declared set contain no fallback rule, no substitute Method
     Version or calculation path, and no partial-applicability outcome that
     would apply instead of that consequence — fallback, substitution, and
     partial applicability are each explicitly prohibited;
   - (d) the declared Method Requirement set is fixed at Method Version
     specification time (§6.7) and contains no field, reference, or
     mechanism by which a requirement could be inferred, added, altered,
     weakened, or bypassed at invocation time.
2. Because predicate 12's sub-requirement (a) now rests on §7.4b's closed
   evaluation semantics (this response's `IR-2` resolution), predicate 12 no
   longer depends on an unresolved evaluation-semantics premise.
3. No other predicate in §8.2 was changed. §8.2a (framework admission is not
   production-method admission) was re-checked and is unchanged; the
   separation between framework-record admission and production-method
   admission is preserved exactly as before.

**Result.** §8.2 predicate 12 now completely enforces every invariant §7.5
states: binary evaluation, binary mapping, the fail-closed inapplicability
consequence of an `UNMET` result, the prohibition on fallback, substitution,
and partial applicability, and specification-time-only declaration with no
invocation-time inference. The admission predicate set (predicates 1–12)
remains closed and exhaustive; no predicate was removed, and only predicate
4 and predicate 12's wording were changed.

---

## Validation Performed

- **Grammar completeness:** §7.4a's grammar (productions, connectives,
  comparators, operand names) was checked to confirm it is byte-for-byte
  unchanged from the prior final round; §7.4b adds semantics only.
- **Evaluation semantics completeness:** Every operand kind, every `EXISTS`
  case, every comparator well-formedness case, and every connective was
  checked to have an explicit, stated result; no case was left implicit.
- **Mechanical decidability:** For any concrete evaluation rule string and
  any concrete invocation state, grammar conformance (§7.4a), canonical form
  (§7.4a), operand-domain well-formedness (§7.4b), and — for well-formed
  rules — the `TRUE`/`FALSE` result (§7.4b) are each checkable without
  invoking judgment or inventing a case; a not-well-formed rule is rejected
  at admission (predicate 4), never left to an undefined runtime outcome.
- **Predicate completeness:** §8.2 predicate 12 was checked line-by-line
  against every bullet in §7.5 to confirm each is separately and explicitly
  enforced (binary evaluation; binary mapping; fail-closed inapplicability;
  no fallback; no substitution; no partial applicability;
  specification-time-only declaration; no invocation-time inference);
  predicate 4 was checked to confirm it now also enforces §7.4b's
  well-formedness restriction.
- **Stage 1 consistency:** §5.4, §6.3, and §6.4's already-confirmed
  vocabulary were checked; §7.4b introduces no reference to any Stage 1 term
  beyond what §7.4 and §7.4a already cited (declared subject shape,
  declared dependency versions, dependency resolution).
- **Architecture consistency:** The M41 architecture proposal's requirement
  that M41-WP1 specify "the specification of a future method-admission
  gate," not exercise it, was rechecked against §8's unchanged non-exercise
  statement; §7.4b and the predicate 12 rewrite add specification detail
  only, admitting no candidate.
- **Repository consistency:** `git status --short` was checked before and
  after this response's edits; only the corrected specification file and
  this new document changed.
- **Markdown:** Heading hierarchy checked — `### 7.4b` is nested correctly
  between `### 7.4a` and `### 7.5`; no skipped or duplicated heading level.
- **Cross references:** All relative links in this document and the new
  §7.4b/predicate-12 text (`M41_WP1_STAGE2_FINAL_INDEPENDENT_CONFIRMATION.md`,
  `M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md`,
  `M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md`,
  `M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md`,
  `M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md`)
  resolve to files that exist on disk.
- **`git diff --check`:** Run against both the corrected specification file
  and this document once staged; both report only the benign
  `LF will be replaced by CRLF` notice, no whitespace errors.

---

## Final Status

`M41-WP1-S2-IR-2` and `M41-WP1-S2-IR-4` are resolved in full. Combined with
the Final Independent Confirmation's own record that `M41-WP1-S2-IR-1` and
`M41-WP1-S2-IR-3` are resolved, all four original Required Correction items
and their subsequently identified unresolved portions are now addressed in
the corrected specification
([status field](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md):
`FINAL2_REQUIRED_CORRECTIONS_APPLIED_PENDING_INDEPENDENT_CONFIRMATION`).

This document does not itself begin, and expressly defers, a further
Independent Review or Independent Confirmation. M41-WP2 is not begun.
