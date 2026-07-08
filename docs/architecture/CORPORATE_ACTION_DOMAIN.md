# Corporate Action Domain

*Corporate actions are real-world events that change the legal or economic structure of financial instruments without ordinary trading: splits, mergers, spin-offs, redemptions, renamings. This document defines how the platform understands, validates, records, and preserves those events — as the bridge between Asset Identity and Canonical Transactions, owning neither.*

*This is not an implementation guide, not a replay algorithm, and not a market-data synchronization design. It is the handbook's first pure **adjudication domain**: every other domain so far owns a permanent record — the Registry owns identity, the ledger owns events, the portfolio owns its boundary. This domain owns a **process**: the disciplined path by which a market's announcement becomes, on one side, identity facts in the [Asset Registry](ASSET_REGISTRY.md), and on the other, canonical events in the [transaction ledger](TRANSACTION_DOMAIN_MODEL.md). Both destinations were reserved in advance — ASSET_REGISTRY.md §7 reserved the identity side, TRANSACTION_DOMAIN_MODEL.md §3 reserved the structural event family, and BROKER_ACCOUNT_DOMAIN.md §5 reserved the claim-for-confirmation door. This document fills the space between them.*

---

## 1. Philosophy

### Corporate actions are facts, not calculations

A stock split is not something the platform computes; it is something that *happened*, out in the world, to an instrument the user holds. This distinction governs everything: the platform's job is never to derive a corporate action from suspicious price movements or infer one from a broker's suddenly-doubled position — it is to **learn** the event from witnesses, **adjudicate** what the event means, and **record** the consequences in the two places consequences live. A platform that calculates corporate actions manufactures facts; a platform that adjudicates them curates facts. Only the second kind can be trusted with an immutable ledger.

### Markets announce; the platform adjudicates; replay consumes

The three verbs assign the three roles, and none of them overlaps:

- **Markets announce.** Announcements reach the platform through witnesses — market-data providers describing the world's events (PROVIDER_INTERFACE.md), brokers reflecting the events' effects on the user's own positions (BROKER_ACCOUNT_DOMAIN.md). Like every witness statement in this architecture, an announcement is a *claim*: evidence of arbitrary quality, carrying zero authority of its own.
- **The platform adjudicates.** Announcements are validated, cross-checked, interpreted, and — because corporate actions touch the user's permanent records — confirmed before anything is written. This is the platform's judgment/arithmetic boundary applied to the one event class where a mistake corrupts *both* permanent authorities at once: get a merger wrong and the Registry's identity graph and the ledger's replayed history are wrong together, in a correlated way that each authority's own defenses cannot catch alone.
- **Replay consumes consequences.** By the time the Replay Engine runs, there are no announcements left to see — only recorded canonical events, admitted through the same standards as every other transaction (§8). Replay never interprets a corporate action; interpretation finished before recording began.

What makes this domain necessary — rather than folding the work into the Registry or the import pipeline — is that corporate actions are the only events whose consequences must land in two authorities *consistently*. A spin-off that creates a child asset in the Registry but no position event in the ledger, or vice versa, is worse than no processing at all. Someone must own the whole interpretation as one decision. That someone is this domain.

---

## 2. Responsibilities

### What the Corporate Action Domain owns

- **Announcements** — the permanent record of every corporate-action claim the platform has received: what was announced, by which witness, when, in which terms, and how those terms changed as the announcement was amended, corrected, or cancelled. Announcements are kept forever, including the ones that were rejected or never took effect — the domain's audit trail is the history of what the world *said*, not just what the platform accepted.
- **Effective dates and the event timeline** — the dated structure of each action as the market defines it: when entitlement is fixed, when the change takes economic effect, when consideration is paid. These are facts about the event, owned here because they decide *where in event time* the consequences will eventually land (§8).
- **Event interpretation** — the adjudicated answer to "what does this announcement mean?": which event family it belongs to (§3), which assets it touches, what it does to quantities, cash, and identity, and — critically — whether it means anything for a given holder at all. Interpretation is the domain's core act and its only difficult one.
- **Identity relationship proposals** — the identity consequences an interpretation implies (successor-of, spun-off-from, renamed, terminal status), formulated as proposals *to* the Asset Registry, which remains the sole authority over whether and how its identity graph changes (§4).
- **Transaction proposals** — the ledger consequences an interpretation implies for each affected portfolio, formulated as claims for confirmation entering the standard admission pipeline (§5). The domain computes what the events *should be*; it never writes them itself.
- **Validation** — the standards an announcement must meet before its consequences may be proposed anywhere: internal consistency, cross-witness agreement, completeness of terms, plausibility of ratios (§7).

### What the Corporate Action Domain never owns

- **Asset identity.** The domain proposes; the Registry disposes. No corporate action processing ever mints, merges, renames, or retires an `asset_id` directly (ASSET_REGISTRY.md §2).
- **The ledger.** Proposed events survive resolution, attribution, and validation like every other claim, and once recorded they are the ledger's — immutable, replayed, and beyond this domain's reach (TRANSACTION_DOMAIN_MODEL.md §1).
- **Portfolio state, replay, valuation.** All derived downstream, by the same machinery, from the same canonical inputs, with no corporate-action-shaped side channel (§8).
- **Performance and risk.** How a structural event flows through returns and exposures is owned by the calculation rules and the future analytics domains (§10). This domain records that quantities rescaled; it holds no opinion about what that did to anyone's performance — the correct answer, for the record, being *nothing* (§10).

The compressed statement: **this domain owns the question "what did the world just do to this instrument?" — and nothing that depends on the answer.**

---

## 3. Canonical Event Families

The world's corporate-action vocabulary is large, jurisdiction-flavored, and vendor-inflected. The platform's vocabulary is small and organized — as with transactions (TRANSACTION_DOMAIN_MODEL.md §3), by *answer-pattern*, not by name. The questions every event must answer: does quantity rescale? does identity continue, transform, or end? does cash or a new position reach holders? does the holder face a choice? The families below are the recurring answer-patterns; the names are vocabulary, not an enumeration.

**Quantity restructuring — Stock Split, Reverse Split, Bonus Shares.** Quantity rescales by a ratio; identity continues; total economic value is unchanged at the instant of the event. The simplest family and the calibration case for every rule in this document: a split must produce a rescaling event in the ledger, zero change in the Registry beyond a recorded occurrence, and *zero* performance effect — any design in which a split moves a return number is wrong by definition.

**Distributions — Cash Dividend, Stock Dividend.** Value flows to holders: cash in the ordinary case, additional units in the stock-dividend case. Routine cash dividends already live in the transaction domain's income family and flow through ordinary import doors; what this domain owns is the *announcement side* — declared terms, entitlement dates, and the unusual forms (elective dividends, special distributions) whose interpretation is not routine. The boundary is deliberate: a dividend that arrives as broker evidence is an income event; a dividend that must be *anticipated, validated, or reconciled against its announcement* is this domain's business.

**Entitlements — Rights Offering.** Holders receive an option, not an outcome: the right to subscribe, which may be exercised, sold, or allowed to lapse. Entitlements are the family that introduces *holder decisions* into the lifecycle — the platform can validate and record the entitlement, but the consequence depends on what the user chooses, and the domain must represent "granted, awaiting decision" honestly rather than assuming an outcome.

**Identity restructuring — Spin-off, Merger, Acquisition.** The family that earns this domain its place in the architecture: identities transform. A spin-off births a new asset whose position appears without a purchase; a merger ends one identity inside another with conversion terms; an acquisition ends an identity in cash, securities, or both. Every event here has consequences in *both* authorities, and their consistency is exactly the one-decision problem §1 identified.

**Cosmetic identity — Ticker Change, Name Change.** The proof case for the ownership split: consequences land *entirely* in the Registry's evidence file and *nowhere* in any ledger. A renamed ticker is new external evidence mapped to the same permanent `asset_id` (ASSET_REGISTRY.md §5); no transaction is proposed because nothing economic occurred. A design that generates ledger events for renames has confused names with facts — the exact confusion the identity architecture exists to prevent.

**Terminal events — Delisting, Liquidation, Bond Redemption.** The instrument's story ends, gracefully or not: a scheduled redemption returns principal; a liquidation distributes residual value; a delisting may end trading without ending ownership. Terminal events pair a Registry lifecycle transition (Delisted, Archived — ASSET_REGISTRY.md §6) with final ledger events where value actually flowed — and with honest *absence* of ledger events where it didn't, because a delisted holding the user still owns is a position, not a disposal.

**Non-events — ETF Rebalancing and its relatives.** Some loudly announced happenings have *no consequences for holders* in either authority: a fund rebalancing its internal composition changes what the fund holds, not what the user holds — no quantity change, no identity change, no cash. The family exists so the interpretation step has a first-class verdict of "true, announced, and irrelevant to the ledger": descriptive updates may flow to the Registry's classification stewardship, and nothing else happens. A domain without this verdict inevitably invents transactions for events that need none.

Two properties bind all families. First, **classification precedes consequence**: the family verdict is decided before any proposal is formulated, because the family *is* the interpretation (the classify-before-mapping rule of ASSET_REGISTRY.md §7, stated from this side of the boundary). Second, **the vocabulary is closed and platform-owned**: witnesses announce in their dialects; the domain classifies into its own families; no vendor's event taxonomy ever becomes the platform's.

---

## 4. Relationship with Asset Registry

Corporate actions are the main force that bends identity over time, and the entire bend is absorbed by the Registry's existing model — which is precisely why the Registry was designed as it was:

- **Identity continuity.** Splits, dividends, renames: the `asset_id` continues untouched. The Registry records that the event occurred (dated facts in its stewardship); the ledger records what it did to quantities. Nothing about *who the asset is* changed.
- **Identity replacement.** Mergers and acquisitions end an identity — into its Merged/Archived lifecycle state, never into deletion. The predecessor's `asset_id` remains permanently answerable, because a decade of ledger events reference it and always will (ASSET_REGISTRY.md §10).
- **Identity relationships.** The connections corporate actions create — *successor-of* for mergers, *spun-off-from* for spin-offs, *converted-into* for reorganizations — are exactly the explicit-relationship vocabulary the Registry already maintains in place of ever merging records (ASSET_REGISTRY.md §5). This domain is that vocabulary's principal author: most relationships in the identity graph will have a corporate action as their provenance.
- **Successor assets.** When a spin-off or merger requires an identity that does not yet exist, the new asset enters through the Registry's ordinary claim lifecycle — Discovery, Candidate, Verified — with the corporate action as its discovery door and its strongest evidence. This domain never mints; it nominates.
- **Historical traceability.** The composed guarantee: because ledger events reference permanent `asset_id`s (TRANSACTION_DOMAIN_MODEL.md §6) and the Registry preserves every predecessor with its relationships, any position can be traced through any sequence of renames, splits, spin-offs, and mergers, in either direction, forever. Traceability is not a feature this domain builds — it is what falls out of both authorities keeping their own records honestly.

The Registry remains the authority throughout, for the same reason providers cannot resolve identity (ASSET_REGISTRY.md §9): authority follows accountability. This domain sees events one at a time; the Registry answers for the coherence of the whole identity graph — including refusing a proposed relationship that contradicts evidence it already holds. A proposal refused is a conflict surfaced, and conflicts are adjudicated, never forced.

---

## 5. Relationship with Transactions

**Corporate actions never edit transactions — not even the transactions they make "obsolete."** A holder bought 100 shares in 2020; a 2:1 split takes effect in 2023. The 2020 ledger row says 100 shares, at the 2020 price, forever — because that is what happened, and the ledger records what happened (TRANSACTION_DOMAIN_MODEL.md §1). The split enters as a **new canonical event** — the structural family reserved in TRANSACTION_DOMAIN_MODEL.md §3 — dated at its effective date, rescaling the position from that moment forward. Replay, consuming the whole stream in event order, carries 100 shares until the split event and 200 after: history is continuous, every row is true, and no arithmetic was ever performed *on* a recorded fact.

The contrast worth naming: the financial-data world routinely handles splits by *back-adjusting* — rewriting historical price series so the past matches the present. That is a legitimate read-time presentation concern, and it belongs entirely to the Market Data Platform's handling of observations. It is never a ledger operation. A ledger that back-adjusts has rewritten history to make the present convenient — the precise thing an immutable memory exists to never do.

The consequences this domain proposes are otherwise ordinary citizens of the transaction domain:

- They enter through the admission pipeline — resolution, attribution, validation — as claims for confirmation (BROKER_ACCOUNT_DOMAIN.md §5), not as privileged writes. A merger affecting three portfolios becomes three attributed proposals, each landing in exactly one ledger.
- They are append-only in every direction: a *corrected* corporate action (an amended ratio, a revised effective date) never edits the recorded events either — it appends correcting events under the same discipline as any restatement (TRANSACTION_DOMAIN_MODEL.md §4).
- They carry provenance: the announcement, the witnesses, the adjudication that produced them — so that every structural event in every ledger is auditable back to what the world said and who confirmed the platform's reading of it.
- They are deduplicated like everything else: the same split learned from a provider announcement *and* reflected in a broker's statement must converge on one recorded event, not two — the reconciliation of the two witness channels is part of this domain's adjudication, finished before proposal.

---

## 6. Event Lifecycle

A corporate action moves through seven stages, and each exists because skipping it has a specific failure mode:

**Announcement.** A witness said something. The claim is recorded verbatim with full provenance — because the domain's audit trail must include what was *actually said*, not the platform's later paraphrase. No interpretation has occurred; the announcement has the standing of any witness statement: evidence, not fact.

**Pending.** The announcement is acknowledged but not yet actionable — terms incomplete, effective date in the future, or corroboration awaited. Pending exists because announcements systematically precede reality: markets announce weeks ahead, terms get amended, some actions are cancelled outright. A platform without a Pending stage must either act on futures that may never happen or discard early knowledge it will want later. Pending holds the future at arm's length, visibly.

**Validated.** The announcement has passed the domain's standards (§7): internally consistent, witnesses reconciled, terms complete and plausible, family classified. Validation exists as its own stage because it is where *most* announcements should finish quickly and where the problematic ones must visibly stall — collapsing validation into approval would present unvetted claims for human confirmation, spending the owner's attention on noise the machine should have caught.

**Approved.** The platform's reading of the event — its family, its terms, its proposed consequences for the affected portfolios — is confirmed. Approval is the claim-for-confirmation discipline (BROKER_ACCOUNT_DOMAIN.md §5) at the moment of highest stakes, and it follows the universal pattern: decisive, well-corroborated, routine events may be confirmed by standing policy; ambiguous, unusual, or high-impact ones surface to the human. Approval exists because what follows is irreversible — it is this lifecycle's minting moment, deliberately parallel to the Registry's Verified (ASSET_REGISTRY.md §6): everything before it is reversible, nothing after it is.

**Recorded.** The consequences land: identity proposals adjudicated into the Registry, transaction proposals admitted into the affected ledgers — as one consistent decision, both sides or neither, because a half-recorded corporate action is the split-brain failure §1 exists to prevent.

**Replayable.** The recorded events are visible to replay at their effective dates. This is a distinct stage only because of the two-timeline rule (ADR-003, TRANSACTION_DOMAIN_MODEL.md §4): an action recorded today with last month's effective date replays *last month*, and everything derived downstream of that date recomputes honestly. Replayability is a property the events acquire from their dates — not an act anyone performs.

**Historical.** The action, its announcements, its adjudication, and its consequences are permanent record. Cancelled and rejected announcements are Historical too — the platform remembers what the world said even when the world changed its mind, because "we evaluated this and declined it" is exactly the memory that prevents re-litigating the same claim next import.

The lifecycle's shape is the platform's two-phase pattern once more: **claim states (Announcement, Pending, Validated) are reversible and cheap; fact states (Recorded onward) are permanent and expensive; Approval is the one-way door between them** — and all care concentrates at the door.

---

## 7. Validation Philosophy

Corporate-action claims fail in richer ways than price data, because they are *structured stories* rather than numbers. The validation stance is the platform's universal one — detect loudly, preserve uncertainty, never guess — applied to each failure shape:

- **Provider disagreement.** Two witnesses describe the same event with different ratios, dates, or terms. The disagreement is recorded as a first-class conflict and adjudicated by evidence quality and corroboration — never averaged, never resolved by silent preference for whichever witness answered last (the Registry's conflict discipline, ASSET_REGISTRY.md §7, governing events instead of identities).
- **Conflicting announcements.** The world amends itself: revised ratios, postponed dates, cancellations. Later announcements *supersede* earlier ones without erasing them — the announcement record is append-only like everything else — and an action already past Approval when the world changes its mind is corrected forward through appended events (§5), never unwound.
- **Missing effective dates.** An action without a date cannot land in event time, so it structurally cannot advance to Recorded — there is nowhere for it to land. It waits in Pending, visibly, however plausible its other terms. A guessed date is worse than no date: it places real consequences at a fictional point in history.
- **Partial information.** An announced merger whose consideration terms are "to be determined" is genuinely, honestly incomplete. The domain holds it at the stage its completeness supports rather than padding it with assumptions — partial truth held openly beats complete-looking fiction (the same reasoning PROVIDER_INTERFACE.md §8 applies to partial data, at higher stakes).
- **Impossible claims.** Ratios of zero, effective dates before announcement dates, splits on assets the Registry says were delisted years ago, consideration exceeding any plausible bound. Impossibility checks exist because witnesses deliver malformed data with total confidence, and the cheapest place to catch a malformed story is before anyone reads it as true.
- **Manual review.** The escalation path for everything adjudication cannot settle: genuinely ambiguous events, first-of-kind structures, conflicts where evidence balances. The human is the platform's court of last resort for judgment (the judge/describe line, applied to events), and the domain's job is to arrive in front of the human with the whole case assembled — announcements, conflicts, proposed readings — not with raw feeds.
- **Quarantine.** Where claims that can neither advance nor be honestly rejected wait: visible, inert, and outside both authorities. Quarantine here is the same first-class outcome it is at the import boundary (BROKER_ACCOUNT_DOMAIN.md §6), and for the same reason — the alternative to visible waiting is invisible guessing.

Why uncertainty is *preserved* rather than resolved by force: an uncertain corporate action affects permanent records in two authorities at once, and both are append-only — a wrong guess is not edited away later; it is corrected through events that permanently record the guess and its repair. The cheapest uncertainty is the kind still standing in the lifecycle's reversible stages. The domain therefore treats "we don't know yet" as a respectable, durable, *reportable* state — never as a gap to be papered over so a pipeline can finish.

---

## 8. Replay Relationship

**Replay consumes consequences, never announcements.** The Replay Engine's input contract (TRANSACTION_DOMAIN_MODEL.md §8) names corporate-action facts among its three permitted inputs — and this domain is what makes those facts *fit* the contract: by the time anything reaches replay, it is a recorded canonical event, admitted through full validation, attributed to one portfolio, dated in event time. Replay contains no corporate-action logic, consults no announcement store, and cannot distinguish a split event proposed by this domain from any other admitted transaction. That indistinguishability is the design goal: the domain's entire complexity — witnesses, conflicts, lifecycles, approvals — discharges *before* the ledger, so that the accounting authority downstream stays exactly as simple as it was before corporate actions existed.

**Announcements become replayable only after validation** — and after approval and recording; the lifecycle (§6) is the only path, and there is no expedited lane. A pending merger, however certain it looks, does not exist for replay. No provisional rescaling, no anticipatory position, no "the split is probably real, adjust now and confirm later" — a deterministic engine fed maybes produces authoritative-looking maybes (the same rule BROKER_ACCOUNT_DOMAIN.md §10 sets for unvalidated imports, with more at stake).

The two-timeline rule does the final honest work. An action's *effective date* places its consequences in event time; its *recording date* preserves when the platform learned and confirmed it. A corporate action learned late — a backfilled account revealing a years-old spin-off — replays at its true historical position while confessing its late arrival in provenance, and everything derived downstream of the effective date recomputes. History converges on truth regardless of the order in which truth arrived, which is the property that makes the whole architecture safe to run for decades.

---

## 9. Future Expansion

New markets bring new event stories; none brings a new *shape*. Each anticipated arrival is an existing family's answer-pattern wearing new clothes:

- **Crypto forks** — the spin-off pattern: holders of one asset receive units of a newly created one. The Registry mints the child through its ordinary lifecycle (convention-defined identity, as crypto already is — ASSET_REGISTRY.md §11); the ledger receives a position-birth event. That the "issuer" is a protocol dispute rather than a board decision changes the announcement's witnesses, not its architecture.
- **Chain migrations and token redenominations** — identity replacement and quantity restructuring, respectively: a migration is a merger-shaped conversion into a successor identity; a redenomination is a split by another name.
- **Fund mergers and class conversions** — the merger and replacement patterns applied to funds: one fund absorbed into another, or a holding converted between classes of the same strategy. The Registry's listing-granular identity model (each class its own identity where accounting facts differ) already provides the vocabulary.
- **Convertible bonds and rights subscriptions** — the entitlement and conversion patterns: an embedded or granted option that, when exercised, converts one position into another. The OPTION_EXERCISE shape (TRANSACTION_DOMAIN_MODEL.md §3) is the consequence; the entitlement lifecycle (§3) is the pathway.
- **Options adjustments** — when an underlying's corporate action cascades into its derivatives' terms: the domain interprets one real-world event into consequences across related identities, using the Registry's derivative-of relationships to find them. Cascade breadth grows; the per-identity consequences remain family-standard.
- **International market events** — jurisdiction-specific structures (odd-lot tenders, capital reductions, local entitlement customs) that arrive as unfamiliar stories and classify into familiar patterns. Where a jurisdiction's convention genuinely alters interpretation, that is announcement-side dialect — absorbed at the witness boundary like every dialect before it, never propagated into the families.

The reason no redesign is required is structural, and it is the same reason twice. On the consequence side, everything above discharges into vocabulary both authorities already speak: existing transaction families, existing identity relationships, existing lifecycle states. On the announcement side, new events are new *stories*, and the domain's machinery — witnesses, claims, families, lifecycle, validation — was built for stories in general, not for the fifteen this document happened to name. **A new corporate action type is a new classification, and classifications are cheap. Expansion adds vocabulary, never surgery.**

---

## 10. Relationship to Future Domains

Corporate actions are where several future domains would silently break if the facts were recorded carelessly — which is why this domain's honesty is *their* foundation:

- **Tax Engine.** Corporate actions are tax events of the subtlest kind: splits redistribute cost basis across new quantities; spin-offs allocate basis between parent and child; mergers may realize gains or defer them by jurisdiction and structure. The ledger records the facts (quantities, dates, consideration, linkage between predecessor and successor events); the tax engine will supply the opinions. Nothing about a tax treatment is ever stored on the events — the facts are kept complete enough that *every* jurisdiction's opinion remains computable later (TRANSACTION_DOMAIN_MODEL.md §11).
- **Performance Analytics.** The calibration truth from §3, generalized: structural events must be performance-transparent. A split is not a return; a spin-off is not income; a merger is not a disposal at a profit — value is continuous through all of them, and the classification recorded at admission is what lets the calculation rules keep it continuous. Every historical accounting incident on this platform was a flow misclassified; corporate actions are the richest future source of exactly that mistake, pre-empted here.
- **AI Evaluation.** Recommendations must be judged across structural events without distortion: a model that recommended an asset pre-split must not be graded as though the position halved, and a thesis interrupted by an acquisition needs the acquisition *visible* to the grader as an exogenous event. The two timelines carry the load — what was knowable at decision time, what happened after — and the evaluation layer reads both.
- **Risk Engine.** Exposures survive identity transformations by following the Registry's relationship graph: the successor carries the position, the spin-off child appears as new exposure, the merged predecessor's history remains attributable. Risk reads derived state and the identity graph; this domain keeps both connected.
- **Goal Planning and Wealth Domain.** Value continuity again, from the describing side: a merger does not change goal progress, and a household's net worth is indifferent to how many identities its value is currently wearing. Both domains read replayed truth, and replayed truth is continuous through structural events because §5 made it so.

The pattern is TRANSACTION_DOMAIN_MODEL.md §11's, inherited: **this domain guarantees facts recorded honestly in two authorities; every future domain stacks its interpretation on those facts without touching them.**

---

## 11. Design Principles

1. **Corporate actions are facts, learned from witnesses — never calculations, never inferences.** The platform adjudicates what the world announced; it does not manufacture events from symptoms.
2. **Identity belongs to the Asset Registry.** This domain proposes continuity, replacement, and relationships; the Registry adjudicates and records them, and may refuse.
3. **Transactions remain immutable.** Consequences are new canonical events at effective dates; no recorded row is ever rescaled, back-adjusted, or rewritten to accommodate the world's restructurings.
4. **Consequences land in both authorities as one decision.** Identity facts and ledger events from a single action are recorded consistently — both or neither; a half-applied corporate action is corruption, not progress.
5. **Replay remains deterministic and innocent.** It consumes recorded consequences indistinguishable from ordinary transactions and contains no corporate-action logic of its own.
6. **Announcements become facts only through validation.** The lifecycle is the only path from witness statement to permanent record, approval is its one irreversible door, and there is no expedited lane.
7. **Uncertainty is preserved, visibly.** Conflicts are recorded, incompleteness waits in its stage, quarantine is a respectable outcome — and no gap is ever papered over so a pipeline can finish.
8. **Classification precedes consequence.** The family verdict — including "announced and irrelevant" — is decided before any proposal is formulated; interpretation is never retrofitted to match consequences already written.
9. **History is never rewritten, including announcement history.** Amendments supersede, cancellations conclude, corrections append; the platform remembers what the world said even when the world retracted it.
10. **Structural events are performance-transparent.** No split, merger, spin-off, or redemption ever moves a return number by itself; value is continuous through every restructuring, and any design that breaks continuity is wrong by definition.
11. **The vocabulary is closed and platform-owned.** Witness dialects and jurisdictional customs die at the announcement boundary; new event types are new classifications into existing families — vocabulary, never surgery.

---

## Related Documents

- [TRANSACTION_DOMAIN_MODEL.md](TRANSACTION_DOMAIN_MODEL.md) — the immutable events this domain proposes and the structural family reserved for them
- [ASSET_REGISTRY.md](ASSET_REGISTRY.md) — the identity authority this domain proposes to, and the relationship vocabulary corporate actions author
- [BROKER_ACCOUNT_DOMAIN.md](BROKER_ACCOUNT_DOMAIN.md) — the claim-for-confirmation door and admission pipeline the proposed events travel
- [PROVIDER_INTERFACE.md](PROVIDER_INTERFACE.md) — the witness contract governing how announcements reach the platform
- [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) — the owner of observations, including any read-time price adjustment that presentation requires
- [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) — the boundaries whose ledgers receive the attributed consequences
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the append-only and classification-honesty precedents this domain extends to structural events
