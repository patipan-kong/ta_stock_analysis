# Definition Review Checklist

_The eight gates of [asset_definition_authoring_guide.md](asset_definition_authoring_guide.md), as a pass/fail form. One copy per definition under review, attached to the milestone or PR that admits it. Every item must be checked before a definition is merged; an unchecked item is a blocked admission, not a note for later._

---

## Before writing

- [ ] **1. Vocabulary complete?** Every axis the kind must declare (unit, acquisition, settlement, valuation, flows, event families, existence) has an existing word in `vocabulary.py` that honestly fits. If not, a governed vocabulary extension ([asset_definitions.md](../architecture/asset_definitions.md) §8.1 Step 2) has already shipped, with its own DECISION_LOG entry, before this checklist is opened. *(Guide Stage 0)*

- [ ] **2. D1 satisfied?** The single declaration this kind makes that no existing current-rung definition makes is stated precisely — axis and value — and checked against every entry in `library.DEFINITION_LADDERS`, not a sample. *(Guide Stage 1)*

- [ ] **3. Duplicate analysis completed?** The individuating declaration from item 2 has been confirmed to actually produce a distinct `canonical_payload()` — not assumed from the axis name alone. If the new definition and its nearest neighbor are compared axis-by-axis, exactly the individuating axis differs (or, if more differ, each extra difference is independently argued in the document, not incidental). *(Guide Stage 1)*

## Writing the document

- [ ] **4. Declaration valid?** The document follows [asset_definition_library.md](asset_definition_library.md) §3.2's nine-part shape and §3.3's style laws: every declaration argued (not asserted), absences explained with the same care as presences, no proper nouns, no speculative grants, version scope named where a known future question is deliberately deferred. *(Guide Stage 2)*

- [ ] **5. Governance review passed?** A second reader has confirmed: no formula, no code, no metadata, no classification, no judgment appears anywhere in the document; nothing in the declarations required a change to the declaration model itself (no new field, no scalar-to-set widening, no relaxed constraint) — any such need is a different milestone with a different, explicit brief. *(Guide Stage 3)*

## Wiring the runtime

- [ ] **6. Fingerprint pinned?** The transcription is added to `library.DEFINITION_LADDERS`; its fingerprint is computed via `fingerprint.compute_fingerprint()` against the real transcription object (never hand-computed) and copied into `library.PINNED_FINGERPRINTS` in the same change. *(Guide Stage 4)*

- [ ] **7. Runtime projection verified?** `DefinitionRegistry.build()` succeeds with the new definition present; `exists(binding)` is `True`; `BindingResolver.resolve(binding)` returns a `CapabilityView`; every row of the document's Capability Projection table has been checked against `CapabilityView`'s accessors and `GovernanceProjection.as_dict()` and matches. A tampered fingerprint for this binding causes boot to fail (proves the pin in item 6 is load-bearing, not decorative). *(Guide Stage 5)*

## Downstream consequences

- [ ] **8. Readiness transition expected — and correct?** `readiness_report.DEFINITION_READINESS`'s row for this binding is updated to `DEFINED` with empty `missing_requirements`, and `test_defined_status_matches_library_ladders` confirms the row agrees with `library.DEFINITION_LADDERS` in both directions. *(Guide Stage 6)*

- [ ] **9. Enforcement decision reviewed?** `enforcement_decisions.py`'s row for this binding has been re-read against the now-closed capability gap and its `gap_type`/`rationale` updated if stale — but `future_action` is left exactly where it was (never promoted past `MIGRATE` by an authoring change alone). A separate, explicit R2 authorization is the only thing that may promote `future_action`. *(Guide Stage 7)*

## Regression

- [ ] **10. Existing definitions unchanged?** Every previously-canonical definition's declarations and pinned fingerprint are byte-identical to before this change — a new definition's admission touches zero bytes of any existing one.

- [ ] **11. Generic framework tests pass?** `test_asset_definition_authoring_framework.py` passes with the new definition present, unmodified — if it needed editing to accommodate the new definition, the tests were not actually generic and that is itself a defect to fix.

- [ ] **12. DECISION_LOG updated?** An entry records what was admitted, the individuating declaration, the fingerprint, and any downstream table (readiness, enforcement) that changed as a consequence.

---

## Related Documents

- [asset_definition_authoring_guide.md](asset_definition_authoring_guide.md) — the narrative workflow this checklist compresses
- [asset_definition_library.md](asset_definition_library.md) — the library's own authoring process (§3)
- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution these gates enforce
