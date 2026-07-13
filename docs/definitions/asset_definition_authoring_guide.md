# Asset Definition Authoring Guide

_The governed workflow for admitting a new canonical Asset Definition to [the library](asset_definition_library.md). Chartered by [asset_definitions.md](../architecture/asset_definitions.md) §8.1's evolution ladder and §3.1's two authoring gates; this guide operationalizes both into the concrete stages a real milestone walks, tool by tool, using ETF's actual authoring run (M15–M18) as the worked example throughout._

| | |
|---|---|
| **Scope** | Process only — no vocabulary, no declaration model, no runtime, no enforcement change |
| **Status** | Governance document (M19) |
| **Companion** | [definition_review_checklist.md](definition_review_checklist.md) — the same eight gates as a pass/fail form |
| **Reference implementation** | ETF v1 (M18) — the first definition admitted after the Runtime architecture existed |

---

## 1. Why this guide exists

CASH and EQUITY were authored alongside the mechanism that consumes them (M8) — their authoring and the runtime's design were one act. ETF was the first definition authored *after* the runtime was already load-bearing, and its path was not straight: M15 misclassified it as ready, M16 attempted authoring and was correctly blocked, M17 closed the actual gap, and only then did M18 succeed. That detour is not a story about ETF — it is the shape every future definition (FUND, BOND, PROPERTY, CRYPTO, COMMODITY, and whatever arrives after them) will walk unless the lessons it taught are written down as a process rather than left as institutional memory in one contributor's head. This guide is that write-down. Section 8 below states the lessons explicitly; Sections 2–7 turn them into eight ordered stages.

Nothing in this guide changes what a definition may say (that is [asset_definitions.md](../architecture/asset_definitions.md)'s vocabulary and axes) or how the runtime processes one (that is `backend/services/asset_definitions/`'s existing modules). It only orders and names the steps an author already had to take, so the order stops being tribal knowledge.

---

## 2. The eight-stage workflow

Each stage names its gate, the artifact it produces or checks, the tool that verifies it mechanically where one exists, and the ETF worked example. A stage is not optional and not reorderable — Stage 1 exists specifically because skipping it is what M16 did, at real cost.

### Stage 0 — Vocabulary review

**Question:** Can this kind's behavior be said in the seven axes' existing words ([asset_definitions.md](../architecture/asset_definitions.md) §7)?

Read `backend/services/asset_definitions/vocabulary.py` axis by axis against the candidate kind's actual behavior. List every axis where an existing word already fits and, separately, every axis where nothing fits. If every axis fits, this stage passes and Stage 1 begins immediately. If any axis has no honest word, stop — this is [asset_definitions.md](../architecture/asset_definitions.md) §8.1 Step 2, a governed vocabulary extension, and it must complete (with its own DECISION_LOG entry) *before* Stage 1 is attempted. Authoring against a missing word — describing the closest existing word and hoping it reads honestly — is not a shortcut, it is the defect Stage 1 exists to catch, one stage too late.

*ETF worked example:* M15's `readiness_report.py` scanned ETF's capability shape and judged every axis already expressible — `VOCABULARY_READY`. That judgment turned out to be wrong on exactly one axis (see Stage 1), which is why Stage 0's output must be an axis-by-axis list checked against the *individuating* declaration, not a shape impression.

### Stage 1 — D1 individuation review

**Question:** What single declaration does this kind make that no existing definition in the library makes ([asset_definition_library.md](asset_definition_library.md) §3.1, gate 1)?

State it precisely: axis and value. Then check it against every current-rung transcription in `library.DEFINITION_LADDERS` — not a sample, all of them. If no such declaration exists, there is no new definition: stop, this is an existing kind plus classification, and the correct outcome is *not authoring anything*.

This gate is checked before Stage 0's vocabulary work is trusted, because a missing individuating declaration is often *also* a missing vocabulary word — the two failures look identical from a distance and this guide's whole reason for separating them into named stages is that M16 conflated them.

*ETF worked example:* [asset_definitions.md](../architecture/asset_definitions.md) §9's own ETF walk names the individuating declaration: periodic-NAV valuation. M16 discovered that `ValuationQuestion` had no such member — Stage 0 and Stage 1 failed for the same underlying reason, on the same axis, and the fix (M17) was a Stage 0 problem, not a Stage 1 one. Once M17 shipped, Stage 1 passed cleanly: ETF's declared `ValuationQuestion.PERIODIC_NAV` is a payload no other current-rung transcription shares, checked directly in Stage 5's registry boot and again by a dedicated pairwise comparison (see [asset_definition_etf.md](asset_definition_etf.md)'s Purpose section and `test_asset_definition_etf.py`'s Constitution Conformance tests).

A note on the constitution's own permission: [asset_definitions.md](../architecture/asset_definitions.md) §9 observes that ETF *could* have declared "both continuous-quote and periodic-NAV valuation semantics on one kind... and either answer is a healthy outcome." M18 chose the single-declaration answer deliberately — `ValuationDeclaration` (Axis 4) is a scalar field, not a set like Axis 5/6's grants, so declaring "both" would have been a declaration-model change, which is Stage 3's territory (see below), not this stage's. This is recorded here because a future author reading §9's prose alone might reasonably expect the wider answer; the narrower one was a real choice, not an oversight.

### Stage 2 — Declaration authoring

**Question:** What is the complete, honest declaration on every one of the seven axes — presences and absences both argued?

Write the definition document following [asset_definition_library.md](asset_definition_library.md) §3.2's nine-part shape (header, Purpose, Axes 1–7, Capability Projection, Validation) and §3.3's style laws (challenge in the text, no proper nouns, no speculative grants, name the version's scope). "Definition quality over completeness" governs here: declare only what the kind actually is, on every axis it must declare something for (unit, acquisition, settlement, flows are the four the deterministic core cannot do without — [asset_definitions.md](../architecture/asset_definitions.md) §6.4) — never pad a definition with declarations chosen merely to widen its distance from a neighbor. A minimal-diff definition that differs from its nearest neighbor on exactly the axis Stage 1 identified, and matches everywhere else, is not a weak definition — it is proof that Stage 1's individuating declaration is doing all the individuating work, honestly.

*ETF worked example:* every axis except Valuation is byte-identical to Equity v1's declaration. `asset_definition_etf.md`'s Purpose section argues this explicitly rather than leaving it to be noticed.

### Stage 3 — Governance review

**Question:** Does the document pass the library's own admission checks — D1 satisfied, vocabulary-only, no formula, no metadata, no classification, no judgment?

This is a human read of the document's own Validation section (the five attestations [asset_definition_library.md](asset_definition_library.md) §3.2 part 5 requires) against the actual text above it, plus a check that nothing in Stage 2 quietly reached for a declaration-model change (a new field, a set where a scalar exists, a relaxed constraint) — those are constitutional or runtime changes and belong to a different milestone with a different brief, never smuggled in during authoring.

*ETF worked example:* the Axis 4 scalar-vs-set question (Stage 1's note above) was exactly this check — recognized in Stage 1, resolved in Stage 2, and re-confirmed here as a governance-review finding worth its own paragraph in the document rather than a silent pick.

### Stage 4 — Fingerprint generation

**Question:** What is the pinned digest that makes this published version's immutability checkable (D8)?

Add the transcription to `library.py` (`DEFINITION_LADDERS`), then compute its fingerprint with `fingerprint.compute_fingerprint()` against the *actual* `DefinitionTranscription` object — never hand-computed, never guessed — and hand-copy the resulting digest into `library.PINNED_FINGERPRINTS`. This is deliberately a manual, two-step act (write the transcription, separately pin its digest) rather than a derived one: `fingerprint.py`'s own module docstring explains why a self-referential fingerprint would defeat its purpose.

```
./venv-test/Scripts/python.exe -c "
from services.asset_definitions import library
from services.asset_definitions.fingerprint import compute_fingerprint
print(compute_fingerprint(library.<NEW>_V1))
"
```

*ETF worked example:* `9aeb81273432ba38b0352600b6b786a6afce4c351bcd5247520cadce42a3421d`, computed once against `ETF_V1` and pinned by hand in the same commit that added the transcription.

### Stage 5 — Runtime validation

**Question:** Does the platform boot clean, and does the new definition actually project the way the document says it should?

`DefinitionRegistry.build()` re-derives every check Stages 1–4 performed by hand — D1 (the `duplicate-declarations` rule), the fingerprint pin (`fingerprint-mismatch`, `missing-fingerprint-pin`), structural integrity (`invalid-existence-reference`, `ladder-ordering`, `duplicate-version`, `unknown-binding`) — and refuses to boot, all-or-nothing, if any fails. Confirm `exists(binding)` is `True`, `BindingResolver.resolve(binding)` returns a working `CapabilityView`, and every row of the document's Capability Projection table matches what `CapabilityView`'s accessors and `GovernanceProjection.as_dict()` actually return. This is the stage the generic framework tests in `backend/tests/test_asset_definition_authoring_framework.py` automate — they run this exact check against *whatever the library currently contains*, so a future definition inherits this validation without a new test file.

### Stage 6 — Readiness verification

**Question:** Does the readiness report now say `DEFINED`, and does it say so *because* the library says so?

`readiness_report.DEFINITION_READINESS` is hand-authored, not derived (its own module docstring explains why — the same discipline `enforcement_decisions.py` applies). Update the new binding's row to `ReadinessStatus.DEFINED` with empty `missing_requirements`, then let `test_defined_status_matches_library_ladders` (in `test_definition_readiness.py`, generic over every `AssetType` member already) confirm the hand-edit agrees with `library.DEFINITION_LADDERS` in both directions. A readiness row that disagrees with the library is a defect regardless of which side is "right" — the row must always describe what the library actually contains.

### Stage 7 — Enforcement implications

**Question:** Does a definition existing change what `enforcement_decisions.py` should say — and does it change what enforcement actually *does*?

These are two different questions and Stage 7 exists to keep them separate. A definition existing closes the *capability* gap `GapType` describes: the runtime now genuinely agrees with legacy behavior for this binding (`_consult_runtime_for_mint` reports an agreement, not an `UnknownCapability` finding), so the binding's row should stop claiming `MISSING_DEFINITION`. It does **not** by itself justify promoting `future_action` past `MIGRATE` — that promotion is a separate, explicit, human-authorized R2 policy decision, out of scope for an authoring milestone by design (this is [asset_definitions.md](../architecture/asset_definitions.md)'s describe/judge line, §2.5, applied to process: authoring describes what a kind is; enforcement policy judges what to do about it, and the two must never be decided in the same breath).

*ETF worked example:* `enforcement_decisions.py`'s ETF row moved `gap_type` from `MISSING_DEFINITION` to the previously-reserved `FUTURE_ENFORCEMENT_CANDIDATE` (M18) — an honest description of the now-closed capability gap — while `future_action` stayed at `MIGRATE`, unchanged. No enforcement was enabled by authoring ETF, and none should be by authoring any future definition either.

---

## 3. What "generic, not per-definition" means for tests

`test_asset_definition_authoring_framework.py` deliberately never names a specific binding (no `"ETF"` string appears in its assertions). It parametrizes over `library.DEFINITION_LADDERS` and `AssetType` as they stand at import time, so the same file validates CASH and EQUITY today, ETF as of M18, and whatever is admitted next without being edited. A *specific* definition still needs its own worked test file (`test_asset_definition_etf.py` is ETF's) for the declarations that are genuinely particular to it — the row-by-row Capability Projection match, the D1 pairwise comparison against its nearest neighbor. The generic file checks the *framework's* guarantees; the specific file checks the *definition's* content. Both are required; neither substitutes for the other.

---

## 4. Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution: seven axes, D1–D12, §8.1's evolution ladder, §9's worked examples
- [asset_definition_library.md](asset_definition_library.md) — the library's own §3, which this guide operationalizes stage by stage
- [definition_review_checklist.md](definition_review_checklist.md) — the same eight gates as a pass/fail checklist
- [asset_definition_etf.md](asset_definition_etf.md) — the reference implementation this guide's worked examples are drawn from
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — M15 (readiness), M16 (blocked attempt), M17 (vocabulary extension), M18 (successful authoring), M19 (this guide)
