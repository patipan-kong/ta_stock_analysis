# M9 — Asset Definition Runtime — Technical Design Document

_How the canonical Asset Definitions become executable without ever becoming a second source of truth. The level-4 technical design realizing [asset_definitions.md](../architecture/asset_definitions.md) (the constitution, D1–D12) and [asset_definition_library.md](../definitions/asset_definition_library.md) (the library charter) at run time._

| | |
|---|---|
| **Milestone** | M9 — Asset Definition Runtime |
| **Status** | Design — no implementation in this milestone |
| **Authority level** | 4 (technical design), bound by the constitutions above (rule G2); any code produced from it is level 6 and conforms to the library, never the reverse (rule G6, library §4) |
| **Prime directive** | The library remains authoritative. The runtime is only the executable projection. |

---

## 0. Scope and the one sentence that governs everything below

The library's two documents — [Cash v1](../definitions/asset_definition_cash.md) and [Equity v1](../definitions/asset_definition_equity.md) — are the platform's truth about what those kinds *are*. Nothing in this design creates truth: every structure below is a **faithful, mechanically-audited copy of a Capability Projection table**, and every design decision is tested against one question — *could this structure ever disagree with its document without anyone noticing?* Wherever the answer was "yes," the design was changed until it was "no."

This document designs; it does not implement. Names like `DefinitionRuntime` below are conceptual handles for review, not committed spellings — implementation spellings are free at level 6 (constitution §7.1).

### 0.1 Ground truth: what the codebase does today

The design is grounded against the current code, and five facts discovered in that survey shape it:

1. **No definition mechanism exists.** The M5 Track B design ([M5_TRACK_B_NATIVE_INTEGRATION_TDD.md](M5_TRACK_B_NATIVE_INTEGRATION_TDD.md) §8) sketched `asset_definition_domain.py` / `asset_definition.py`; neither was ever built. The runtime is greenfield, which is the best possible starting condition: there is no wrong mechanism to unwind, only implicit behavior to make explicit.
2. **Kind-truth lives in three shadow homes.** What the platform "knows" about cash and equity behavior is encoded as transaction-type frozensets in three engines independently: `portfolio_rebuilder.py` (`_CASH_INFLOW_TYPES`, `_CASH_OUTFLOW_TYPES`), `ledger_validator.py` (`_EQUITY_TYPES`, `_BUY_TYPES`, `_CASH_IN_TYPES`), and the canonicalizer's preserved-type list. Three homes for one truth is the drift precondition the constitution's D4 exists to prevent.
3. **`AssetType` is pre-constitutional.** The enum in `services/asset_domain.py` carries a docstring stating engines "are expected to branch on this" — a direct contradiction of D5, quoting a UAA §2 test that the ratified constitution has since reorganized (asset_definitions.md §11). Seven of its nine members (`ETF`, `FUND`, `BOND`, `CRYPTO`, `COMMODITY`, `PROPERTY`, `OTHER`) name kinds **no definition describes**.
4. **Cash has a definition but no instances.** Cash is `Portfolio.cash_balance`, a column — not a minted asset. `replay_key()` deliberately returns `None` for cash-side rows. The numeraire is the one kind whose declarations currently have no identity to bind to.
5. **Cash v1 grants INTEREST, but the ledger has no INTEREST spelling.** The live transaction vocabulary is BUY, SELL, DEPOSIT, WITHDRAW, INITIAL_POSITION, INITIAL_CASH, QUANTITY_CORRECTION, DIVIDEND. An interest flow arriving today would be booked as a DEPOSIT — invisible as income.

Facts 2–5 are addressed in §10 (constitutional challenges); the architecture in §§1–10 is designed so that fixing them is consumption, not surgery.

---

## 1. Runtime Architecture

### 1.1 The pipeline: document → transcription → boot validation → frozen registry → projection

A definition becomes executable in four stages, and the stages are deliberately asymmetric in who performs them:

1. **Transcription (human, review-gated).** Each canonical document's **Capability Projection table** — and only that table — is transcribed into a code-shipped, frozen declaration structure: one per (definition, version). The prose never crosses; §3 says exactly what does. Transcription is a governed act: the PR that adds or changes a transcription must link the library document it copies, and review compares them row by row.
2. **Conformance corpus (human-authored, machine-enforced).** Every row of every projection table becomes one conformance test asserting the transcription says exactly what the document says. From that moment, drift between library and runtime is a *test failure*, not a discovery. This is the load-bearing answer to "never a second source of truth": the runtime cannot silently disagree with the library, because disagreement is mechanically detected at the cheapest possible moment.
3. **Boot validation (machine, fail-fast).** At process start, the runtime registry loads all transcriptions and runs the constitutional checks of §6. A library that fails them prevents the platform from starting. A malformed canonical definition is a build defect, and a platform that would run anyway — defaulting, guessing, skipping the bad kind — would violate D7 in its own foundations.
4. **Projection (machine, per-query).** Engines receive `CapabilityView` handles (§2.2) resolved from an asset's binding. Views are read-only, carry no kind name, and answer only the questions of §4.

### 1.2 Why code-shipped, not database-stored

The single most consequential decision in this design. Definitions ship inside the same deployable artifact as the engines, as frozen declaration data — never as database rows, and never as runtime-loaded configuration. Three arguments, in increasing order of force:

- **The treaty must be verifiable at build time.** The constitution's §2.1 treaty says everything a definition can say, some engine already honors (D3/D4). If definitions live in a database, a definition can claim a word the *deployed* engine build does not implement — the treaty broken by version skew between data and code. Shipping them together makes the treaty an invariant of the artifact: a transcription using an unknown word does not deploy, it fails to build.
- **Mutable storage invites retroactive redefinition.** D8's immutability is trivial for code (published versions are commits; changing one is visible in every diff and rejected by the fingerprint check of §5.4) and hard for rows (an UPDATE is silent, and risk 10.8 of the constitution is exactly that UPDATE). The design chooses the substrate on which the constitutional violation is *structurally loud*.
- **The library is text under version control; the runtime should live in the same history.** A definition version, its transcription, and its conformance tests belong in one reviewable change — one PR that is the entire audit trail of "the platform learned a kind." Splitting the transcription into a database splits the audit trail.

What the database *does* store: the **binding** (each asset row's definition binding, today spelled `assets.asset_type`) and, from the first v2 onward, admission-version stamps (§5.3). Bindings are instance facts; declarations never are.

### 1.3 Lifecycle and immutability

- The registry is **built once at boot, then frozen** — immutable in-process data, no reload, no hot-swap. A new definition or version arrives the way new code arrives: a deployment. This is not a limitation; it is D8 made physical. (The registry is pure data — its "lifecycle" is the process lifecycle.)
- Published transcriptions are **append-only**. A new version of a definition is a new frozen structure alongside its predecessor; the predecessor is never edited, and both remain loaded forever, because replay may consult either (§5).
- **No I/O on any query path.** Every engine question is answered from frozen in-memory data. Performance consequences in §11.8: there are none worth discussing.

---

## 2. Runtime Objects

Four objects exist. Everything else is deliberately absent.

### 2.1 `DefinitionRegistry` — the loaded library

The boot-built, frozen collection of every (definition, version) transcription plus each definition's version ladder (§5.2). Responsibilities: load, validate (§6), resolve. It is the *only* component that knows definition names — names exist here because binding resolution and governance need them, and the projection boundary (§3) is precisely the line below which they never pass.

### 2.2 `CapabilityView` — what engines hold

The projection of exactly one (definition, version), resolved for exactly one asset-in-hand. This is the treaty surface: everything in §4's "may ask" list, nothing else. What it deliberately does **not** expose:

| Hidden | Why |
|---|---|
| The definition's name, the kind, the binding spelling | D5 — engines never receive a kind. A view is deliberately anonymous: two views of the same kind are not distinguishable *as* that kind through the view surface. |
| The version identifier | Engines behave identically under every version; version resolution is the runtime's job (§5), and exposing it would invite "if v2 then…" — kind-branching wearing a version costume. |
| Any enumeration of its own grants ("list all flows") | Discipline 2 (require, never enumerate). Enumeration is the reconstruction kit for fingerprinting kinds (§11.3). Engines ask about the words their operation contract names, by name. |
| Metadata, classification, instance facts | D12; §5.3 of the constitution. Instance facts reach engines on the asset record where they always have — never through the view (§3.2). |
| The document, the prose, the reasoning | Governance reading, not runtime input. |

Views are value-like, immutable, and cheap; engines may hold them for the duration of an operation but never persist them — the persisted fact is the asset and the moment, from which the view is always re-derivable (§5).

### 2.3 `BindingResolver` — from asset to view

Resolution is the only door: given an asset (by `asset_id` or a loaded registry row) and an **as-of moment**, return the `CapabilityView` of the bound definition at the version governing that moment. Properties:

- **Resolution never returns the kind.** The caller gets a view or a refusal, never a name.
- **An asset bound to a definition the registry does not carry is a loud, named refusal** — "no definition admits this binding" — not a boot failure (the defect is in one data row, not in the library) and never a default view (D7). Ledger and registry validators surface the same condition as an integrity finding (§9).
- **The numeraire resolution.** Until cash instances are minted (§10.3), the resolver exposes one deliberate, documented special entry: the portfolio's cash position resolves to the Cash definition's view without an instance binding. This is transitional scaffolding with a named retirement condition — multi-currency's cash minting — recorded here so it is a plan, not a drift.

### 2.4 `GovernanceProjection` — the human surface

The full, enumerable dump of any (definition, version) — every axis, every grant, the version ladder, the fingerprints — for trust surfaces, audit UIs, the registry admin API, and conformance tests. It is a **separate object behind a separate import path** from `CapabilityView`, and the mechanical audit of §4.3 forbids engine modules from importing it. Same data, two doors, because the two readers of the constitution's §2.4 have different rights: humans may enumerate; engines may only ask.

---

## 3. Projection Layer

### 3.1 What survives transcription, what intentionally disappears

| From the document | Into the runtime? | Why |
|---|---|---|
| The Capability Projection table — every grant and every enumerated semantic on all seven axes | **Yes — exactly and only this.** | It is the document's own declaration of "the truth engines consume" (library §1). |
| Explicit absences (Cash: no event families; no relationships) | **Yes, as explicit empty declarations** — distinguishable from "axis not declared." | D7: absence is a declaration. The runtime representation must make "declared none" and "malformed/missing" different states, because the first is truth and the second is a boot failure (§6). |
| Refinement authorities ("fractional/lot: instance facts", "cycle length: instance fact") | **Yes — as the named permission to refine.** | D10 validation at minting needs the permission surface: which instance facts this definition allows, so a contradicting claim is refused at registration. |
| Purpose, individuation reasoning, challenged alternatives, rejected grants and where they live instead | **No.** | Governance reading. The runtime carrying "why" would make it a second place the reasoning lives — and reasoning is exactly what must stay diffable text. |
| Version scope notes (FX deferred, shorting deferred) | **No.** | Roadmap for authors, not truth for engines. An engine needing to know "FX is out of scope" is an engine about to default around an absence — the absence itself (no grant) is all it may see. |
| Related documents, status, library metadata | **No.** | Text plumbing. |

The test applied to every candidate field, present and future: **if an engine could behave differently because of it, it is projection; if only a human could, it is not.** This is D3's behavioral-difference test applied to the projection itself, and it is what keeps the projection from inflating (§11.6).

### 3.2 Instance facts flow beside the projection, never through it

The `Asset` row's universal fields (`fractional_support`, `lot_size`, `settlement_cycle`, `tradable`) are D10 instance refinements. They keep reaching engines exactly as they do today — on the asset record. The runtime's involvement is exactly one new duty, at exactly one moment: **at minting (and at instance-fact update), validate that the claimed refinements lie within what the bound definition permits.** A fractional claim under a definition whose unit axis permits fractional refinement: admitted. A `tradable=True` claim under Cash (not transactable): a registration-time defect, refused loudly with the contradicted axis named (§10.4). This realizes D10's "never a runtime negotiation" — after the gate, engines trust both surfaces without cross-checking.

---

## 4. Capability API

### 4.1 Exactly what engines can ask

One question form per axis — seven forms, closed, growing only when the vocabulary grows (§7):

| # | Axis | Question an engine may pose | Answer shape |
|---|---|---|---|
| 1 | Unit | What is the unit semantics? Is quantity discrete or continuous? May it be negative? Is quantity identical to value? May instances refine divisibility/lots? | Enumerated semantics + booleans + refinement permissions |
| 2 | Acquisition | What acquisition mechanism does this kind declare? (venue-traded / not-transactable / …) | One enumerated value |
| 3 | Settlement | What settlement pattern? (instant / cycle-based / …) May instances refine the cycle? | Enumerated value + refinement permission |
| 4 | Valuation | What valuation question exists for this kind? (continuous-quote / identity / …) | Enumerated value |
| 5 | Flows | *Is flow type F granted?* — asked per flow type, by name | Boolean, per query |
| 6 | Event families | *Is event family E granted?* — asked per family, by name | Boolean, per query |
| 7 | Existence | What existence pattern? *Is relationship kind R permitted? Is it mandatory?* — per kind, by name | Enumerated value + boolean pair, per query |

Axes 1–4 are **total semantics**: every definition answers them (§6.4 of the constitution — the fundamental axes; the runtime's completeness check enforces it). Axes 5–7's grant questions are **membership queries**: asked word by word, answered present/absent, absence meaning *refuse* (D7).

### 4.2 Exactly what engines cannot ask

- *What is this?* — no kind, name, class, or binding spelling exists on the view (D5).
- *What version am I seeing?* — version-blindness by construction (§2.2).
- *What else does it support?* — no enumeration of grants; engines ask about words they implement, by name (discipline 2).
- *Is it like an equity?* / any similarity, family, or comparison question — families are shelving for humans (constitution §6.3); the view exposes none.
- *What does its metadata / classification / instance record say?* — different surfaces, different laws (D12; §3.2).
- *What should I do about an absence?* — nothing. There is no "fallback semantics" accessor, no default provider, no "closest supported behavior." The API's shape makes refusal the only representable response to absence.

### 4.3 How ask-never-identify is enforced

Honestly: by **structural absence plus mechanical audit** — not cryptography. A determined engine could fingerprint a kind by sweeping every vocabulary word through membership queries. The defense in depth:

1. **Structural.** The information is not on the surface: no name, no version, no enumeration. Fingerprinting requires *visible, deliberate* effort — a wall of membership queries no operation contract justifies — which converts a silent defect into a reviewable smell.
2. **Mechanical (the CI audit).** Three greppable gates, run as tests: (a) no module below the engine boundary imports the `AssetType` enum or any binding spelling; (b) no engine module imports `GovernanceProjection`; (c) no class-name string literal (`"EQUITY"`, `"CASH"`, …) appears below the boundary. This extends the audit the constitution already declares mechanical (risk 10.3) into the build.
3. **Contractual.** Each engine operation publishes which capabilities it requires (discipline 2); review compares queries made against requirements published. A query outside the contract is a finding even when harmless.

---

## 5. Version Runtime

### 5.1 The guarantee to deliver

Law 4 and D8, combined, demand: **replaying a recorded fact consults the definition version that admitted it, bit-for-bit, forever.** The version runtime is the machinery that makes this a pure function of recorded state.

### 5.2 The version ladder

Per definition, the registry carries an ordered, append-only ladder: each version's frozen transcription plus its **effective-from moment** (the deployment moment its governing began, recorded in the transcription itself and in DECISION_LOG). Resolution for a fact admitted at time *t*: the latest version whose effective-from ≤ *t*. The ladder is code-shipped and immutable (§1.2), so this resolution is deterministic from (binding, *t*) alone.

### 5.3 The epoch rule, and stamping from v2

- **Everything before the runtime's activation replays under v1 — by fiat, and correctly.** The library's own sufficiency argument (library §2: "they are already true") is what makes the fiat sound: v1's declarations were transcribed *from* the engines' historical behavior, so replay of pre-runtime history under v1 is bit-identical by construction. The epoch rule is that argument doing mechanical work.
- **From the first v2 onward, admission stamps the version.** When any definition first gains a second version, the admission path begins recording the admitting version on the fact at write time — recorded, not re-derived — making D8's "the definition consulted is part of the recorded state" literal rather than inferential, and immunizing replay against any future ambiguity at effective-from boundaries. Until a v2 exists, the stamp column would carry one constant value for every row; deferring it is not debt, it is the absence of a question.
- **Assets bind to definitions; versions govern moments** (constitution §8.2). Nothing ever re-decides which version governed a recorded fact — not a rebinding, not a repair, not a rebuild. `rebuild_portfolio()` under this design resolves the version per fact from the stamp (or ladder, pre-v2) exactly as it resolves prices from recorded snapshots: as recorded input.

### 5.4 Immutability made checkable: fingerprints

Every published (definition, version) transcription has a **declaration fingerprint** — a digest of its canonically-serialized declarations — pinned in a manifest that changes only when a version is *added*. At boot, the registry recomputes and compares: a published version whose fingerprint moved is retroactive redefinition (constitution risk 10.8), and the platform refuses to start. This turns the subtlest constitutional violation — a "small correction" to a shipped version — into the loudest possible failure, at the earliest possible moment, before any ledger is touched.

---

## 6. Validation Layer

Three failure classes, three severities, three moments — never blended:

### 6.1 Malformed library → **boot failure**

Checks run at registry build, all-or-nothing; any failure names the definition, version, axis, and violated law:

| Check | Law |
|---|---|
| Every declaration's every word is a member of the closed vocabulary | D3 (with code-shipped transcriptions this is largely a build-time impossibility to violate — which is the point of §1.2 — but the check exists as the stated invariant, not an accident of substrate) |
| All seven axes present on every definition; axes 1–4 (the fundamental four) carry complete semantics; axes 5–7 carry explicit grant sets, empty allowed | Constitution §6.4; D7 (empty ≠ missing) |
| No two (current) definitions with identical complete declaration sets | D1 — the duplicated-definitions audit (risk 10.4), run standing, at the single admission point |
| No declaration carries logic, formulas, free text, judgment-shaped fields, or metadata-shaped fields — the transcription structure is *incapable* of representing them, and the check asserts the incapability holds | D2, D11, D12 |
| Version ladders strictly ordered, effective-from moments total, fingerprints match the pinned manifest | D8, §5.4 |
| Every binding spelling the platform can mint maps to exactly one definition | D9 precondition; §10.2 |

### 6.2 Unknown vocabulary → **build/boot failure, never a runtime shrug**

A transcription claiming a word no engine implements cannot deploy (§1.2). The *converse* — an engine querying a word the vocabulary doesn't carry — is a programming defect surfaced in tests. And an engine encountering a granted word it doesn't itself implement follows discipline 4: unknown is unsupported, refuse the operation, never crash the process. Three different "unknowns," three different behaviors — collapsing them is how "unknown" becomes "default," which D7 forbids.

### 6.3 Projection failures → **per-operation loud refusal**

At resolution time (§2.3): an asset bound to an unadmitted spelling, a binding row missing, a numeraire consultation outside its documented scope. These are data defects in one row, not library defects — they refuse the *operation*, with the missing thing named, and surface as validator findings (new ledger-validator check IDs in the established CRITICAL/ERROR/WARNING discipline: unresolvable binding; flow-not-granted; acquisition-inadmissible; instance-fact-contradicts-definition). The platform never fails to boot because one asset row is bad, and never serves a defaulted view because booting felt more important than truth.

---

## 7. Extension Model

The constitution's three-step ladder (§8.1), stated as runtime impact:

| Change | Library | Runtime data | Runtime code | Engine code | Who approves |
|---|---|---|---|---|---|
| **New definition** (Step 1 — the expected case) | +1 document | +1 transcription, +1 conformance test file, +1 fingerprint pin, +1 binding-spelling mapping | **none** | **none** | Library admission (both gates, library §3.1) |
| **New definition version** | +1 successor document, predecessor marked superseded | +1 transcription appended to the ladder; admission stamping activates if first v2 (§5.3) | **none** | **none** | Same + DECISION_LOG |
| **New vocabulary word** (Step 2) | (enables future documents) | +1 vocabulary member | **none** (registry code is word-agnostic) | **exactly one owning engine** implements it, with its test corpus | Governed extension path; glossary; DECISION_LOG |
| **New axis** (Step 3 — constitutional) | Amendment to asset_definitions.md §5.1 | every transcription revisits | +1 question form on `CapabilityView`; completeness check updated | engines that ask the new question | Constitutional amendment |

The table is the acceptance test made visible: **the "new definition" row's engine column reads "none," permanently.** A new kind whose PR touches an engine has, by that diff alone, failed (constitution §8.1). Impact analysis for any proposed change is reading its row — which is the point of designing the rows this way.

---

## 8. Consumer Integration

### 8.1 First consumers, in order — chosen by blast radius, ascending

1. **`ledger_validator`** (read-only; zero accounting risk). New checks consult views: flows against ungranted flow types, BUY/SELL rows naming the cash position (Cash's not-transactable refusal power — the misclassified-transfer catch Cash v1 §Axis 2 promises), instance-fact contradictions. Read-only findings first is this platform's proven onboarding pattern (the validator, the snapshot auditor, and M6's parity stages all began exactly here).
2. **The mint gate** (`asset_registry` / `bootstrap_planner`). Two duties: refuse minting under a binding no definition admits (§10.2), and D10-validate claimed instance facts against the definition's refinement permissions (§3.2). The M5 sketch's `validate_against_definition()` intent is hereby conformed to library contents and realized here.
3. **The admission path** (transaction write path). Enforcing: the flow/acquisition refusals graduate from findings to admission failures, behind the staging of §9.
4. **`portfolio_rebuilder`** (replay). Consults views per fact at the recorded version (§5.3) so replay-time refusal equals admission-time refusal — the same-law-both-moments property that makes validator and rebuilder agree by construction rather than by parallel maintenance (the exact drift the three frozensets of §0.1 risk today).
5. **Lifecycle & structural events** (when Phase 5's pipeline arrives): event-family grants consulted at event interpretation — the surprise-forbidding promise of Equity v1 §Axis 6.

### 8.2 Never direct consumers

- **The frontend / API layer** — receives capability *facts* through an API adapter that may enrich for presentation; the UI is a human surface and reads `GovernanceProjection`-derived shapes, never engine views.
- **AI / agent layers** — may receive curated capability facts in structured context via the same adapter; the registry never enters a prompt as an oracle, and no agent output ever writes definitional truth anywhere.
- **The judgment layers** (optimizer, policy, execution penalty). `execution_penalty.py` today branches on a locally-derived `EQUITY | DR | ETF | INDEX` tag for liquidity/spread baselines. Ruling, recorded here deliberately: that is **classification consumption in a judgment layer** — legitimate in kind (classification exists to be consumed by analytics and judgment; wrapper-hood *is* a classification fact per Equity v1's DR reasoning), wrong only in sourcing (local symbol heuristics instead of registry classification — pre-existing debt, out of M9 scope, logged in §10.7). It must **never** be migrated onto the definition runtime: "DR trades wider" is an opinion about markets, and the day it reads definitions, judgment has smuggled itself below the describe/judge line (D11).
- **Importers / connectivity** — they receive *refusals* from the gates, not projections; an importer that consulted definitions to pre-shape its bookings would be routing around the gate it exists to be caught by.

### 8.3 Where adapters belong

One adapter, at the API boundary, translating governance projections into presentation shapes. **No adapter between engines and the runtime**: an engine that needs adaptation to consume a view has found a vocabulary defect or its own design error (discipline 1), and an adapter there would become the place defaults are quietly manufactured — the exact soil D7 forbids.

---

## 9. Migration Strategy

The M6 playbook — golden baseline, per-portfolio flags, bit-identical parity as the gate — is reused wholesale; it is the platform's proven instrument for changing load-bearing machinery without moving a single recorded number.

**Stage R0 — Runtime exists, nothing consumes it.** Registry, transcriptions, conformance corpus, boot validation, fingerprint manifest. Ships dark. Deliverable: the platform boots with a constitutionally-validated library in memory, and a governance endpoint can display it.

**Stage R1 — Observe (hybrid begins).** `ledger_validator` checks activate (read-only, findings only). Mint-gate validation runs in report-only mode against all existing assets — producing the inventory §10.2 needs. The admission path consults views and *logs* would-be refusals without refusing. Deliverable: a complete, quantified picture of every place current data or behavior disagrees with the library — which, per the library's "already true" argument, should be near-empty; every finding is either a data defect (repair via the established ledger-repair path) or a transcription defect (fix via conformance corpus). **Nothing may advance past R1 while an unexplained finding stands.**

**Stage R2 — Enforce at the gates.** Mint-gate and admission-path refusals go live (behind the same style of per-portfolio/global flags M6 used, with the observe-mode logs as the pre-flip parity evidence). The shadow frozensets of §0.1 remain but gain conformance tests asserting they equal what the runtime derives — the hybrid's honesty check: two homes temporarily, provably agreeing.

**Stage R3 — Fully runtime-driven.** `portfolio_rebuilder` consults views during replay (per-portfolio flag; golden-baseline bit-identical parity as the acceptance test, exactly as M6 Stage 4). The frozensets are then either derived from the runtime or deleted where the consult replaces them — kind-truth reaches one home. The `AssetType` docstring is conformed (§10.1), and the CI audit of §4.3 turns on, permanently.

Rollback at every stage is flag-flip plus re-run, never data restoration — the same property M6's staging had, for the same reason: no stage moves a recorded number; every stage only changes *who is consulted* about numbers that must not move.

---

## 10. Constitutional Challenges — improvements the constitutions imply that were never noticed

The brief asks that flaws not be silently preserved. Seven, found by holding the current code against the ratified texts:

### 10.1 `AssetType`'s charter is unconstitutional
The docstring at `asset_domain.py` ("Engines are expected to branch on this") was true under UAA §2 and is false under D5. The enum survives — as the **level-6 spelling of the definition binding**, legitimate *above* the engine boundary (registry, minting, binding resolution) and contraband below it. Conforming the docstring is a one-line change with constitutional weight; the CI audit (§4.3) makes the demotion permanent.

### 10.2 Seven binding spellings name kinds that do not exist
`ETF`, `FUND`, `BOND`, `CRYPTO`, `COMMODITY`, `PROPERTY`, `OTHER` have no definitions. Under "an asset without a definition is unregisterable" (constitution §5.2), minting under them should already refuse — today nothing checks. The mint gate (§8.1) closes this; the R1 inventory reveals whether any existing row is already bound to a ghost kind (and if so, it is a dated, adjudicated repair per D9 — never a silent re-type). `OTHER` deserves its own sentence: it is the anti-definition — a binding that names the *refusal to describe* — and under this design it becomes exactly as registerable as it deserves to be: not at all.

### 10.3 The numeraire has no identity
Cash v1 is canonical, yet no cash instance exists to bind it to — cash is a column. The constitution's D1 ("every asset instantiates exactly one definition") is satisfied only vacuously. This design bridges with the documented numeraire resolution (§2.3) so Cash's refusal powers arrive *now*, and records the debt honestly: multi-currency (Phase 5) mints cash instances, the special entry retires, and `replay_key()`'s `None`-for-cash tier already accommodates the arrival (asset-id tier). Improvement noticed, not invented: the constitution implies the column was always a compressed asset.

### 10.4 `tradable` is a smuggled axis with no gate
The Asset row's `tradable` boolean overlaps Axis 2 (acquisition semantics) and is validated by nothing — an asset could claim `tradable=True` under a not-transactable kind today without complaint. Under §5.3 of the constitution the field's legitimate reading is narrow: an instance-level refinement within a venue-traded kind (e.g., a suspended-from-trading flag would instead be *lifecycle*). The D10 mint-gate validation (§3.2) gives it a gate; whether the field should be renamed or split into its lifecycle and instance-fact components is a registry-domain question this design raises and deliberately does not settle.

### 10.5 Kind-truth has three homes
The frozensets (§0.1 fact 2) are a working shadow definition system — the platform's real, undeclared library until M8. The migration (§9) is designed specifically to end at *one home* rather than adding a fourth: the runtime does not join the frozensets, it retires them.

### 10.6 The INTEREST grant has no ledger spelling
Cash v1 grants INTEREST; the transaction vocabulary has no such type, so real interest arrives disguised as DEPOSIT — income invisible as income, the mirror image of the misbooked-flow errors the definitions exist to catch. Under D4 the fix is one word, one owner: an INTEREST transaction type in the ledger's admission implementation, at which moment the grant becomes enforceable rather than merely declared. Not M9 scope; recorded so the grant's currently-unexercised state is a known fact, not a discovery.

### 10.7 `execution_penalty`'s local kind-tagging
Ruled in §8.2: legitimate as judgment-layer classification consumption, deficient in sourcing (symbol heuristics), and permanently barred from the definition runtime. The eventual fix is registry-classification sourcing — logged as pre-constitutional debt for the registry roadmap.

---

## 11. Risks

| # | Risk | Structural prevention (never merely a rule) |
|---|---|---|
| 11.1 | **Runtime drift** — transcription quietly diverges from library | The conformance corpus (§1.1): divergence is a failing test, not a fact. Plus review-gated transcription PRs that must link their document. |
| 11.2 | **Duplicate truth** — the runtime starts *being* the definition | Runtime carries zero reasoning and zero prose (§3.1); every dispute resolves by reading the document (G6, library §4); the transcription's only legitimate content is a copy of a table whose original it must cite. |
| 11.3 | **Reflection abuse** — engines fingerprint kinds via query sweeps | No enumeration surface, no name, no version on the view (§2.2); operation contracts name required capabilities and review compares (§4.3); the governance surface — where enumeration is legal — is import-barred to engines. |
| 11.4 | **Metadata leakage** — the view becomes a tote bag | The view is constructed from the transcription alone — its construction path *cannot see* the asset row, classification, or metadata (§3.2); the projection test (§3.1) gates every proposed field. |
| 11.5 | **Kind-switch branching** — D5 violated downstream of all this machinery | Engines are never handed what they would branch on (§2.2); the three-gate CI audit (§4.3); `AssetType` demoted with its docstring conformed (§10.1). |
| 11.6 | **Projection inflation** — convenience accessors ("is-equity-like", "supports any income") accrete | The API grows only at §7's word/axis gates; no composite or umbrella question is representable (constitution §6.3); every new accessor is a vocabulary event with an owner, never a helper PR. |
| 11.7 | **Version corruption** — a published version moves | Fingerprint manifest + boot refusal (§5.4); code-shipped substrate makes the edit diff-visible (§1.2); admission stamps from v2 make even a successful corruption unable to re-decide history (§5.3). |
| 11.8 | **Performance** — a consult on every fact of every replay | Frozen in-process data, O(1) membership queries, zero I/O on all query paths (§1.3); replay adds one map lookup per fact against structures smaller than a page of text. Named because the brief names it; retired because the design's substrate choice already did. |

---

## 12. Governance

- This document is the **level-4 technical design of the Definitions subdomain's runtime**, bound by [asset_definitions.md](../architecture/asset_definitions.md) (G2) and by [asset_definition_library.md](../definitions/asset_definition_library.md) §4's conformance rule; implementation produced from it is level 6.
- It **supersedes** [M5_TRACK_B_NATIVE_INTEGRATION_TDD.md](M5_TRACK_B_NATIVE_INTEGRATION_TDD.md) §8 (the pre-constitutional definition mechanism sketch) in full — its ratified guarantees (unknown-is-unsupported, additive-only, the vocabulary test) are carried forward inside §§4–7 above; its contents (`Capability` enum members, `EQUITY_V1`/`CASH_V1` literals) were already superseded by the library and are here superseded as mechanism.
- No vocabulary is introduced. Conceptual object names (`DefinitionRegistry`, `CapabilityView`, `BindingResolver`, `GovernanceProjection`) are implementation-facing spellings (level 6, constitution §7.1), not glossary terms.
- Implementation of this design is a future milestone with its own staged rollout per §9; its DECISION_LOG entries are written then.

## Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution: laws D1–D12, the seven axes, the five engine disciplines
- [asset_definition_library.md](../definitions/asset_definition_library.md) — the authoritative library; §4 is the conformance rule this runtime lives under
- [asset_definition_cash.md](../definitions/asset_definition_cash.md) · [asset_definition_equity.md](../definitions/asset_definition_equity.md) — the two projection tables this runtime transcribes
- [asset_foundation.md](../architecture/asset_foundation.md) — the parent domain constitution
- [M5_TRACK_B_NATIVE_INTEGRATION_TDD.md](M5_TRACK_B_NATIVE_INTEGRATION_TDD.md) — predecessor design; ReplayKey (still governing) and §8 (superseded here)
- [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) — identity, minting, lifecycle — the other half of resolution
