# Asset Registry Retrospective

_An engineering retrospective on the Asset Registry epic — the Foundation
(M1–M4), the Compatibility Layer (M6 Compatibility-Layer Integration), the
Watchlist Registry Pilot, and Classification Consolidation. All four have
been merged into main. This document explains why decisions were made, what
the team learned, and what a future maintainer should understand before
touching this subsystem again._

_This is history, not specification. For what the Registry **is**, read
[ASSET_REGISTRY.md](ASSET_REGISTRY.md). For what remains to be **built**,
read [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](../implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md)
and [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md).
This document does not restate either — it explains the reasoning behind
them and the gap between what was planned and what happened._

---

## Executive Summary

The platform was symbol-keyed end to end: one string did four jobs — ledger
key, price-series key, analytics dimension, and display name — that the
architecture always intended to be four different concepts. This had
already caused a real incident (a vendor's depositary-receipt symbol
convention had to be normalized at every call site) and carried a standing
risk that has never gone away: a recycled ticker or a renamed listing could
silently weld two unrelated instruments' histories together in a ledger
that is supposed to be forever.

The Asset Registry epic built a permanent, platform-owned identity layer —
`asset_id`, minted once, never reassigned — and an adjudication pipeline
that resolves any symbol claim to that identity, decisively or by
escalating to a human, never by guessing. It did **not** yet re-key the
ledger itself. What shipped is the identity core (M1), the authoritative
service boundary (M2), the resolver (M3), a provider-adapter translation
layer (M4, partial), evidence-and-bootstrap tooling for the historical
ledger (M5 Track A), and — the part that actually touches production
behavior today — a read-time compatibility layer that makes every
non-ledger consumer (optimizer internals, execution sizing, AI evaluation,
watchlist, human idea intake, sector classification) Registry-informed
without waiting for the ledger to change (M6 Compatibility-Layer
Integration, all 7 phases, plus the Watchlist Pilot and Classification
Consolidation that were folded into it).

The center of gravity — giving `Transaction`, `PortfolioItem`, and
`PortfolioSnapshot` a native `asset_id` and proving replay is bit-identical
before and after — is M5 Track B, and it has not started. Everything that
has shipped was explicitly designed to deliver value **without** that step,
and to not be thrown away once it happens. That is the single fact most
worth carrying forward: **the Registry exists and has real callers today,
but the ledger it was built to protect is still symbol-keyed.**

---

## Original Problem

Before the Registry, a symbol string was simultaneously: the transaction
ledger's key, the price-series key, an analytics dimension (sector,
region), and the thing rendered on screen. Nothing in the codebase
distinguished "what this asset *is*" from "what a data provider *calls*
it" from "what a user should *see*." That collapse is not a coding-style
complaint — it is where every subsequent bug in this domain came from:

- **Duplicated identity logic.** By the time the epic's own read-path audit
  ran, it found the same "is this bare ticker the same instrument as its
  `.BK`-suffixed spelling?" question independently hand-rolled in five
  separate files, each with its own subtly different rules — a textbook
  ADR-004 ("[one implementation per rule](../decisions/ADR-004_ONE_IMPLEMENTATION_PER_RULE.md)")
  violation that had grown silently over the platform's life, one feature
  at a time, with nobody deciding to create the duplication on purpose.
- **Provider-specific symbols leaking into business logic.** Suffix
  conventions, DR spellings, and vendor quirks were handled at the call
  site that happened to need them that week, not at a boundary.
- **Inconsistent symbol matching.** `agents/optimizer.py` alone had
  something close to a dozen `dict[symbol, ...]` structures — the single
  widest blast radius in the codebase for a silent identity collision.
- **Replay risk.** The Replay Engine's contract — same ledger, same
  prices, same result, forever — rested on an unstated premise: that every
  symbol in the ledger would always mean what it meant when written. That
  premise is false in general; it was only ever *usually* true because the
  platform's footprint (one market, one primary provider) hadn't yet
  stressed it.
- **Technical debt that wasn't messy code.** The debt was a **missing
  institution** — no single subsystem was accountable for answering "what
  is this instrument?" Every symbol-keyed table, cache, and join was, in
  the implementation plan's own words, "an IOU written against the day
  identity moves."

None of this was a hypothetical architecture concern. The DR-symbol
normalization incident is in the decision log as a real, already-paid cost,
and it is the concrete proof, cited throughout this epic's documents, of
what happens when a provider's naming convention is treated as identity
instead of evidence.

---

## Original Design Goals

The goals set before implementation began, and why each one mattered:

- **Canonical identity.** One real-world instrument must map to exactly one
  `asset_id`, forever. Everything else in the architecture exists only to
  keep this guarantee true.
- **Provider independence.** A provider owns a namespace, not the truth.
  Demoting providers from identity sources to witnesses means a vendor
  changing its symbol convention becomes a one-row evidence update instead
  of a codebase-wide incident — the DR-normalization incident, but made
  structurally impossible to repeat.
- **Replay safety.** The ledger is immutable and forever
  ([ADR-001](../decisions/ADR-001_TRANSACTION_LEDGER_SINGLE_SOURCE_OF_TRUTH.md)).
  Whatever key it uses must mean the same thing on every future day it is
  read. A symbol cannot promise that; an opaque, platform-minted
  `asset_id` can, because the platform — not a vendor, not an exchange —
  is the only party accountable to its own ledger.
- **Compatibility-first migration.** No flag days. The old symbol-keyed
  world and the new identity-keyed world had to coexist for the entire
  epic, with every switchover per-consumer, reversible, and independently
  verifiable. This goal shaped every milestone's shape more than any other
  single decision — see "Major Architectural Decisions" below.
- **Single source of truth.** Exactly one subsystem answers "what is
  this?" No engine, import path, or provider holds a private identity
  mapping running alongside the Registry's own.

These goals were never revised. What changed, repeatedly, was the shape of
the *milestones* built to reach them — see "What Changed During
Implementation."

---

## Major Architectural Decisions

**The Canonical Asset Model (M1).** A two-tier identity: a small permanent
core (`asset_id`, `canonical_symbol`, assigned once, never reassigned) and
a growing, mutable evidence tier (ISIN, provider symbols, display symbol,
etc.) that the world is allowed to keep changing. This decision is why the
Registry can absorb a ticker rename, a vendor going out of business, or a
recycled symbol without ever touching a row that any ledger references —
identity and description were separated from the start, rather than
retrofitted later.

**The Identity Resolver as adjudicator, not matcher (M3).** The resolver
does not return a best guess; it returns one of five outcomes that collapse
onto three honest positions — decisive, ambiguous, unknown — and an
ambiguous or conflicting verdict is *surfaced as a Registry Finding*, never
silently resolved. This is the architecture's single most load-bearing
rule ("resolve decisively or ask — never guess," ASSET_REGISTRY.md §4), and
it was enforced mechanically, not just in prose: `test_resolve_never_
mutates_assets_table` and equivalent tests assert the resolver cannot
create or merge an asset on its own initiative under any confidence level
short of certainty.

**A current mapping preempts an asset's own stale history.** A genuine bug
was caught during M3's own test-writing, before it ever reached
production: without this rule, an asset's *own* superseded identifier
would count as a second competing candidate against its own live mapping
for the same value, manufacturing false ambiguity out of an asset
correctly re-describing itself. Small in isolation, but the kind of defect
that would have made the resolver noisier — and therefore less trusted —
than the architecture it was implementing.

**Registry-first identity, with `Unresolved` as a first-class, non-
exceptional value.** Every consumer-facing function in the Compatibility
Layer returns either a resolved `AssetView` or an honest `Unresolved`
reason string — never an exception for the ordinary case of "the Registry
doesn't know yet." This is the mechanism that made the entire
Compatibility-Layer track safe to ship incrementally while the Registry's
own coverage was, and still is, partial: callers fall back to today's
symbol-string behavior automatically, by construction, rather than by
remembering to add a try/except at every call site.

**Boundary-first migration, enforced by an explicit exclusion list.** The
Compatibility Layer's `resolve_asset()` was, from its first line of
documentation, forbidden from being called inside
`services/portfolio_rebuilder.py`'s replay loop or `services/
ledger_validator.py`'s CHECK functions — the two places where a read-time
Registry lookup could introduce exactly the kind of silent behavior change
during coexistence that Migration Principle 3 forbids. Every phase of the
Compatibility Layer re-states this boundary rather than assuming a reader
remembers it from an earlier document.

**Pure-function preservation over pure-function modification.** Repeatedly,
when a correctness fix was needed inside an already-pure, already-tested
function (`compute_execution_analysis`, `build_action_summary`), the fix
was made at the *caller's* boundary instead — passing already-resolved
data in, rather than teaching the pure function to resolve identity
itself. This is [ADR-004](../decisions/ADR-004_ONE_IMPLEMENTATION_PER_RULE.md)
applied to a subtler case than usual: not "don't duplicate the resolver,"
but "don't let the resolver's presence erode a function's documented
purity contract."

**Compatibility Layer before Native Integration — a second, distinct
compatibility layer, not an extension of the first.** The original plan's
"compatibility layer" meant symbol↔asset_id mapping totality for M1–M4's
own live provider flows. The read-path audit (2026-07-09) found a second,
separate need: non-ledger consumers wanting Registry-informed reads
*before* the ledger itself becomes id-keyed. `resolve_asset()` is that
second layer, and the decision to name it, scope it, and gate its removal
at M7 separately from the first is why the majority of this epic's
practical, running-in-production value shipped without waiting on M5 Track
B at all.

---

## What Changed During Implementation

**M5 split into Track A and Track B.** The plan's original M5 was one
milestone: adjudicated backfill, full coverage, replay parity, engine
cutover. What actually shipped first — a ledger-evidence builder, a
migration planner, a migration executor, a Registry bootstrap — never
touched `Transaction`, `PortfolioItem`, or `PortfolioSnapshot`, by explicit
design at every step. Rather than call that "M5 done" on the strength of
adjacent tooling, the plan was revised to name Track A and Track B
separately. The stated reason is worth internalizing as a general
practice: treating substantial adjacent work as if it satisfied a
milestone's actual Definition of Done would have been "a false signal to
every milestone depending on M5's hard gate" — precisely the kind of
optimistic status reporting the epic's own audit discipline exists to
prevent.

**M6 split into Compatibility-Layer and Native Integration**, for the same
underlying reason, discovered by the same audit: most read-path work
(optimizer internals, execution sizing, analytics, evaluation, watchlist)
does not actually require the ledger to be id-keyed to become
Registry-informed. Only the ledger-adjacent paths — replay itself, and the
frozen-plan-vs-live-`Transaction` join in AI Evaluation — do. Splitting the
milestone let roughly six sprints of real, shippable, risk-bounded value
proceed on a schedule independent of M5 Track B's unknown timeline.

**Scope was narrowed at milestone kickoff, repeatedly, and each narrowing
was recorded as an explicit deviation rather than silently absorbed.** M3
dropped bulk mode and shadow mode (no M5 backfill or live import door
existed yet to serve them). M4 was retitled "Provider Adapter Layer" and
shipped only the translation abstraction and one concrete adapter, leaving
the fuller scope — live-flow coverage, dual-key equivalence audits,
resolver corroboration wiring — explicitly undone rather than claimed. In
every case, the milestone's implementation notes state the original scope
verbatim alongside what actually shipped, so a future reader sees the gap
without having to reconstruct it from git history.

**Phase 3 step 8 was rescoped mid-flight.** The brief asked for
`asset_id`-aware read paths in `plan_grader.py` and
`optimizer_action_summary.py`. A full read of both (not a grep) found
neither has a genuine cross-source identity join to fix — both index a
dict built from the same list they were constructed from. Implementing the
originally-worded fix would have been decorative. The actual correctness
gap in that domain turned out to live one layer over, in
`execution_ledger.py`'s plan-vs-live-`Transaction` join — and that is what
got fixed instead, under a corrected understanding of the brief's intent
rather than its literal wording.

**Classification Consolidation absorbed a Watchlist pilot that came before
it.** The read-path plan named Phase 1 step 2 (Watchlist) and Phase 7
(Classification) as the two legitimate remaining tracks after the Phase 5
completion audit found nothing else qualified. Both shipped the same day,
in the order the dependency made natural — Watchlist first, since it was
already scoped as the lowest-risk pilot consumer.

---

## Unexpected Findings

**Fewer consumers than expected, twice, from the same category of
mistake.** `execution_report.py` was named in two separate task briefs
(the M6 Phase 4 read-path audit and, independently, the Classification
Consolidation predecessor work) as a migration target. It does not exist
anywhere in this codebase, in either case — the only match both times was
an unrelated CLI helper in `manage.py`. This was not caught by trusting
the brief; it was caught by the standing rule to audit by reading files in
full rather than assuming a named list is accurate. The lesson generalizes:
a task brief's list of targets is a hypothesis, not a fact, and this epic
found on two separate occasions that treating it as fact would have
produced work on a file that does not exist.

**An audit corrected a previous audit.** `attribution_engine.py` had been
classified, in an earlier pass, as "confirmed symbol-agnostic" — its
attribution/BHB math genuinely is. The Phase 4 audit, reading the file in
full rather than trusting the prior classification, found one function,
`_timing_and_fee_effects`, that was a fourth, previously undocumented
consumer of the exact plan-vs-live-`Transaction` join the rest of the
domain was being fixed for. The earlier classification wasn't wrong about
the file's dominant behavior; it was incomplete about one function inside
it. This is the strongest evidence in the whole epic for reading files in
full rather than grepping for keywords — a keyword search for "symbol"
would likely have found this function anyway, but the *classification* of
what it does required reading the surrounding logic, not just locating the
identifier.

**Duplicated `.BK`-variant logic was worse than a clean count suggested.**
The read-path audit named five files with independent shims. Wiring them
up surfaced a sixth, previously undocumented consumer
(`portfolio_construction.py`, via a shared helper) and revealed that
several of the five were internally *asymmetric* — one direction of the
bare-ticker/`.BK`-suffix match implemented, the other silently missing,
inconsistently across files. The unified replacement is symmetric
everywhere, which is a real, intentional behavior change (documented,
additive-only, and verified to add matches no old code depended on the
absence of) — a reminder that "consolidate five duplicate implementations"
sounds like a pure refactor and occasionally isn't, because duplicates
drift, not just multiply.

**Three sector-normalization implementations had already silently
diverged before the Registry epic ever started.** `agents/optimizer.py`,
`services/idea_review.py`, and `services/optimizer/policy_engine.py` each
carry their own `normalize_sector`/`_norm_sector`, and `policy_engine.py`'s
own source comment admits it is "deliberately reduced... to avoid circular
import with optimizer.py." This predates the Registry entirely — the
Classification Consolidation audit simply found it, because it was
specifically looking for the *pattern* (a function taking a symbol and
returning a classification fact) rather than the *name*. It was not fixed,
on purpose: unifying three rulesets that already disagree on some inputs
would change behavior for at least two of the three call sites, which
directly conflicts with an adoption milestone's mandate to leave existing
behavior unchanged. The finding was recorded with a named blocking
dependency (a product decision on the canonical ruleset) instead.

**The Registry's own coverage numbers were better than the risk section
feared, and worse than "done" would suggest.** The bootstrap validation
run against production-like data resolved 41 of 52 historical transactions
(79%) and 21 of 25 claim shapes (84%), with only 2 duplicate clusters and
zero symbols quarantined — the ambiguity-volume risk that most worried the
original plan turned out to be small, not the schedule-breaking workstream
it might have been. But "small" is not "zero": 21% of ledger transactions
still have no resolvable identity, and that backlog is now the named,
explicit precondition on M5 Track B's Definition of Done — Track A's own
adjudication debt, not Track B's to absorb silently.

**The safety of Classification Consolidation rested on a fact that had to
be actively verified, not assumed.** `_get_sector()`'s new Registry-first
check is provably behavior-preserving today for exactly one reason: the
Registry currently holds *zero* SECTOR classification facts anywhere,
confirmed by inspecting every milestone's own implementation notes for any
code that writes `AssetClassification` rows. That fact — not a design
property, a current-data property — is what made shipping a
Registry-checks-first code path safe before the seed script had ever run
once. It is also a fact that expires: once `seed_registry_classification
--commit` runs, this byte-identical-until-seeded property no longer holds
by construction, and a future change to `_get_sector()` cannot assume it.

**The Execution & Evaluation domain's completion review found *nothing to
migrate*, and that was the deliverable.** Phase 5's brief allowed two
outcomes: implement what qualifies, or declare the domain complete with
rationale. Every remaining candidate was read in full and classified;
zero satisfied all four required conditions (genuine cross-source identity
join, Registry materially improves correctness, no schema change, no
business-logic redesign) simultaneously. A phase whose entire shipped
artifact is an audit table and a "not now" on every row is still a real
deliverable — it converts an open question ("is there more Registry work
hiding in Execution/Evaluation?") into a closed one, which is exactly what
let the Compatibility-Layer track be declared complete with confidence
rather than left open indefinitely on the chance something was missed.

---

## Engineering Principles That Worked

- **Audit before implementation, by reading files in full.** Every phase
  of the Compatibility Layer opens with a full-file audit, not a grep
  pass, and the `attribution_engine.py` and `execution_report.py` findings
  above are the direct payoff — both would have been missed or
  mischaracterized by keyword search alone.
- **Boundary-first migration.** Fixing `execution_ledger.py`'s caller
  rather than `execution_analyzer.py`'s pure function, never calling
  `resolve_asset()` from inside replay or the ledger validator — the
  discipline of fixing at the boundary that assembles data, not the
  function that consumes it, kept every already-tested pure function's
  contract intact through six phases of change.
- **Preserve pure functions.** Directly downstream of boundary-first
  migration: a function documented as having "no AI calls, no DB access,
  no side effects" was treated as a hard constraint on *where* a fix could
  live, not a description to work around.
- **Compatibility before persistence.** The single decision — split M6 so
  most of its value doesn't wait on M5 Track B — is why this epic has real
  production callers today instead of an architecturally complete but
  functionally inert Registry sitting beside a codebase that still ignores
  it.
- **Additive API evolution.** Every response-shape change across the
  entire epic (Watchlist's `"registry"` key, the Recommendation
  snapshot's enriched `scores_map_json`, `AssetView`'s fields) added a key;
  none renamed or removed one. This is why zero frontend or downstream
  consumer code ever needed to change in lockstep with a backend Registry
  phase shipping.
- **Regression-first development, verified mechanically, every phase, no
  exceptions.** Every changelog entry in this epic states an exact
  before/after pass count and an exact, diffed failure set, produced by
  `git stash`-isolating the change and re-running the full suite twice.
  "Zero regressions" is asserted as a measured fact with a number attached
  in every single entry, not a claim taken on faith.
- **Documentation-driven engineering, including documenting deviations.**
  When a milestone's actual scope diverged from its originally-written
  text (M3's dropped bulk/shadow mode, M4's narrowed Provider Adapter
  Layer, Phase 3 step 8's rescoping), the original text was kept verbatim
  next to the revision, with the reason stated. A future reader — human or
  agent — can tell what was *intended* from what *happened* without
  reconstructing intent from commit messages.

---

## Metrics

Avoiding vanity metrics — these are the ones that were actually load-
bearing for the decisions made along the way:

- **Milestones complete:** M1 (identity core), M2 (registry service), M3
  (resolver) — fully complete. M4 (provider adapters) — partially complete
  by deliberate, documented scope narrowing. M5 Track A (evidence,
  planning, bootstrap tooling) — complete. M5 Track B (native ledger
  persistence) — not started. M6 Compatibility-Layer Integration — all 7
  named phases shipped. M6 Native Integration — blocked on M5 Track B, not
  started.
- **Bootstrap coverage against production-like data:** 21/25 claim shapes
  resolved (84%), 41/52 transactions resolved (79%), 2 duplicate clusters
  correctly left unminted rather than auto-resolved, 0 quarantined.
- **Duplicate implementations retired:** 5 independently hand-rolled
  `.BK`-variant matchers (plus a 6th undocumented consumer found while
  wiring the fix, plus 4 separate instances of the same pattern inside
  `idea_review.py` alone) — all replaced by one shared adapter.
- **Duplicate implementations found but deliberately not retired:** 3
  divergent `normalize_sector` copies, already disagreeing on real inputs,
  recorded as technical debt with a named blocking dependency rather than
  silently reconciled.
- **Zero-migration outcome:** the Phase 5 Execution & Evaluation
  completion review — a full audit of the remaining domain that concluded
  no further code change was warranted, closing the question rather than
  leaving it open.
- **Regression discipline:** every phase boundary in this epic (at least
  a dozen distinct shipped changes) was verified via `git stash` isolation
  with a before/after pass-count delta matching exactly the number of new
  tests added, and a byte-identical pre-existing-failure set in every
  single case.
- **Documentation produced:** the frozen architecture (`ASSET_REGISTRY.md`,
  unmodified by this epic), the epic plan
  (`ASSET_REGISTRY_IMPLEMENTATION_PLAN.md`), the read-path plan
  (`M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md`), and two focused
  migration write-ups (`WATCHLIST_REGISTRY_PILOT.md`,
  `CLASSIFICATION_CONSOLIDATION.md`) — each carrying its own audit,
  migration summary, and technical-debt register rather than deferring
  that bookkeeping to a shared, generic changelog.

---

## Remaining Technical Debt

Named here without redesigning any of it — that redesign, if and when it
happens, belongs to the milestone that owns each item:

- **Native Asset Persistence (M5 Track B).** `Transaction`, `PortfolioItem`,
  and `PortfolioSnapshot` still carry no `asset_id` column. This is the
  epic's original center of gravity and its highest-risk remaining
  milestone — every mitigation the plan specifies (adjudicated backfill,
  per-portfolio replay parity as a hard gate, flagged cutover) still
  applies unchanged. It remains gated on
  [ADR-005](../decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md) being
  accepted before golden baselines can even be captured.
- **Ledger backfill.** Blocked on Track B directly; also blocked on
  clearing or explicitly waiving Track A's own adjudication backlog (2
  duplicate clusters, 11 unresolved transactions as of the last bootstrap
  run) — that backlog is Track A/M2 debt, not something Track B inherits
  the right to solve from scratch.
- **Replay.** `services/portfolio_rebuilder.py`'s replay loop and
  `services/ledger_validator.py`'s CHECK functions remain entirely
  untouched by every Compatibility-Layer phase, on purpose. They stay that
  way until Track B's parity gate exists — introducing a Registry lookup
  there first would be exactly the "silent behavior change during
  coexistence" the migration principles forbid.
- **Compatibility-layer removal.** Gated on M5 Track B and M6 Native
  Integration both completing, plus their probation periods elapsing, plus
  one explicit go decision — this is M7, and it is deliberately the one
  step in the whole plan that is not trivially reversible, which is why it
  is last.
- **Optimizer redesign.** `agents/optimizer.py`'s internal `dict[symbol,
  ...]` structures (`score_map`, `pc_map`, `alloc_map`), the consensus
  engine's symbol-set overlap scoring, and the `policy_engine.py`
  free-text-violation / `execution_optimizer.classify_reason`
  substring-search coupling are all named, real risks — deliberately left
  alone because fixing the last one requires `policy_engine.py` to emit a
  structured field instead of prose, which is a business-logic redesign of
  the violations contract, outside any read-path or adoption milestone's
  authority.
- **Classification gaps.** Three divergent `normalize_sector`
  implementations, `idea_review.py`/`basket_simulation.py`'s sector
  fallback chains not yet Registry-classification-aware, `SignalHistory`
  carrying no `asset_id`/registry-metadata column (schema-change-blocked),
  and `execution_penalty.classify_execution`'s ticker-shape asset-type
  inference (blocked on threading a `db` session into a synchronous
  optimizer call chain) — all documented with the specific blocking
  dependency that would need to be resolved first, in
  [CLASSIFICATION_CONSOLIDATION.md](../implementation/CLASSIFICATION_CONSOLIDATION.md) §4
  and [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) §6.

---

## Lessons Learned

**What surprised the team:** how often "audit the named targets" turned
into "most of the named targets don't need this, and one un-named target
does." `execution_report.py` not existing twice, `plan_grader.py`/
`optimizer_action_summary.py` having no genuine join to fix, the Phase 5
domain review concluding in zero migrations — the pattern repeats often
enough across this epic's changelog that it is not noise, it is a
property of how these briefs get written: a plausible-sounding list of
suspects, assembled without reading every file first, that a real audit
routinely both prunes and extends.

**What should be repeated:** treating a task brief's named file list as a
hypothesis to verify, never a fact to implement against; reading files in
full before classifying them, since the `attribution_engine.py` finding
shows a prior *keyword-level* classification can be right about a file's
dominant behavior and still miss a real risk inside it; recording every
scope deviation with the original text preserved alongside the revision,
so intent and outcome are both visible later; verifying "zero regressions"
mechanically (a diffed failure list, an exact pass-count delta) rather
than asserting it; and writing down technical debt with a named blocking
dependency rather than a bare TODO, because "blocked on a product decision
about which ruleset is canonical" is actionable in a way "someday unify
these" is not.

**What should be avoided:** reconciling divergent implementations
opportunistically because you happen to be touching the area — the three
`normalize_sector` copies were found and correctly left alone, precisely
because "while we're in here" is how identity-adjacent code accumulates
silent behavior changes across an adoption milestone that promised none.
Also worth avoiding: treating adjacent, real, well-tested tooling as
satisfying a milestone's actual Definition of Done — Track A's bootstrap
tooling is genuinely valuable and was not "M5," and conflating the two
would have quietly weakened the one gate (replay parity) this entire epic
exists to protect.

---

## Future Roadmap

Kept high level, since the detailed shape of each item belongs to the plan
document that owns it, not this retrospective:

- **M5 Track B — Native Ledger Persistence.** Accept ADR-005, capture
  golden baselines, clear or explicitly waive Track A's adjudication
  backlog, run the adjudicated backfill, and gate every engine cutover on
  bit-identical replay parity. This is the next real milestone in the
  epic and the one every subsequent step depends on.
- **M6 Native Integration.** Once Track B lands, revisit every call site
  the Compatibility Layer touched so it reads a native `asset_id` directly
  instead of resolving one at read time — the Compatibility Layer was
  always meant to be superseded here, not to persist indefinitely.
- **Compatibility removal (M7).** Retire the shims, retire symbol columns
  as *keys* (never as evidence — symbols stay in the Registry's evidence
  tier forever), and run the architecture's own final audit: no engine
  below the resolution boundary should be able to tell what any asset is
  called.
- **Multi-Asset expansion.** The Registry was built to onboard funds,
  bonds, crypto, property, options, futures, and private equity without a
  redesign — each is a question of what its evidence file looks like, not
  whether the identity model fits. That expansion is real future product
  work, deliberately not started, and deliberately not blocked by
  anything in this epic.

---

## Closing Remarks

Before this epic, "what is this asset?" was a question every engine
answered for itself, from a string, on its own schedule — and the platform
had already paid for that once, in the DR-symbol-normalization incident
that this document's own philosophy section still cites. The Registry
makes that question answerable exactly once, by one authority, in a way
that survives a provider disappearing, a ticker being recycled, or a
company renaming itself on its home exchange.

It is not finished. The ledger — the one place identity errors are
irreversible, because replay reproduces them forever — is still
symbol-keyed, and will stay that way until M5 Track B closes that gap
under its replay-parity gate. But the Registry is no longer a subsystem
sitting beside the platform, unused. It has real callers in the optimizer,
in execution planning, in AI evaluation, in the watchlist, in human idea
intake, and in sector classification — each one wired in without a single
flag day, without rewriting a frozen historical record, and without
changing one existing user-visible behavior until the moment the Registry
actually has something better to say. That is the shape the whole
migration strategy was designed to produce, and it is the shape a future
maintainer should expect to keep building in: additive, boundary-first,
audited before it is implemented, and honest — via `Unresolved`, via
surfaced ambiguity, via technical-debt entries with named blocking
dependencies — about exactly how far it has gotten.

The Asset Registry is now a shared platform capability, not an isolated
feature. The next engineer who needs to know what an asset *is* should
reach for `resolve_asset()`, not write a sixth `.BK`-suffix check.

---

## Related Documents

- [ASSET_REGISTRY.md](ASSET_REGISTRY.md) — the frozen architecture this
  retrospective explains the history behind, not a replacement for it.
- [REGISTRY_INTEGRATION_GUIDE.md](REGISTRY_INTEGRATION_GUIDE.md) — the
  developer-facing usage guide for `resolve_asset()` and every consumer
  wired into it so far.
- [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](../implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) —
  the M0–M7 milestone plan, including the full changelog of scope
  revisions this document draws its "What Changed" section from.
- [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](../implementation/M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) —
  the read-path audit and its Technical Debt Register, the primary source
  for this document's "Remaining Technical Debt" section.
- [WATCHLIST_REGISTRY_PILOT.md](../implementation/WATCHLIST_REGISTRY_PILOT.md),
  [CLASSIFICATION_CONSOLIDATION.md](../implementation/CLASSIFICATION_CONSOLIDATION.md) —
  the two focused migration reports this retrospective synthesizes
  findings from.
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the
  original incidents (DR symbol normalization, provider quirks) that first
  established why identity must be owned, not borrowed.
