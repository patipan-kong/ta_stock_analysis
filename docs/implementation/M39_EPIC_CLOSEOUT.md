# M39 — Canonical Asset Market Observation Epic Closeout

**Closeout date:** 2026-07-23

**Status:** Complete and frozen

**Decision:** M39 is closed and admitted to the repository as the frozen
constitutional specification corpus for Canonical Asset Market Observation.

## 1. Executive summary

M39-WP1 through M39-WP6 are complete, canonically represented, and frozen. The
independent Constitutional Architecture Review of the whole milestone returned
**APPROVED FOR EPIC CLOSEOUT** with no constitutional defect and three
OBSERVATION-level editorial clarifications that the reviewer expressly
determined do not block closeout.

This closeout reconciles the repository record only. It creates no new
architecture, semantic concept, work package, runtime, provider integration,
public endpoint behavior, or product behavior. M38 and every earlier milestone
remain frozen. The three observations remain informational and are not
converted into constitutional amendments.

## 2. Milestone objective

M39 establishes the constitutional semantic model of a single, authenticated,
read-only Market Intelligence boundary through which a registered asset's
current market observation may be requested by canonical `asset_id`, together
with the frozen semantic layers that govern what an Observation **is**, what it
**means**, how it **relates** to other observations, and which event it
**denotes**.

The milestone delivers:

- one provider-neutral market-observation boundary contract (WP1); and
- the layered Observation semantics — Source, Classification, Payload,
  Relationship, and Identity (WP2–WP6) — atop that frozen contract.

Market Intelligence remains the sole semantic owner of Market Observation.
Registry identity is used only to address the observed asset and derive the
configured provider request. Observation remains evidence and never becomes
identity, ledger, decision, execution, or presentation authority.

## 3. Work-package reconciliation

| Work package | Canonical repository representation | In-document status | Closeout finding |
|---|---|---|---|
| WP1 — Canonical Boundary Specification | [M39_WP1_Canonical_Boundary_Specification.md](M39_WP1_Canonical_Boundary_Specification.md) | Canonical and frozen | Frozen public read boundary `GET /assets/{assetId}/market-observation`, `MarketObservation` contract, availability model, exact provider derivation, no-symbol-fallback, canonical normalization reuse, and execution separation are present and admitted. |
| WP2 — Market Observation Source Boundary | [M39_WP2_market_observation_source_boundary_specification.md](M39_WP2_market_observation_source_boundary_specification.md) | Canonical specification, approved | Observation Source eligibility and the meanings of Observation Event, Observation Payload, Observation Timestamp, and Observation Origin are grounded in External Fact / Source-Reported Claim; non-domain authorization boundary and Connectivity & Ingestion ownership are correct. |
| WP3 — Market Observation Classification | [M39_WP3_market_observation_classification_specification.md](M39_WP3_market_observation_classification_specification.md) | Canonical specification, approved | Canonical Observation Classes, the Classifying Fact, the exactly-one-class rule, zero/one/multiple disposition, mixed-content treatment, and additive class admission are closed and non-overlapping with no catch-all. |
| WP4 — Market Observation Payload | [M39_WP4_market_observation_payload_specification.md](M39_WP4_market_observation_payload_specification.md) | Canonical specification, approved | Provider-neutral Payload Meaning, Semantic Sufficiency, Semantic Subject, temporal and provenance preservation, uncertainty, absence, and Correction Lineage preserve fidelity without adding, losing, or reinterpreting source meaning. |
| WP5 — Market Observation Relationship | [M39_WP5_market_observation_relationship_specification.md](M39_WP5_market_observation_relationship_specification.md) | Canonical specification, approved | Observation Relationship and Relationship Meaning relate Identity-Distinct events only; endpoint distinctness, Semantic Independence, lifecycle relationships, grouping, cross-reference, and Causal Independence are consistent and additive. |
| WP6 — Market Observation Identity | [M39_WP6_market_observation_identity_specification.md](M39_WP6_market_observation_identity_specification.md) | Canonical specification candidate, complete | Observation Identity, Identity Meaning, Identity Equivalence and Distinctness, Identity Stability, and Semantic Persistence denote one immutable event without collapsing into Semantic Equivalence or an M39-WP5 relationship. |

Every M39 work package has exactly one canonical repository path to its frozen
authority. No standalone file is orphaned from this closeout or the index.

## 4. Constitutional achievements

- **Single semantic owner.** Market Intelligence is the sole owner of Source,
  Event, Timestamp, Origin, Classification, Payload, Relationship, and Identity
  across WP2–WP6. No concept is defined twice, owned twice, or left
  insufficiently owned.
- **Non-domain authorization boundary.** Authentication, authorization,
  approval, and actor identity are treated as a non-domain boundary under
  Law 12 in every ownership table. No fabricated "identity and access" domain
  survives anywhere in the corpus.
- **Evidence, never authority.** Every layer restates that an Observation is
  evidence and never becomes truth, quality, currentness, preference, ledger,
  decision, execution, or presentation authority.
- **Deterministic interpretation.** Each layer pairs a closed disposition set
  with an explicit "ambiguous → unadmitted, never guessed" fallback
  (exactly-one-class, semantic sufficiency, endpoint distinctness, and the
  three-way identity disposition).
- **Provider, implementation, runtime, storage, API, transport, and
  serialization neutrality** are uniformly asserted and mutually consistent.
- **Additive-only extensibility** with no `OTHER`/`UNKNOWN`/catch-all,
  no provider-private entry, and no implicit widening of the WP1 contract.

## 5. Architectural outcomes

The corpus resolves to one coherent event model: one immutable Observation
Event carries exactly one Canonical Observation Class (WP3), preserves one
provider-neutral Payload Meaning (WP4), participates in relationships among
distinct events (WP5), and bears one immutable Observation Identity (WP6),
all reachable through the single frozen WP1 boundary. The most sensitive
internal seam — WP5 Observation Relationship versus WP6 Identity Equivalence —
is explicitly and repeatedly disjoined: Identity Equivalence relates references
or representations of one event; WP5 relationships relate distinct events.

## 6. Ownership preservation

| Boundary | Owner | M39 disposition |
|---|---|---|
| Market Observation semantics (Source/Class/Payload/Relationship/Identity) | Market Intelligence | Sole owner; established by M39 |
| Canonical asset identity and Registry adjudication | Asset Foundation | Unchanged; Observation references but never owns subject identity |
| External-fact ingestion toward ledger truth | Connectivity & Ingestion | Unchanged |
| Transactions and financial truth | Ledger & Accounting | Unchanged |
| Portfolio facts and derivations | Portfolio Intelligence | Unchanged |
| Trust, quality, and conflict assessment | Trust & Evaluation | Unchanged; may consume Observation evidence, may not mutate it |
| Investment conclusions and actions | Decision Intelligence | Unchanged |
| Authentication, authorization, approval, actor identity | Non-domain authority boundaries (Law 12) | Unchanged |
| Runtime, storage, transport, Experience composition | Existing owners | Unchanged |

No M39 row grants new authority. Every prior ownership boundary remains
authoritative.

## 7. Compatibility guarantees

- M38 remains complete and frozen; all M31–M38 contracts remain unchanged.
- The WP1 `MarketObservation` contract, its exact initial `contract_revision`,
  field-presence rules, `AVAILABLE`/`DEGRADED`/`UNAVAILABLE`/`UNSUPPORTED`
  availability semantics, provider request derivation, no-symbol-fallback rule,
  canonical normalization reuse, feature expectations, and rollback contract
  are frozen and are not widened by WP2–WP6.
- `price_kind` is never reinterpreted as a classification field;
  `assetId`, `subject_reference`, and `subject_asset_id` remain subject
  references and never become Observation Identity; execution evidence remains
  structurally and semantically separate.

## 8. Implementation authority

M39 is a constitutional specification milestone. WP1 is the frozen boundary
**contract**; WP2–WP6 establish **semantic obligations only**. Each work
package expressly disclaims authority to implement, adopt at runtime, persist,
integrate a provider, transport, serialize, or expose. Accordingly, this
closeout authorizes **no** runtime, endpoint, provider adapter, storage,
migration, schema, or public-exposure work. Realization of the WP1 boundary and
any consumer of the WP2–WP6 semantics is a separately governed future step and
is not begun by this closeout.

## 9. Deferred work

| Deferred capability | Reserved owner or boundary | M39 disposition |
|---|---|---|
| Runtime implementation of the WP1 market-observation boundary | Market Intelligence, separately governed | Specified, not implemented |
| Provider adapter, routing, or session behavior for observations | Provider Layer / existing provider boundaries | Not authorized |
| Observation persistence, retention, replay, or storage model | Existing storage owners | Not authorized |
| Public exposure of Classification, Payload, Relationship, or Identity vocabulary | Experience Platform under separate authority | Not authorized |
| Identifier syntax, matching, comparison, deduplication, or resolution | Separately governed future work | Not authorized |
| Any M40 material | Future milestone | Not created |

These deferrals are tracked boundaries, not incomplete M39 work packages.

## 10. Review outcome

The independent Constitutional Architecture Review of the whole M39 milestone
determined the corpus internally complete, internally consistent, and
constitutionally admissible, and returned:

> **APPROVED FOR EPIC CLOSEOUT** — no constitutional defect remains.

## 11. Observations (informational only)

The review recorded three OBSERVATION-level editorial clarifications. Each is
optional, non-blocking, and is **not** a constitutional amendment. They are
preserved here for lineage and are not acted upon by this closeout.

1. **Correction Lineage vs Relationship layering** — a one-line note could make
   explicit that WP4 Correction Lineage (payload-semantic acknowledgment) and
   WP5 Correction Relationship (canonical inter-event relationship) are two
   governed layers of one phenomenon under one owner, not duplicated concepts.
2. **"material" glossary** — the corpus-wide, contextually anchored term
   "material"/"materially" could carry a single shared glossary definition.
3. **Identity-reference name verification** — the illustrative subject-reference
   names enumerated in WP6 identity-exclusion lists (`assetId`,
   `subject_reference`, `subject_asset_id`) could each be confirmed against the
   live frozen WP1 contract elements.

These remain informational. They do not reopen WP1–WP6 and introduce no new
concept.

## 12. Repository reconciliation and validation

Closeout changes are limited to:

- this epic closeout record;
- the M39 navigation entries in [docs/implementation/INDEX.md](INDEX.md);
- the appended M39 epic closeout entry in
  [docs/engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md); and
- the required Graphify refresh.

No M39-WP1–WP6 specification content was modified. No M31–M38 artifact, runtime
source, schema, API, or public contract was modified during closeout.

## 13. Final closeout decision

M39 is `COMPLETE AND FROZEN`. All six work packages are resolved and admitted,
the independent architecture review approved the milestone for closeout, the
three observations remain informational, ownership and compatibility boundaries
are preserved, implementation remains a separately governed future step, and
the repository record is reconciled.

M40 is the next milestone number eligible for specification. This statement is
only a sequencing confirmation: M40 has not been designed, authorized, or begun
by this closeout.
