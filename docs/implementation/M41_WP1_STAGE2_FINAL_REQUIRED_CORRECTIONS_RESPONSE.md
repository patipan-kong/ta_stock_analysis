# M41-WP1 Stage 2 — Market Measure Definition, Method Version, and
# Applicability Contract Specification
# Final Required Corrections Response

**Date:** 2026-07-23

**Response role:** Implementation Author

**Governing Independent Confirmation:**
[M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md](M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md)
— Final Determination `NOT CONFIRMED`.

**Governing Independent Review:**
[M41_WP1_STAGE2_INDEPENDENT_REVIEW.md](M41_WP1_STAGE2_INDEPENDENT_REVIEW.md)
— `APPROVED WITH REQUIRED CORRECTIONS`.

**First Required Corrections Response (superseded by nothing; this document
adds to it, not over it):**
[M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md](M41_WP1_STAGE2_REQUIRED_CORRECTIONS_RESPONSE.md).

**Artifact corrected:**
[M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md](M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md).

**Architecture status:** `CONFIRMED`, `FROZEN` — not reopened.

**WP1 Stage 1 status:** `CONFIRMED`, `FROZEN` — not reopened.

**WP1 Stage 2 status:** Author `COMPLETE`; Independent Review `COMPLETE`;
first Required Corrections `COMPLETE`; Independent Confirmation
`NOT CONFIRMED`; this document resolves the four unresolved items that
determination identified.

**Implementation authority:** `NONE`

**Canonical vocabulary admission by this response:** `NONE` — no new
candidate noun is introduced; §7.4a's grammar tokens are ordinary,
non-governed predicate syntax, consistent with §4.3's existing treatment of
descriptive contract phrases as non-canonical.

**`GLOSSARY.md`:** Not modified. **Decision Log:** Not updated.
**Graphify:** Not refreshed.

**Files modified:**
`docs/implementation/M41_WP1_DEFINITION_METHOD_VERSION_APPLICABILITY_CONTRACT_SPECIFICATION.md`.

**Files created:** this document.

No other repository file was modified.

---

## Scope discipline

The Independent Confirmation is explicit that its four findings are
unresolved portions of the *existing* Required Corrections
`M41-WP1-S2-IR-1` through `-IR-4` — not new findings and not architectural
recommendations. This response accordingly:

- does not reopen Architecture or Stage 1;
- does not redesign any contract's scope, ownership, or admitted candidate
  set;
- does not introduce new governed vocabulary — the evaluation-rule grammar
  added below is ordinary predicate syntax (`AND`, `OR`, `NOT`, `EXISTS`,
  comparators, and three closed operand names), not a candidate noun,
  consistent with Stage 1's own treatment of similar descriptive phrases
  ([register §6.0](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#60-complete-noun-inventory));
- does not modify ownership;
- resolves exactly the four items the Independent Confirmation identified as
  unresolved, and nothing else.

---

## M41-WP1-S2-IR-1 — internal contradiction on subject-shape vocabulary

**Finding:** §5.4 supplied the three closed Stage 1 subject shapes, while
§12 still stated that "Measure Subject's exact subject-shape vocabulary" was
deferred to M41-WP2 — the same deferral the original Independent Review had
identified as the reason Stage 1 evidence was incomplete.

**Resolution:**

1. §12's bullet was rewritten. It no longer names any "subject-shape
   vocabulary" as deferred. It instead names precisely what remains
   M41-WP2's obligation: Measure Subject's own **record structure, identity,
   and binding rule** — i.e., how an actual Measure Subject value is
   constructed, serialized, and (for the ordered-reference-set shape)
   canonically ordered.
2. The rewritten bullet explicitly distinguishes this from §5.4's declared
   subject shape field, which only *cites*, by name, which of the three
   already-named Stage 1 shapes a Market Measure Definition requires — a
   closed citation, not a definition of Measure Subject's own structure.
3. §5.4's table cell for "Declared subject shape" was left unchanged (it
   already made this same distinction: "it does not itself define Measure
   Subject's own identity, ordering, or binding rules (M41-WP2)"), so the
   specification now states one consistent position throughout: the *set of
   permitted shapes* is closed and supplied by citation (§5.4); the
   *construction, identity, and ordering* of an actual Measure Subject value
   under a chosen shape remains M41-WP2's exclusive, still-deferred
   obligation.

**Result:** No section of the corrected specification both supplies and
disclaims the same vocabulary. The Stage 2 / WP2 boundary is preserved
without reintroducing ambiguity.

---

## M41-WP1-S2-IR-2 — Method Requirement evaluation-rule mechanical closure

**Finding:** §7.4 permitted "ordinary existence, comparison, and
boolean-combination logic" without an exact predicate grammar, operator set,
operand representation, or canonical form; §7.8's worked example
instantiated the field as natural-language prose. A mechanical validator
could not decide, from the field's concrete value alone, whether a given
evaluation rule used only permitted constructs.

**Resolution:**

1. A new **§7.4a "Evaluation rule closed grammar and canonical form"**
   subsection was added, defining an exact, closed grammar for the
   evaluation rule field:
   - three closed operand kinds only: `SubjectShape`, `Dependency(<id>)`,
     `ObservationEvidenceCount` (plus non-negative integer literals), each
     gated to the corresponding Prerequisite category exactly as before;
   - a closed connective set (`AND`, `OR`, `NOT`) and comparator set (`=`,
     `!=`, `>`, `<`, `>=`, `<=`);
   - a fixed prefix-notation production grammar (`<predicate>`, `<atom>`,
     `<comparator>`, `<operand>`) that admits no other token, reference, or
     vocabulary;
   - a canonical-form rule: exactly one space as every token separator, no
     other whitespace or formatting variance, so two semantically identical
     rules must be byte-identical.
2. §7.4's required-fields table cell for "Evaluation rule" was rewritten to
   reference §7.4a's grammar directly, replacing the prior open-ended
   "ordinary ... logic" language.
3. §7.8's worked example was rewritten from natural-language prose
   (`"at least one M39 Observation evidence record exists..."`) to the
   grammar-conformant string `(>= ObservationEvidenceCount 1)`, with an
   added explanation of why it conforms and how it evaluates.
4. §7.4a states explicitly that every atom and predicate evaluates to
   exactly `TRUE`/`FALSE`, mapped one-to-one to `MET`/`UNMET` (§7.5), making
   §7.5's binary result and fail-closed consequence a guarantee of the
   field's closed form rather than a separate prose assertion.
5. §8.2 predicate 4 ("Requirement well-formedness") was reworded to check
   grammar conformance and canonical form under §7.4a, checkable from the
   field's concrete string value alone.
6. §11.3's five-part gate table (Permitted inputs, Output meaning,
   Prohibited Ledger/Portfolio/Wealth inputs, Prohibited judgment semantics
   rows) was revalidated against the corrected field, citing §7.4a's closed
   operand and token set directly rather than the prior looser "structurally
   restricted to references" language.
7. §4.3's ordinary-non-canonical-language list was extended to name the
   grammar's own syntax tokens explicitly, confirming none is a proposed
   candidate noun.

**Result:** The evaluation rule field is now mechanically checkable —
grammar conformance and canonical-form byte-identity are decidable from the
field's concrete value alone, with no reference to any actual invocation.
§11 has been revalidated against the corrected field.

---

## M41-WP1-S2-IR-3 — dependency ordering consistency in registry invariants

**Finding:** §6.3/§6.4 defined one dependency-list ordering rule (ascending
code-point order by dependency identifier), used by §8.2 predicate 8 and the
worked example, but §9.2 invariant 7 (referential closure) neither required
registry-held dependency/requirement lists to retain that order nor
cross-referenced the ordering model — leaving the registry-invariant portion
of `IR-3` item 1 unresolved.

**Resolution:**

§9.2 invariant 7 was extended with an explicit clause: every admitted
record's declared dependency versions list and declared Method Requirement
set held in the registry MUST retain, unchanged, the exact
ascending-code-point ordering model §6.4 fixes — cross-referencing §6.3,
§6.4, and §8.2 predicate 8 by name — and the registry MUST NOT reorder,
re-sort, or otherwise store either list under a different ordering than the
admitted record carried through the gate.

**Result:** There is exactly one dependency ordering model defined in this
document (§6.4), and it is now referenced consistently everywhere a
dependency or requirement list appears: Method Version identity (§6.3), the
required-fields table (§6.4), the admission gate (§8.2 predicate 8), and the
future registry invariants (§9.2 invariant 7).

---

## M41-WP1-S2-IR-4 — admission gate and registry invariant completeness

**Finding:** The ten-predicate admission gate contained no predicate
enforcing the Market Measure Definition revision rules (§5.6) or the Method
Requirement evaluation invariants (§7.5), so it was not truly exhaustive;
and §9.2 invariant 6 rejected colliding canonical identities only when field
content differed, not when it was identical — supplying conflicting-duplicate
rejection but not unconditional canonical-identity uniqueness.

**Resolution:**

1. Two new closed predicates were added to §8.2, bringing the set to twelve:
   - **Predicate 11 (Revision compliance)** — for a candidate sharing a
     Market Measure Definition identifier with an already-admitted lower
     revision, the candidate's fields MUST differ only by an additive or
     narrowing amendment; a candidate that changes the bound umbrella
     concept, output coordinate meaning, a permitted-input category, or the
     declared subject shape subset fails as a revision (though it may still
     be admissible under a new identifier) — enforcing §5.6 at the gate.
   - **Predicate 12 (Requirement evaluation invariant compliance)** — every
     declared Method Requirement is confirmed, beyond predicate 4's grammar
     check, to evaluate to exactly `TRUE`/`FALSE` mapping to `MET`/`UNMET`
     with no third value, and to be declared only at specification time —
     enforcing §7.5 at the gate.
2. §8.2 predicate 2 (Identity uniqueness) and §9.2 invariant 6
   (canonical-identity uniqueness) were both reworded to reject any
   colliding canonical identity **unconditionally** — including when the
   colliding records' content is otherwise identical — removing the prior
   "under a different meaning" / "different field content" qualifier that
   left identical-content duplicates admissible.
3. §8.2's intro sentence ("closed, exhaustive set... no fewer... a future
   chartering milestone MAY NOT substitute a smaller or open-ended set")
   was left unchanged in force and now covers all twelve predicates, each
   still traced to an invariant already fixed by §5–§7.
4. §8.2a (framework admission is not production-method admission) was
   re-checked and left unmodified — it already stated the required
   non-implication explicitly and remains structurally separate from the
   predicate list, so the framework/production-admission separation the
   Independent Confirmation required to be preserved is unchanged.
5. §14 and §15 were updated to record this final round and its status.

**Result:** The admission gate now enforces every applicable invariant from
§5.6 and §7.5 in addition to §5.4/§6.4/§7.4's field-level and §6.5's
Deterministic Calculation invariants, and is exhaustive over all of §5–§7.
Canonical-identity uniqueness is unconditional at both the gate and the
registry-invariant level. The framework-versus-production-admission
separation is preserved unchanged.

---

## Validation Performed

- **Semantic consistency:** §5.4/§12's subject-shape statements, §7.4/§7.4a's
  evaluation-rule statements, and §8.2/§9.2's ordering and identity
  statements were each checked pairwise for contradiction; none remains.
- **Constitutional consistency:** The corrected fields and predicates were
  checked against the frozen M40 five-part gate and against `M34-D-0005`'s
  Event Type / Producing Domain boundary; no correction alters that
  boundary, and §5.5's witnessed-versus-computed invariant is unchanged.
- **Stage 1 consistency:** §5.4's subject-shape citation was re-checked
  verbatim against register §6.4's three-shape closure; the correction to
  §12 removes a contradiction without altering or reinterpreting the
  register's own text.
- **Contract completeness:** §7.4/§7.4a now supply the exact evaluation-rule
  grammar and canonical form register §6.3's future contract acceptance
  evidence obligation required; no other field's closure was reopened.
- **Identity consistency:** §5.3, §5.6, §6.3, §6.4, §8.2, and §9.2 were
  checked together; the dependency ordering model and the canonical-identity
  uniqueness rule are each now stated once and referenced consistently
  everywhere they apply.
- **Gate completeness:** §8.2's twelve predicates were checked against every
  invariant stated in §5.4–5.7, §6.4–6.8, and §7.4–7.7; none is left
  unenforced by the gate.
- **Registry invariant completeness:** §9.2's eight invariants were checked
  to confirm ordering inheritance (invariant 7) and unconditional identity
  uniqueness (invariant 6) are both present and cross-reference the sections
  that define them.
- **Terminology consistency:** No new governed noun was introduced; §7.4a's
  grammar tokens were checked against §4.3's ordinary-non-canonical-language
  treatment and against §4's provenance table.
- **Repository consistency:** No file outside the two listed above was
  modified; `git status` was reviewed to confirm no unintended changes.
- **Internal cross references:** All new and modified links
  (`M41_WP1_STAGE2_INDEPENDENT_CONFIRMATION.md`,
  `M41_WP1_STAGE2_FINAL_REQUIRED_CORRECTIONS_RESPONSE.md`, and existing
  targets) were checked to resolve to files present on disk; §7.4/§7.4a and
  §8.2 predicate cross-references were checked for correct numbering after
  the insertion of predicates 11–12.
- **Markdown:** Heading hierarchy was checked; the new `### 7.4a` subsection
  nests correctly under `## 7.`, alongside the existing `### 8.2a` under
  `## 8.`, with no skipped or duplicated levels.
- **`git diff --check`:** Run against both this file and the corrected
  specification once staged; only the repository's standard benign
  `LF will be replaced by CRLF` notice was reported for each — no whitespace
  errors.

---

## Final Status

All four items the Independent Confirmation identified as unresolved —
`M41-WP1-S2-IR-1` through `M41-WP1-S2-IR-4` — are resolved in full by this
revision. The corrected specification's status field now reads
`FINAL_REQUIRED_CORRECTIONS_APPLIED_PENDING_INDEPENDENT_CONFIRMATION`.

Per the governing task instruction, this document does not itself begin a
further Independent Review or a further Independent Confirmation of the
corrected specification, and M41-WP2 is not begun. No repository file other
than the corrected specification and this response was modified.
