# M38 — Product Workspace Foundation Epic Closeout

**Closeout date:** 2026-07-22

**Status:** Complete and frozen

**Decision:** M38 is ready for merge

## 1. Executive summary

M38-WP1 through M38-WP10 are complete, canonically represented, and frozen.
The independent implementation review is approved, the bounded WP10
synchronous re-entrancy defect is remediated, and the independent re-review
has no remaining blocking finding.

This closeout reconciles the repository record only. It creates no new
architecture, runtime authority, work package, public contract, or product
behavior. M35, M36, M37, and every approved M38 work package remain frozen.

## 2. Canonical architecture preserved

The completed milestone preserves the following boundaries:

- Search discovers; Workspace interacts.
- Registry owns canonical asset identity.
- Providers own their source data.
- Intelligence consumes Workspace through declared public boundaries.
- Experience Platform owns Workspace Context, Asset Focus association,
  navigation orchestration, composition mechanics, observation, querying, and
  the transient Discovery Experience, but no upstream business fact.
- `asset_id` is the only canonical workspace asset identity.
- Discovery Candidates contain no `asset_id` and can open only a transient,
  non-routing, non-persistent Discovery Experience.
- Workspace runtimes consume only frozen public contracts and do not import
  Search, Registry, Resolver, or provider internals.
- Current Selection remains independently owned and read-only to M38
  composition.
- Reserved contribution and intent seams remain inert.

No constitutional contradiction was found during closeout.

## 3. Work-package reconciliation

| Work package | Canonical repository representation | Final state | Closeout finding |
|---|---|---|---|
| WP1 — Boundary Contracts | [Boundary Contracts and Conformance Specification](M38_WP1_BOUNDARY_CONTRACT_SPECIFICATION.md) and Decision Log | approved and frozen | constitutional contract is present; corrective verification closed |
| WP2 — Workspace Context | [Workspace Context Runtime Implementation Design](M38_WP2_WORKSPACE_CONTEXT_RUNTIME_IMPLEMENTATION_DESIGN.MD) and Decision Log | complete and frozen | workspace-only route prerequisite is preserved; no Asset Focus ownership imported |
| WP3 — Asset Focus | [Asset Focus Runtime Implementation Design](M38_WP3_IMPLEMENTATION_DESIGN.md) and Decision Log | complete and frozen | exact-read orchestration and Asset Focus ownership are represented |
| WP4 — Canonical Navigation | [Decision Log WP4 record](../engineering/DECISION_LOG.md#m38-wp4--canonical-navigation-runtime) | complete and frozen | no standalone file exists; frozen navigation-orchestration authority is represented without recreation |
| WP5 — Contribution | [Decision Log WP5 record](../engineering/DECISION_LOG.md#m38-wp5--contribution-runtime) | complete and frozen | no standalone file exists; frozen Contribution authority is represented without recreation |
| WP6 — Projection Composition | [Decision Log WP6 record](../engineering/DECISION_LOG.md#m38-wp6---projection-composition-runtime-implementation-design) | complete and frozen | no standalone file exists; frozen Projection Composition authority is represented without recreation |
| WP7 — Experience Composition | [Experience Composition Runtime Implementation Design](M38_WP7_EXPERIENCE_COMPOSITION_RUNTIME_IMPLEMENTATION_DESIGN.md) and Decision Log | complete and frozen | bounded corrections and final verification are recorded |
| WP8 — Experience Observation | [Experience Observation Runtime Implementation Design](M38_WP8_EXPERIENCE_OBSERVATION_RUNTIME_IMPLEMENTATION_DESIGN.md) and Decision Log | complete and frozen | bounded corrections and final verification are recorded |
| WP9 — Experience Query | [Experience Query Runtime Implementation Design](M38_WP9_EXPERIENCE_QUERY_RUNTIME_IMPLEMENTATION_DESIGN.md) and Decision Log | complete and frozen | bounded corrections and final verification are recorded |
| WP10 — Discovery Experience | [Discovery Experience Runtime Implementation Design](M38_WP10_DISCOVERY_EXPERIENCE_RUNTIME_IMPLEMENTATION_DESIGN.md), [runtime](../../frontend/lib/discoveryExperience.ts), [tests](../../frontend/lib/discoveryExperience.test.ts), and Decision Log | complete and frozen | missing standalone record created; re-entrancy blocker and remediation are synchronized |

Every approved work package therefore has one canonical repository path to its
frozen authority. WP4–WP6 are intentionally represented by Decision Log
records because no standalone implementation files exist in the repository.
Reconstructing those already-frozen documents during closeout would create new
normative text and was not authorized. WP10 received a standalone document
because it has a concrete implementation and test suite and its absence made
the completed implementation record structurally incomplete.

## 4. Implementation and documentation synchronization

### 4.1 Frozen designs

WP1–WP9 implementation designs and contracts were not edited. Their accepted
review and corrective-verification outcomes remain recorded in the
[Decision Log](../engineering/DECISION_LOG.md). Some frozen design footers
describe the pre-review handoff state (for example, “ready for implementation”
or “ready for corrective verification”). Those historical footer statements
were not rewritten. The later Decision Log entries and this closeout record
the final frozen state and provide the authoritative lifecycle reconciliation.

### 4.2 WP10 implementation

The WP10 implementation consists only of:

- `frontend/lib/discoveryExperience.ts` — public values, strict validation,
  transient lifecycle coordinator, observation, stale-handle suppression, and
  the private re-entrancy guard;
- `frontend/lib/discoveryExperience.test.ts` — 20 focused contract, lifecycle,
  dependency-boundary, and regression tests; and
- the existing `test:pure` command extension in `frontend/package.json`.

The implementation matches WP1 §§3.4 and 5.2 and the approved WP10 authority:
it preserves the exact Discovery Candidate and Search degradation values,
copies the resolved WP2 workspace identity without coercion, supports only
`OPEN` and terminal `CLOSED`, represents absence structurally, and introduces
no Asset Focus, route, canonical identity, persistence, Search execution,
Registry, Resolver, provider, Portfolio, Intelligence, Intent, or Action
dependency.

The remediation is private and semantic-preserving. During lifecycle
transition and synchronous notification, nested `open` rejects explicitly and
nested `close` or `expire` returns false. Nested commands mutate nothing and
emit nothing. `try/finally` releases the guard, and observer failures remain
isolated.

## 5. Decision Log and index reconciliation

The [Implementation Index](INDEX.md) now:

- identifies M38 as the current completed milestone;
- links every standalone M38 document;
- identifies the Decision Log as the WP4–WP6 representation;
- links this closeout; and
- classifies WP1–WP10 as complete and frozen.

The [Decision Log](../engineering/DECISION_LOG.md) now:

- records the final WP10 authority and bounded remediation;
- records the epic-level M38 closeout;
- preserves all earlier WP1–WP9 decisions unchanged; and
- states that M39 is next only in milestone sequence, not authorized or begun.

No M38 implementation document is orphaned from the index or this closeout.

## 6. Deferred work

The following work remains explicitly outside M38 and receives no authority
from this closeout:

| Deferred capability | Reserved owner or boundary | M38 disposition |
|---|---|---|
| Discovery-to-canonical-asset handoff | Resolver | no endpoint; reserved seam only |
| Market projection | Market Intelligence | no endpoint; reserved slot only |
| Intelligence projection | owning Intelligence domain | no endpoint; reserved slot only |
| Intent or action submission | future intent owner | no endpoint; reserved seam only |
| Workspace directory, switching, membership, or RBAC | future owning context | not implemented |
| Multi-workspace behavior | future milestone | not implemented |
| Portfolio ownership or persistence changes | Portfolio owner | unchanged |
| Provider runtime behavior beyond frozen M37 contracts | Providers / M37 boundaries | unchanged |

These deferrals are tracked boundaries, not incomplete M38 work packages.

## 7. Repository reconciliation and validation

The closeout validation performed on 2026-07-22 produced:

| Check | Result |
|---|---|
| WP10 focused Node test suite | passed: 20/20 |
| Existing frontend pure suite | passed: 31/31 |
| Existing Vitest suite | passed: 3 files, 23/23 tests |
| TypeScript no-emit type-check | passed |
| Next.js production build | passed; 23 routes generated |
| Markdown relative-link validation for changed closeout records | passed |
| M38 representation and orphan-document audit | passed |
| `git diff --check` | passed |
| Graphify incremental update | passed |

The standalone ESLint configuration and unrelated backend native-access
findings were outside the approved WP10 remediation and are not introduced or
altered by this closeout.

## 8. Change-scope reconciliation

Closeout changes are limited to:

- this epic closeout record;
- the new WP10 implementation design required for repository consistency;
- M38 navigation entries in `docs/implementation/INDEX.md`;
- WP10 and M38 closeout entries in `docs/engineering/DECISION_LOG.md`; and
- the required Graphify refresh.

The pre-existing approved WP10 runtime, tests, and `test:pure` script change
remain the only implementation changes in the worktree. No frozen WP1–WP9
artifact, M35–M37 artifact, unrelated runtime source, schema, API, or public
contract was modified during closeout.

## 9. Final closeout decision

M38 is `COMPLETE AND FROZEN`. All ten work packages are resolved, no blocking
finding remains, deferred seams remain inert, documentation navigation is
reconciled, and the repository is ready for merge.

M39 is the next implementation milestone in sequence. This statement is only
a sequencing confirmation: M39 has not been designed, authorized, or begun by
this closeout.
