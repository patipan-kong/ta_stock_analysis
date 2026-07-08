# Transaction Domain Model

*The canonical transaction is the platform's permanent memory: the immutable business event from which all accounting, replay, performance, tax, and AI evaluation are derived. This document defines what a Transaction **means** — what it owns, what vocabulary it speaks, and why every historical portfolio state must be reproducible from canonical transactions alone.*

*This is not a database design, not an accounting implementation, and not an API specification. It is the innermost document of the handbook: everything before it explains how facts arrive at the ledger — [BROKER_ACCOUNT_DOMAIN.md](BROKER_ACCOUNT_DOMAIN.md) owns the doors and the import pipeline, [ASSET_REGISTRY.md](ASSET_REGISTRY.md) owns the identity every event references, [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) owns the boundary every event lands inside. This document defines the fact itself: the event as it exists once it has been admitted, forever.*

*Read together with [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) (§9, whose universal transaction concepts this document adopts and completes) and [../investment/PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) (the frozen semantics that consume what this domain records).*

---

## 1. Philosophy

The platform's entire accounting architecture rests on a four-layer distinction, and this domain is its foundation:

**Transactions are facts.** A transaction records that something *happened*: an asset was bought, cash arrived, a fee was charged. It records the event at the resolution the world delivered it — what, when, how much, at what terms, learned from where — and nothing more. Facts do not expire, do not improve with age, and do not change when the platform's opinions change.

**Snapshots are derived.** Any statement of portfolio state — holdings on a date, NAV at a close, cash on hand — is the *output* of replaying recorded facts. Snapshots exist for speed and inspection; they carry no authority of their own. The platform has proven this the hard way: its reconstruction machinery can delete every snapshot and rebuild them all from the ledger, and its audit tooling treats snapshot-versus-replay disagreement as a defect in the snapshot, never in the ledger (ADR-002: metrics never compensate for the ledger).

**Analytics are interpretations.** Returns, attribution, benchmark comparisons, and trust scores are *readings* of the facts under rules that legitimately evolve. When a calculation rule improves, history is re-interpreted — the facts beneath it never move. This is what makes it safe to improve analytics forever: interpretation is versioned opinion; the ledger is not.

**Replay reconstructs history.** The bridge between facts and everything else is deterministic replay: the same ledger under the same rules produces the same state, every time, on any machine, in any year (ADR-001: the transaction ledger is the single source of truth). Every historical portfolio state — not just the current one — must be reproducible solely from canonical transactions, because any state that cannot be replayed is a state the platform is merely asserting.

From these four layers follows the domain's one absolute rule: **a transaction is never edited.** When the platform learns something new — a broker restates a dividend, a fee was missed, an event was misclassified — the new knowledge enters as a *new event*, explicit and provenance-tagged. The original record was not wrong to exist; it faithfully recorded what was then known. A ledger whose past can be rewritten is not a memory; it is a whiteboard.

---

## 2. Responsibilities

### What a Transaction owns

- **The business event** — what economically happened, expressed in the canonical vocabulary (§3). One event, one record; a real-world action with several economic effects (a purchase and its fee and its withholding) is a small set of explicitly linked events, never a blur.
- **Two timestamps, two meanings** — *when it happened* (the transaction date, which governs where the event lands in replay) and *when the platform learned it* (the recording date, which governs audit and window membership). The distinction is already settled law (ADR-003) and is what makes backfills honest: a 2022 trade imported in 2027 replays in 2022 and confesses its late arrival in provenance.
- **Asset reference** — the permanent `asset_id`, and only that (§6).
- **Portfolio reference** — the one portfolio whose ledger this event belongs to (§5).
- **Quantity** — the signed change in units held, in the asset's own quantity conventions (shares, weight, fractional units — facts the Registry describes).
- **Cash movement** — the signed cash consequence, in the currency it actually moved in (§7).
- **Execution terms** — the price *as executed*: the actual terms of the actual event, including their divergence from any market observation. Execution price is a historical fact owned here; market price is an observation owned by the Market Data Platform. They are different numbers with different owners, and their difference (slippage, spread, dealer margin) is real information precisely because the two are never conflated.
- **Settlement facts** — when and in what currency the event actually settled, as distinct from when it was struck (the settlement-versus-trade distinction the platform learned from a documented settlement-price incident).
- **Classification** — the truthful typing of the event (§3): income or capital, boundary flow or internal movement, performance-bearing or excluded. Classification is a *fact about the event* recorded once at admission; what a classification *implies* for returns is owned by the calculation rules and applied at read time.
- **Provenance** — where this fact came from: which door, which broker account, which import batch, which original claim (BROKER_ACCOUNT_DOMAIN.md §5). Provenance makes every ledger line auditable back to its source and is permanently load-free: replay never reads it (§8).

### What a Transaction never owns

- **Current price or valuation.** A transaction knows what was paid, never what the position is worth now. Valuation is replayed quantity multiplied by canonical observation — computed, not stored on the event.
- **Portfolio state.** No running balances, no cumulative positions, no "holdings after this trade." State is replay's product; an event that carries state invites the circularity §8 forbids.
- **Analytics.** No returns, no P/L opinions, no attribution. An event that stores its own performance meaning freezes an interpretation into a fact.
- **Risk, signals, recommendations.** The decision-intelligence layers read the ledger; nothing they produce is written back into it. A recommendation that led to a trade is linked *from* the decision record *to* the transaction — the transaction itself remains innocent of why it happened.
- **Asset metadata.** Names, sectors, capabilities, and lifecycle status belong to the Registry. The event holds the reference; the Registry holds the description.

The test for any proposed field: *would two people who agree on what happened necessarily agree on this value?* If yes, it is a fact and may live on the transaction. If it depends on rules, models, or the present moment, it is an interpretation and lives downstream.

---

## 3. Canonical Transaction Types

The platform records events in one closed, platform-owned vocabulary. UNIVERSAL_ASSET_ARCHITECTURE.md §9 established the universal concepts and their three-way grouping (changes in quantity held; cash flows generated by holding; costs and adjustments layered on either). This section completes that vocabulary into the full canonical families and states what each *conceptually owns*. No enumeration here is a schema; the names are vocabulary, not fields.

**Acquisition and disposal — BUY, SELL.** Economic exchange: quantity changes *and* cash moves, in opposite directions, inside the portfolio boundary. These are the only events that establish or realize cost basis, which is why their execution terms must be facts, not estimates.

**Position movement — TRANSFER_IN, TRANSFER_OUT.** Quantity changes *without* economic exchange: an in-kind move between custodians, a position entering the platform's tracking. No sale occurred, no basis reset, no performance event — the classification-honesty rule BROKER_ACCOUNT_DOMAIN.md §8 already defends against the sell-and-rebuy lie. A transfer that crosses a portfolio boundary is mirrored on both ledgers; one that merely changes custody location within a portfolio is provenance detail on a single pair of events.

**Holding income — DIVIDEND, INTEREST.** Cash generated *by holding*: performance-bearing inflows attributable to a position. The family is deliberately open along the axis §9 of the asset document drew — rent, staking yield, coupons, and fund distributions are the same shape awaiting their asset classes (§10).

**Costs and levies — FEE, TAX.** Cash consumed *in connection with* events or holdings. They are distinct concepts (already true in the platform's fee-decomposition rules): a fee is a service cost; a tax is a levy. Both may attach to a parent event or stand alone, and keeping them explicit rather than netted is what makes honest cost analysis — and any future tax engine (§11) — possible at all.

**Boundary flows — DEPOSIT, WITHDRAWAL.** Cash crossing the portfolio boundary from or to the outside world. These are the events the platform's accounting-correctness era was fought over: they are real, they are recorded, and they are *excluded from performance* by classification — because money arriving is not skill (the cash-flow-adjusted-returns and imported-position-stripping lessons, both in the decision log). The boundary, not the motion of money, decides what is a flow (BROKER_ACCOUNT_DOMAIN.md §4).

**Currency exchange — FX_CONVERSION.** Real money actually exchanged between currencies, at the true executed rate with its true costs. A ledger event; never to be confused with read-time translation, which is an opinion and is never stored (BROKER_ACCOUNT_DOMAIN.md §7).

**Structural events — the CORPORATE_ACTION family: SPLIT, MERGER, SPINOFF, RIGHTS, OPTION_EXERCISE.** Events where position structure changes *without ordinary user intent*: quantities rescale, one identity becomes another, a new position is born from an old one, an entitlement converts into a holding. These events are unique in touching both of the platform's permanent authorities at once — the ledger (quantities, cash-in-lieu) and the Registry (identity relationships, ASSET_REGISTRY.md §7) — which is why they enter as claims for adjudication, never as auto-applied facts (BROKER_ACCOUNT_DOMAIN.md §5), and why they are reserved as a future domain of their own (§11).

Three properties hold across all families:

- **Types classify by economic effect, never by source or asset class.** There is no "Thai dividend" and no "the kind of buy that came from broker X" — the door is provenance, never semantics.
- **A type is a claim about effects in fixed dimensions**: did quantity change? did cash move? did the movement cross the boundary? is the cash income or capital? did identity structure change? Every family above is a distinct answer-pattern to those questions — which is exactly what makes the vocabulary extensible (§10): a new type is a new answer-pattern, not a new question.
- **The vocabulary is closed and platform-owned.** Doors translate into it; nothing translates out of it. Admitting a source-specific type would fork the ledger's meaning by vendor — the exact failure the canonical model exists to prevent.

---

## 4. Event Model

The ledger is an **append-only stream of business events**, and four consequences follow:

**Business events never disappear.** Delisting an asset, closing a portfolio, ending a broker relationship, even discovering that an event was recorded in error — none of these removes a ledger line. Closed is never deleted, anywhere in this platform; the ledger is where that rule is load-bearing rather than aesthetic, because every derived state in the system rests on the stream being complete.

**Corrections append.** New knowledge about old events enters as new events: an explicit, signed adjustment; a reversal paired with a corrected re-statement; a provenance-tagged restatement from a broker. The platform has built this discipline twice already — signed manual adjustments for cash, and the repair-overlay machinery that lets replay honor a documented correction *without one recorded row ever changing*. Both are instances of the same law: the ledger records everything the platform has ever believed, in the order it came to believe it, and later beliefs supersede without erasing.

**The stream carries two timelines.** Event time (when it happened) orders replay; knowledge time (when it was learned) orders audit. Because both are permanent facts on every event, the platform can answer two different honest questions about any date: *what was true then?* and *what did we believe then?* The gap between those answers — the backfilled trade, the late correction — is not an embarrassment to hide but a fact the AI-evaluation layer legitimately needs, since a model can only be judged on what was knowable at decision time.

**Replay always consumes the entire stream.** There is no "replay since the last snapshot" as a source of truth, no checkpoint that events before it may be forgotten, and no event too old to matter. Snapshots may accelerate; only the full stream *authorizes*. This is the property that makes the ledger a permanent memory rather than a rolling buffer — and it is why admission standards (§9) matter so much: everything admitted is consumed forever.

---

## 5. Relationship with Portfolio

**Every transaction belongs to exactly one Portfolio.** This is the ledger rule on which the whole boundary architecture stands (PORTFOLIO_DOMAIN_MODEL.md §2). Attribution is decided per event at admission — trivially where an account serves one portfolio, by durable rule or the owner's confirmed word where it serves several (BROKER_ACCOUNT_DOMAIN.md §3) — and once recorded, it is a fact like any other.

**The Portfolio owns accounting; the transaction is its atom.** The portfolio's boundary decides which flows are external, its base currency decides the reporting frame, its policy decides what validation tolerates — and all of these operate *on* transactions without living *in* them. The event records what happened; the portfolio's rules decide what it adds up to.

**The broker supplies evidence, never entries.** No broker statement, API payload, or file row is a ledger event. Claims become transactions only by surviving the admission pipeline — resolution, classification, validation, attribution — and what the ledger then holds is the platform's own record, in the platform's own vocabulary, with the broker preserved as provenance (BROKER_ACCOUNT_DOMAIN.md §5–6).

**Transactions never migrate between portfolios.** A recorded event's portfolio attribution is permanent — because the moment events can move, both ledgers' histories silently rewrite: replayed states change retroactively on two boundaries at once, and every snapshot, return, and evaluation derived from either becomes unverifiable. When an attribution is discovered to be *wrong*, the correction follows §4: explicit reversing events on the wrong ledger, explicit re-statements on the right one, all dated by knowledge time, all provenance-linked to the mistake they repair. Both portfolios' histories then tell the truth — including the truth that a mistake was made and fixed. A migration hides the mistake; a correction records it. This platform always chooses the record.

---

## 6. Relationship with Asset Registry

**Transactions reference `asset_id` — never symbols, never provider identifiers.** The ledger is forever; names are not; therefore the ledger may never be keyed by a name (ASSET_REGISTRY.md §1). Every ticker change, provider migration, and broker spelling quirk in the platform's future will leave the ledger untouched because the ledger never knew those names existed.

**Identity is resolved before entry.** Resolution is a completed precondition of admission, not a step replay performs later: a claim whose symbol has not yet been adjudicated into an `asset_id` waits in quarantine (§9), visibly, and no ledger event is written for it. This ordering is what lets the Registry's whole adjudication machinery — evidence hierarchies, ambiguity surfacing, never-guess verdicts (ASSET_REGISTRY.md §4) — happen where mistakes are still cheap. The one place an identity error must never reach is the one place events are permanent.

**The division of labor is total.** The Registry answers *what this thing is* — including what it used to be called, what it merged into, and what wraps what. The ledger answers *what happened to it* — quantities, cash, terms, dates. A corporate rename touches the Registry's evidence file and zero ledger rows; replay of a decade-old trade in a since-renamed, since-merged asset works because the `asset_id` it references is permanent and the Registry still answers for it (ASSET_REGISTRY.md §10). Neither authority ever answers the other's question.

---

## 7. Cash Model

Cash is the dimension every transaction family touches, so its ownership must be exact:

- **Cash movements are effects of events, not events beside them.** A BUY moves cash out as the same fact that moves quantity in — one event, two effects, never a separate "cash leg" invented to balance books. Only genuinely cash-native events (deposits, withdrawals, FX conversions, standalone fees) are cash-first facts.
- **Settlement is timing on the fact, not a second fact.** When cash actually moved, and in which currency it actually settled, are recorded terms of the event (§2). Unsettled proceeds are a *state* of a recorded event, never separate money (BROKER_ACCOUNT_DOMAIN.md §4) — and no settlement convention ever invents a transaction.
- **Fees and taxes stay decomposed.** A purchase's all-in cost is the sum of explicit parts — execution, fee components, levies — not a single blended number. Blending is irreversible: once netted, the parts can never be recovered for cost analysis, tax treatment, or honesty about what the broker actually charged. The ledger records parts; reports may sum them.
- **FX has three shapes, one of which is a transaction.** Conversion (real exchange at true terms) is a ledger event. Rates are canonical observations owned by the Market Data Platform. Translation is read-time arithmetic, never stored. The full doctrine is BROKER_ACCOUNT_DOMAIN.md §7's; the ledger's share of it is simple: record what actually moved, in the currency it actually moved in.
- **Income and capital are different kinds of cash, and the difference is sacred.** Income (dividends, interest, and their future siblings) is cash the portfolio *earned* — performance-bearing. Capital movements (deposits, withdrawals, transfer flows) are cash the portfolio was *given or relieved of* — performance-excluded. Every accounting incident in the platform's history that genuinely hurt — phantom deposits, imported positions inflating returns, external flows contaminating daily performance — was this one distinction recorded falsely. The classification is made once, truthfully, at admission (§2); the exclusion arithmetic it drives is owned by the calculation rules.

Ownership summary: the **event** owns what moved and when; the **classification** owns what kind of movement it was; the **portfolio's rules** own what it means for performance; the **Market Data Platform** owns what any of it is worth in another currency. Four owners, no overlaps — any cash question that seems to need two of them at once is two questions.

---

## 8. Replay Relationship

The Replay Engine is the accounting authority, and its inputs are deliberately, permanently minimal — three things, and nothing else:

- **Transactions** — the canonical stream, complete, in event-time order (ADR-003).
- **Portfolio rules** — the boundary, base currency, and frozen calculation semantics that give the stream its accounting meaning.
- **Corporate action facts** — the adjudicated structural events (§3) that rescale quantities and connect identities, already admitted to the stream through their own disciplined door.

And three things replay must *never* consume:

- **Never snapshots.** Snapshots are replay's outputs. A replay that reads its own outputs is circular: errors freeze into inputs, and the ledger quietly stops being the source of truth. Snapshots accelerate reads and enable audits (the platform's snapshot-verification tooling exists precisely to check them *against* replay) — they never feed the computation that defines truth.
- **Never current holdings.** Holdings are a snapshot by another name — the most tempting one, because it is always at hand. The platform's reconstruction engine proves the discipline: state is rebuildable from the ledger alone, therefore state is never an input.
- **Never broker statements.** Brokers are witnesses (BROKER_ACCOUNT_DOMAIN.md §10). Their statements reconcile *against* replayed truth through a read-only back-channel; the moment an external balance can enter replay, the platform has outsourced its memory to an institution that can restate, err, or vanish.

The payoff of this austerity is the platform's deepest guarantee: **the same ledger under the same rules yields the same history, forever** — on any machine, after any migration, after every broker and provider involved has ceased to exist. Determinism is not an optimization; it is what makes the ledger's permanence *worth* anything, because a permanent record that cannot be deterministically re-read is just a permanent mystery.

*(How replay computes is an implementation concern and lives outside this document; what it may depend on is architecture, and it lives here.)*

---

## 9. Idempotency

The ledger is append-only and consumed forever (§4), so the platform's entire defense against a corrupted memory is **admission discipline plus standing audit** — prevention where it is cheap, detection where it is honest, and never silent repair.

- **Duplicate and repeated imports** converge on the same ledger. Each incoming claim is recognized by content identity — the fingerprint concept the platform already trusts enough that duplicate-fingerprint findings are among the very few things permitted auto-repair — and recognition happens *at the boundary*, before recording, because prevention is the only cheap correction an immutable ledger allows. The import-side mechanics are BROKER_ACCOUNT_DOMAIN.md §6's; the ledger-side consequence is stated here: re-running any import, re-fetching any span, re-processing any file is a safe, boring operation that cannot mint a second copy of a recorded fact.
- **Corrections** are appended events (§4), never edits — which means idempotency applies to corrections too: the same restatement learned twice is recognized as already-applied, not applied twice.
- **Historical backfills** are ordinary admissions riding the two-timeline rule (ADR-003): they land in event time, confess in knowledge time, and trigger honest recomputation of everything derived downstream of their event date. A backfill is never a special mode with weaker checks; late facts pass the same admission bar as fresh ones.
- **Ledger validation** is the standing audit: a read-only discipline that sweeps the recorded stream for structural dishonesty — duplicates that slipped the boundary, impossible sequences, orphaned references, classification contradictions — and reports findings by severity without ever writing a fix. Repair is a separate, explicit, human-authorized act, executed through the platform's overlay-and-append machinery so that even repairs leave the recorded rows untouched. Detect loudly, repair explicitly, never auto-correct what is load-bearing — the platform-wide law, applied to its most load-bearing structure.
- **Quarantine** is where admission standards live with claims that cannot yet meet them: unresolved identity, undecidable attribution, contradictory terms. A quarantined claim is visible, waiting, and *outside the ledger* — invisible to replay, excluded from every derived state — until it can be recorded honestly or rejected explicitly. Quarantine exists because the alternative is guessing, and a guess admitted to an immutable, forever-consumed stream is the most expensive guess the platform can make.

Beneath all five: **transaction immutability is what makes trust in the ledger transitive.** Because recorded events cannot change, verifying admission once verifies it forever; every snapshot, return, and evaluation derived from the ledger inherits the ledger's integrity without re-checking it. Mutability anywhere would break the chain everywhere — which is why immutability is not a storage preference but the domain's founding axiom.

---

## 10. Future Transaction Types

The vocabulary will grow with the asset classes. It will grow **by classification into the existing families, never by redesign** — because replay consumes effects (quantity deltas, cash deltas, boundary crossings, income/capital classification, structural changes), not type names (§3). Each anticipated arrival already has a home:

- **Crypto staking rewards** — holding income: cash (or in-kind units — an income event whose payout is quantity, a shape the family already implies) generated by holding. The income family's fourth sibling, exactly as UNIVERSAL_ASSET_ARCHITECTURE.md §9 anticipated.
- **Bond coupons** — holding income, on a schedule the asset's capabilities describe. INTEREST wearing its fixed-income name.
- **Property rental income** — holding income from an asset with no exchange, no ticker, and no provider — and the ledger cannot tell the difference, which is the whole point.
- **Private equity capital calls** — a staged acquisition: each call is an acquisition event at its own date and terms, honoring a commitment the portfolio's policy tracks. Composite behavior lives in the pattern of ordinary events, not in a new exotic one.
- **Fund distributions** — holding income, with a classification nuance the family already carries: the income-versus-return-of-capital line (§7) decides whether a given distribution is earnings or a capital adjustment, and honest classification at admission — not a new type — is what keeps performance truthful.
- **Loan repayments** — a composite of two existing facts: a capital movement (principal) and holding income (interest), recorded as the decomposed parts they are, in the fee-and-tax tradition of never blending what analysis will later need separated.
- **Derivative settlements** — structural family: a position resolving into cash or into another position (physical delivery), the OPTION_EXERCISE shape generalized. The Registry's identity coordinates for derivatives (ASSET_REGISTRY.md §11) answer *what*; the settlement event answers *what happened*.

The test for every future arrival is the one §3 established: state the new event's answers to the fixed questions — quantity? cash? boundary? income or capital? structure? If the answers fit the existing patterns, it is vocabulary, and vocabulary is cheap. If a genuinely new *answer-pattern* ever appears, that is an architecture conversation — and the honest expectation, after surveying asset classes from Thai equities to rental property, is that the patterns above are complete. **Expansion adds vocabulary, never surgery.**

---

## 11. Relationship to Future Domains

The planned domains of the handbook (README §6) will each stand on this one. None will require it to change — that is the claim this section makes precise, without designing any of them:

- **Corporate Actions** will own the *adjudication* of structural events — interpreting the world's announcements, resolving their identity consequences with the Registry, proposing their ledger consequences for confirmation. What it delivers to this domain is what §3 already reserved: admitted structural events in the canonical stream. The ledger's role is unchanged: record what was adjudicated, forever.
- **The Tax Engine** will be a *reader*. Everything a jurisdiction-aware tax computation needs — true execution terms, decomposed fees and levies, settlement dates and currencies, holding periods derivable by replay, honest income-versus-capital classification — is already a recorded fact or a replay derivation. Tax opinions (liabilities, lot selections, wrapper treatments) are interpretations and live downstream; the ledger never stores a tax opinion, only the facts that make every future tax opinion computable.
- **Multi Currency** as a platform-wide treatment will elaborate the four-concept doctrine (BROKER_ACCOUNT_DOMAIN.md §7). The ledger's contribution is already fixed: settlement currency as fact on every event, FX conversions as events, translation never stored. A richer FX domain refines reading, not recording.
- **Goal Planning** will connect portfolios to intent over time. Its factual substrate — contributions, withdrawals, the dated history of money crossing boundaries — is exactly the boundary-flow family, already truthfully classified. Goals interpret flows; they will never need new kinds of them.
- **The Risk Engine** will reason over exposures and scenarios. Exposures begin with positions, positions are replay derivations, and replay stands on this domain. Risk adds models on top of derived state; it touches no fact.
- **The Wealth Domain** will describe across portfolio boundaries — net worth, household views, allocation in aggregate. It reads many ledgers and judges none (the describe-side of PORTFOLIO_DOMAIN_MODEL.md §10's line), which makes it the purest consumer of all: interpretation over facts it has no power to create.

The pattern across all six: **the ledger supplies facts; each domain supplies an interpretation; interpretations stack without touching the facts beneath them.** That is not a coincidence of these six domains — it is the reason the transaction domain was placed at the bottom of the stack.

---

## 12. Design Principles

1. **Transactions are immutable.** Recorded once, edited never; the founding axiom from which every other guarantee derives.
2. **Business events are append-only.** New knowledge — corrections, restatements, repairs — enters as new events; history records even its own mistakes.
3. **Replay derives truth.** All portfolio state, past and present, is reproducible from canonical transactions under portfolio rules — deterministically, forever.
4. **Snapshots are caches; analytics are interpretations.** Neither carries authority; both are rebuildable; disagreement with replay always indicts the derived layer.
5. **Every transaction belongs to exactly one portfolio, permanently.** Attribution errors are corrected by appended, mirrored events — never by migration.
6. **Transactions reference `asset_id`, never names.** Identity is resolved before admission; the ledger never learns what anything is called.
7. **Types classify by economic effect.** Never by source, never by asset class, never by vendor — the door is provenance, and provenance is load-free.
8. **Income and capital are never confused.** The classification is made truthfully at admission; every hard accounting lesson in the platform's history is this principle, learned once each way.
9. **Two timelines, both permanent.** Event time orders replay; knowledge time orders audit; the gap between them is honest information, not noise.
10. **Admission is the last cheap moment.** Resolution, classification, attribution, and deduplication complete before recording; what cannot yet be recorded honestly waits in quarantine, visibly.
11. **Validation detects; repair is explicit; nothing self-corrects.** The audit reads, the human authorizes, and even repairs leave recorded rows untouched.
12. **Canonical transactions are the platform's permanent memory.** Portfolios give them a boundary, the Registry gives them identity, brokers give them provenance, replay gives them meaning — and the events themselves outlive all four conversations.

---

## Related Documents

- [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) — the accounting boundary every transaction lands inside
- [BROKER_ACCOUNT_DOMAIN.md](BROKER_ACCOUNT_DOMAIN.md) — the doors and admission pipeline through which claims become the events defined here
- [ASSET_REGISTRY.md](ASSET_REGISTRY.md) — the identity authority whose `asset_id` is the only name the ledger ever holds
- [UNIVERSAL_ASSET_ARCHITECTURE.md](UNIVERSAL_ASSET_ARCHITECTURE.md) — §9's universal transaction concepts, which this document completes into the canonical vocabulary
- [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) — the owner of observations, rates, and everything a transaction's execution terms are *not*
- [../investment/PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) — the frozen semantics that interpret what this domain records
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — ADR-001/002/003 and the accounting-correctness lessons this domain generalizes into law
