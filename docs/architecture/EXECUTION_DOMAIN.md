# Execution Domain

*Execution is the moment investment intent becomes immutable portfolio history: recommendations express ideas, humans make decisions, and execution produces canonical transactions. This document defines what Execution means inside the platform — the bridge between intelligence and accounting, owned by neither.*

*This is not an order management system, not broker integration, and not trade routing. It is the handbook's second adjudication domain, the deliberate sibling of [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md): that domain adjudicates the **world's** events into the ledger; this one adjudicates the **user's own intentions** into it. Both stand between claims and permanent records; both own a process rather than the records the process feeds.*

*One question deserves settling before anything else: is Execution truly a domain, or merely an application workflow? The handbook's own test decides it — a domain must own a permanent record or a load-bearing boundary that no other domain can own. Execution owns both. The record: the platform's **decision history** — what was recommended, what the human decided, what was actually done, and crucially what was *never* done — which is not the ledger's to keep (the ledger records economic facts, not judgment) and not the intelligence layer's to keep (advice is not decision). The boundary: the one gate through which intent is allowed to become money movement. Without this domain, decisions scatter into UI state, inferred ledger diffs, and recommendation-store annotations — unauditable, ungradeable, and unrecoverable. The platform's entire evaluation promise — judging AI against human, calibrating trust, tracking the counterfactual — stands on this record existing as a first-class, append-only structure. Execution is a domain; what it is **not** is an order engine, and this document is careful to define it as the former without drifting into the latter.*

---

## 1. Philosophy

### Ideas are not facts

The platform's intelligence layers produce ideas continuously: signals, allocations, sizing, timing. Ideas are cheap by design — the optimizer may propose daily, and most proposals should die unexecuted without ceremony. A fact, by contrast, is forever: once a transaction enters the ledger, every snapshot, return, and evaluation downstream inherits it permanently (TRANSACTION_DOMAIN_MODEL.md §1). Between the cheap and the permanent stands exactly one thing — a **decision** — and the Execution Domain exists because decisions deserve the same architectural seriousness as the facts they create.

### Execution is the moment an intention becomes reality

Everything upstream of execution is reversible: a recommendation can be regenerated, a review can be reconsidered, an approval can be withdrawn. Everything downstream is immutable: transactions recorded, history replayed, performance attributed. Execution is the one-way door between those regimes — the same door-shape the handbook has drawn twice before (the Registry's minting moment, the corporate-action lifecycle's Approval), here at its highest stakes, because this is the only door through which the *user's own money moves on the platform's word*. All the care in this document concentrates at that door.

### Two ledgers, two kinds of fact

The deep insight of this domain is that judgment produces facts too. "The human rejected this recommendation on this date, for this stated reason" is as immutable a fact as any purchase — it happened, it cannot un-happen, and the platform's evaluation machinery depends on it being remembered exactly. The platform therefore keeps two permanent records: the **transaction ledger** remembers what happened to money; the **decision record** remembers what was intended, chosen, declined, and left to expire. They are equally append-only, equally two-timelined, and equally beyond editing — but only one of them participates in accounting. Only executed decisions become part of portfolio history; *every* decision becomes part of decision history. A rejected recommendation leaves zero trace in any ledger and a permanent trace in the decision record — which is precisely what lets the platform later ask the question no ordinary tracker can: *what would have happened if the human had listened?*

---

## 2. Responsibilities

### What the Execution Domain owns

- **Execution intent** — what was actually decided to be done: instrument, direction, size, conditions. Intent is distinct from the recommendation that inspired it (the human may resize, retime, or redirect) and distinct from the outcome that follows it (reality may deliver less, later, or at different terms). Intent is the middle term, and this domain is its only home.
- **The decision lifecycle** — the full state history of every intent from advisory origin to terminal outcome (§3), recorded as append-only transitions with both timelines: when each state was entered, and what was known at the time.
- **Approval state** — whose judgment authorized what, when, under which then-active policy envelope. Approval is a recorded act by an accountable party, never an inferred or defaulted condition.
- **Execution status** — the honest, current answer to "what has reality delivered against this intent?": requested, partially executed, completed, cancelled, expired — a summary *derived from ledger evidence* (§7), never a parallel accounting.
- **Human confirmation records** — the explicit record of every human act in the process: approvals, rejections, overrides with their classified reasons, manual edits with both sets of numbers, deferrals (§5).
- **AI recommendation linkage** — the durable references binding each decision to the recommendation(s) it responded to and to the transaction(s) it eventually produced. This linkage is the attribution spine of the platform: recommendation → decision → transactions is the three-strand braid every human-versus-AI question is answered from.
- **Execution metadata** — the context that makes later judgment fair: what prices were observed at decision time, what constraints were active, what the portfolio's replayed state was. Evaluation must grade decisions on what was *knowable*, and this domain is where knowability is preserved.

### What the Execution Domain never owns

- **Portfolio accounting.** No balances, no positions, no NAV. The domain checks intent against replayed truth (§9); it never maintains a competing version of it.
- **Asset identity.** Intents reference `asset_id` like everything else; the Registry answers for what things are, including whether they are still executable (§9).
- **Market prices.** Observed prices in execution metadata are snapshots *from* the Market Data Platform, recorded for fairness; the domain never sources, adjusts, or asserts a price.
- **Performance.** How an executed (or unexecuted) decision worked out is an interpretation computed downstream by analytics and evaluation. The decision record holds no verdicts about itself.
- **Replay.** The accounting authority consumes transactions and remains permanently innocent of intentions (§7).
- **The recommendation itself.** What the AI said, with what reasoning and confidence, belongs to the intelligence layer's own record — frozen there, referenced from here, edited by no one (§4).

The compressed statement: **this domain owns the question "what did we decide, and what became of the decision?" — and none of the truths the decision was about.**

---

## 3. Execution Lifecycle

The lifecycle is a set of recorded states with one irreversible threshold. Each state exists because collapsing it into a neighbor destroys information the platform is committed to keeping:

**Recommendation.** An idea exists; no decision does. This state exists to keep the advisory world honestly separate: a recommendation is not "pending" anything — most recommendations should live and die without ever engaging the lifecycle, and their non-engagement is itself recorded knowledge (§4).

**Pending Review.** A recommendation (or a human's own idea — the intelligence layer is not the only door into the lifecycle) has been taken up for decision. This state exists because human attention is the scarce input: what is awaiting judgment must be visible, aging must be measurable, and nothing may drift from "awaiting decision" to "decided" without a recorded act.

**Approved / Rejected.** The two decision verdicts, and they are architectural equals: a rejection is exactly as permanent, exactly as attributable, and — to the evaluation layer — exactly as valuable as an approval. Rejected is a terminal state that exists so that "the human said no" is a durable fact with a date and a reason, not an absence. Approval, by contrast, is not terminal: it is authorization, the last reversible moment.

**Execution Requested.** The intent has been committed toward reality — instructions issued, the world engaged. This state exists because it marks the irreversibility threshold: before it, withdrawal is free; after it, the world may already have acted, and every subsequent change is reconciliation with reality rather than revision of intent.

**Partially Executed.** Reality has delivered some of the intent. A true state, not an error: markets fill orders in pieces, sessions close, liquidity runs out. The state exists so the gap between intent and reality is a visible, first-class condition — the platform already treats partial execution as a distinct decision outcome in its attribution machinery, precisely because "did some of it" grades differently than "did it" or "didn't."

**Completed.** Ledger evidence accounts for the full intent. Terminal.

**Cancelled.** The human withdrew intent — before the threshold, freely; after it, as an instruction to stop that reconciles against whatever reality already did (a cancel after partial fill terminates the *remainder*; what executed stays executed and stays recorded). The state exists because withdrawn intent is a judgment fact: "we decided to, then decided not to" is information, not noise.

**Expired.** Time invalidated the premise before a decision or completion occurred. This state exists as the honest third verdict: an expired recommendation was neither accepted nor rejected — the human never engaged it, or the window closed mid-flight — and evaluation must never count silence as either agreement or refusal. Expiry is how the lifecycle decays gracefully instead of accumulating zombie intents that a later reader mistakes for live ones.

Every transition is appended, dated in both timelines, and attributed to an actor — human, policy, or the passage of time. The lifecycle never loses a state it passed through: the record is the *path*, not the endpoint.

---

## 4. Relationship with Recommendations

**Recommendations are advisory; execution is authoritative.** The intelligence layer proposes with reasoning and confidence; it never acts, schedules, or nags an action into being. Authority to change the world enters exactly once, at the decision — and the decision belongs to this domain, made by a human or by a policy a human explicitly authorized.

**Many recommendations never execute — by design, and the platform keeps them all.** An advisory layer that expected execution would be an execution layer with extra steps. Unexecuted recommendations are not waste; they are half of the platform's most valuable dataset. The counterfactual question — what the AI's advice would have produced had it been followed — is answerable only because declined and ignored advice is preserved with the same fidelity as accepted advice. The platform's shadow-tracking machinery is this principle in production: the model's suggested portfolio accumulates its own track record regardless of what the human executed.

**Execution preserves the relationship without changing recommendation history.** What the AI recommended — terms, reasoning, confidence, timestamp — is frozen at the moment of recommendation, forever. No approval improves it, no rejection annotates it, no outcome revises it retroactively. The linkage runs *from* the decision record *to* the frozen recommendation, never as edits upon it — because calibration is measured against what the model actually said at the time, and a recommendation store that can be touched after the fact is a calibration instrument that can be bent.

**The decision may diverge from the recommendation, and divergence is first-class.** The human who approves at half the suggested size, or substitutes a different funding source, or acts a week later has neither accepted nor rejected the advice — they have *overridden* it, and the platform records the override as its own classified fact: what kind of divergence, the human's terms beside the AI's terms, the stated reason. The platform's structured-override machinery exists exactly here, and it is what elevates human-versus-AI comparison from a binary scoreboard into an honest account of *where* human judgment adds or subtracts value.

---

## 5. Relationship with Humans

The Execution Domain is where the platform's oldest commitment — *the human owns the ledger* — becomes operational. Every path from idea to money passes through a recorded human act (or a standing policy a human explicitly, revocably granted), and the record captures judgment in all its forms:

- **Approvals** — the affirmative act, attributed and dated, with the context that was on screen when it was made.
- **Overrides** — divergence from advice, classified by kind and reasoned in the human's own words (§4).
- **Manual edits** — the human's numbers recorded beside the machine's numbers, so that later analysis can ask which set was wiser — a question that is unanswerable the moment an edit silently replaces what it edited.
- **Rejections** — explicit refusals with their reasons, terminal and permanent (§3).
- **Deferred decisions** — "not now" recorded as itself: neither yes nor no, visible in the pending queue, aging honestly toward expiry rather than lingering as ambient guilt or vanishing as if never asked.

Why human judgment remains *explicit* — recorded act by recorded act — rather than smoothed into defaults: three architectural reasons, each already load-bearing elsewhere in the platform. **Accountability**: money moves on someone's word, and the record must always answer *whose*. **Attribution**: the human-versus-AI ledger is meaningless if the platform cannot distinguish "the human chose this" from "the system assumed this" — a silent default poisons the comparison in whichever direction it leans. **Evaluation integrity**: the AI's calibration is measured against genuine human responses; auto-approved advice would let the model grade its own homework. The pattern is the platform's universal one — resolve silently only what is decisive, surface what is ambiguous, never guess — with the observation that where money moves, almost nothing is decisive enough to resolve silently without a human having pre-authorized exactly that class of silence.

---

## 6. Relationship with Broker Accounts

Execution faces the broker domain across a clean seam: **intent flows out as instructions; evidence flows back as claims; neither side ever writes the other's record.**

- **Execution produces broker instructions.** An approved intent becomes an instruction to a custody venue — which account, per the portfolio's funding and attribution realities (BROKER_ACCOUNT_DOMAIN.md §3). What an "instruction" physically is — an API order, a generated checklist the user carries to their broker's app, a phone call — is edge machinery below this domain's horizon. The platform's present reality, where the human executes manually at the broker, is not a degenerate case but the proof case: the architecture is identical whether the instruction travels by wire or by hand, because the door is provenance, never semantics.
- **The broker confirms execution — as a witness.** Fills, confirmations, and statements return through the ordinary import doors and the ordinary admission pipeline (BROKER_ACCOUNT_DOMAIN.md §5). Broker evidence is how execution status *learns* — it is never a privileged channel that writes status directly. A confirmation is a claim; claims are validated; validated claims become ledger events; and ledger events are what execution status summarizes (§7).
- **The broker never changes execution intent.** A fill at a different price, a smaller quantity, a rejection at the venue — all of these are *outcomes*, recorded as what reality delivered, beside an intent that continues to say what was wanted. The divergence between the two is not an inconvenience to reconcile away; it is the raw material of execution quality analysis (§11), and it exists as data only because intent and outcome are kept as separate records with separate owners.

The seam mirrors the reconciliation doctrine (BROKER_ACCOUNT_DOMAIN.md §10) from the other side: there, broker statements testify about the ledger's completeness; here, broker confirmations testify about an intent's fulfillment. In both, the broker may inform and may accuse — and may never overwrite.

---

## 7. Relationship with Transactions

**Execution never edits transactions.** Not to correct a fill, not to reverse a mistake, not to tidy a cancelled remainder. Whatever needs saying after the fact is said in the ledger's own append-only grammar (TRANSACTION_DOMAIN_MODEL.md §4), through the same admission pipeline as everything else.

**Successful execution creates canonical transactions — through the front door.** Execution-caused events hold no privileged path into the ledger: they are claims, resolved and attributed and validated and deduplicated like an imported statement row (BROKER_ACCOUNT_DOMAIN.md §5). This matters most where execution and import *overlap*: the platform may learn of a fill from its own instruction's confirmation *and* from next month's statement — one recorded fact, converged by content identity, not two. Execution provenance rides the event like any provenance: visible, auditable, load-free.

**Replay consumes transactions, never execution objects.** The Replay Engine's input contract (TRANSACTION_DOMAIN_MODEL.md §8) does not name this domain, and never will. Portfolio truth is deliberately independent of *why* trades happened: a portfolio replays identically whether its trades came from AI advice diligently followed, advice overridden, or a human acting entirely alone — because accounting that varied with intent would let opinions leak into arithmetic. The linkage points the safe direction only: the decision record references its resulting transactions; the transaction remains innocent of why it happened (TRANSACTION_DOMAIN_MODEL.md §2).

The closing consequence: **execution status is derived from ledger evidence, not asserted beside it.** An intent is Completed because admitted transactions account for it — never because an instruction was sent and hope was high. There is one source of truth about what happened, and even the domain that caused it to happen must read it there.

---

## 8. Partial Execution

Reality fills intents in fragments — partial fills, multiple fills across a session, an order split across venues or days, failures midway, retries after. The domain's treatment rests on one granularity rule: **facts are recorded at the granularity reality delivered them; intent remains whole at the granularity it was decided.**

- Each fill that actually happened is its own canonical transaction — its own quantity, price, time, and provenance — because that is what happened, and the ledger records what happened. Three fills are three events; blending them into one averaged pseudo-fill would manufacture a fact reality never produced, destroying (among other things) the per-fill terms that execution analytics and any future tax engine will need.
- The intent stays one object, and "partially executed" is its *status*: a decision-side summary of ledger reality measured against decided intent. It is never an accounting state — no ledger event is provisional, fractional-pending, or awaiting-completion. Every recorded fill is simply, fully true.
- **Execution failures** leave the record honest in both directions: whatever executed before the failure is recorded and permanent; whatever did not execute is visibly unfulfilled intent. There is nothing to roll back, because nothing false was ever written — the ledger contains only what happened, and the intent openly shows the shortfall.
- **Retries** are new instructions under the same intent, deduplicated at admission like everything else — a retry that turns out to have duplicated a fill the platform hadn't yet learned about converges on one recorded fact by content identity (BROKER_ACCOUNT_DOMAIN.md §6). The intent's history shows every attempt; the ledger shows only what the attempts actually produced.

This is why accounting remains deterministic through every partial-execution scenario without any special machinery: **replay never sees partiality.** It sees complete, immutable events — some intents simply produced fewer of them than were hoped for, and the hoping happened in a different domain. Partiality is a relationship between two records, and it lives in the record that owns relationships: this one.

---

## 9. Validation Philosophy

Execution validation is the platform's universal stance — check against truth, surface uncertainty, never guess — applied at the gate where guessing costs actual money. Every check below runs against *replayed* truth and *canonical* reference data, because the alternative to checking is discovering at the broker:

- **Price drift.** An intent is premised on the conditions at decision time, and conditions decay. An intent whose premise has drifted materially is not silently executed at the new reality, and not silently repriced — it is surfaced for reconfirmation, because the human approved a *decision*, not a direction, and the size of "material" is policy the portfolio's owner sets.
- **Expired recommendations.** Advice has a shelf life; an intent formed on stale advice inherits the staleness. Expiry (§3) is enforced at validation, not merely displayed — executing last month's recommendation *is* a new decision and must be made as one.
- **Insufficient cash.** Funding is checked against the portfolio's replayed cash — including settlement timing per the portfolio's own policy — before any instruction is issued. The platform's funding-source discipline (what sells to fund what buys, in what order) lives upstream in decision formation; validation is the final honest check that the plan still adds up when it is about to become real.
- **Insufficient quantity.** Selling what replay says the portfolio does not hold is refused loudly. If the human insists they hold it, the discrepancy is a *ledger completeness* problem — a missing import, an unrecorded transfer — to be repaired at the ledger through proper channels, never bypassed at execution. Executing around a wrong ledger buries the wrongness deeper.
- **Asset delisting.** The Registry's lifecycle status gates executability: intents referencing suspended, delisted, or merged identities are stopped and surfaced with the identity fact attached. Execution never argues with the Registry; it asks.
- **Corporate actions during execution.** The subtlest hazard: a split, merger, or spin-off effective between approval and execution changes the *meaning* of the approved terms — "100 shares at 50" describes a different world after a 2:1 split. Affected in-flight intents are interrupted and surfaced for reconfirmation against post-event reality; the platform never auto-rescales an intent, because rescaling human judgment is manufacturing consent. This is the one place the two adjudication domains touch operationally, and the corporate-action domain's recorded events (CORPORATE_ACTION_DOMAIN.md §6) are what make the interruption detectable at all.
- **Manual intervention.** The standing escalation path for everything validation cannot settle mechanically. As with corporate actions, the domain's duty is to arrive before the human with the case assembled — the intent, the check that failed, the truth it failed against — not with an error code.
- **Quarantine.** Intents that can neither proceed nor be honestly cancelled wait — visible, inert, excluded from any instruction flow — exactly as unadmittable claims wait at the import boundary. An intent in quarantine is a question the platform is refusing to answer by force.

The through-line: uncertainty at execution is handled by **stopping**, and stopping is cheap precisely because of where this domain sits — before the one-way door. Every ambiguity caught here is a conversation; the same ambiguity past the door is a correction event in a permanent ledger. The entire lifecycle (§3) is arranged so that doubt has somewhere honest to stand while it is resolved.

---

## 10. Future Expansion

The domain's invariants — intent recorded, judgment explicit, facts through admission, status derived from the ledger — are independent of how sophisticated intent formation or instruction handling becomes. Each anticipated evolution lands inside them:

- **Scheduled execution** — intent with a future activation: the lifecycle acquires a dormant period, and validation (§9) runs at activation against *then-current* truth, not at scheduling against today's. Nothing else changes; a scheduled intent is an ordinary intent that waits.
- **Recurring investments** — a standing intent generating dated instances, each an ordinary lifecycle citizen individually validated and individually recorded. The standing authorization is itself a recorded, revocable human act (§5) — recurrence automates the *instances*, never the *judgment* that authorized them.
- **Algorithmic execution** — working an instruction skillfully over time (slicing, pacing, venue choice) is edge machinery *below* the instruction seam (§6), exactly as adapters sit below the import seam. The domain records intent and consumes resulting fills; how artfully the space between was navigated is invisible to the decision record and measurable in execution analytics.
- **Tax-aware and goal-aware execution** — richer *advice* into decision formation: which lots to sell, which account to buy in, how an action serves a goal. These enrich the recommendation-and-context side of the lifecycle and leave the lifecycle itself untouched — better-informed intents, same door.
- **Multi-account execution** — one intent fulfilled across several custody venues: instructions fan out per the funding and attribution rules the broker domain already settled per-event (BROKER_ACCOUNT_DOMAIN.md §3), and the fills converge on the same intent's status. Fan-out is plumbing; the intent stays one decision.
- **Capacity-aware execution** — liquidity and market-impact constraints joining the validation set (§9) as one more check against one more kind of truth.
- **Institutional workflows** — more parties in the approval state: proposer, reviewer, approver as distinct recorded acts. The approval state grows richer; the one-way door stays singular; accountability stays attributable per act — the design already required for one human generalizes to N by addition, not redesign.

The pattern completing the handbook's refrain: expansion changes how intents are *formed* and how instructions are *worked* — the reversible edges. The middle — decision recorded, door passed once, facts admitted properly — is the stable part, and it is stable because nothing in this section touches it. **Vocabulary, never surgery.**

---

## 11. Relationship to Future Domains

- **AI Evaluation** — the primary customer, and the reason this domain's record-keeping is uncompromising. Every grade the evaluation layer produces is computed over this domain's braid: what was recommended (frozen), what was decided (attributed), what resulted (ledger-linked), what was knowable at each step (metadata). Completeness is the non-negotiable part — evaluation over only-executed decisions is survivorship bias with a dashboard, which is why rejections, expiries, and overrides are first-class records rather than absences.
- **Execution Analytics** — the study of the intent-versus-outcome gap this domain deliberately preserves: slippage against decision-time prices, cost of delay between approval and action, fill quality, the price of hesitation. Every one of those questions is a *difference between two records* — and both records exist only because §6 and §7 refused to let either overwrite the other.
- **Risk Engine** — execution is where risk gets its veto moment: pre-trade checks join the validation set (§9), reading proposed intent against replayed exposure before the door, where refusing is still free. Risk defines the constraints; this domain provides the gate they act at.
- **Tax Engine** — tax-aware execution (§10) consumes the tax domain's opinions as advice into decision formation; and in the other direction, this domain's fill-granular facts (§8) are what make lot-level tax reasoning possible at all. Advice in, facts out — never opinions stored as facts.
- **Goal Planning** — goals will express standing intent (contribute monthly, rebalance quarterly) and read progress from replayed truth. The recurring-intent machinery (§10) is the execution-side half of that conversation; the decision record is where "the plan said to, and the human did / didn't" becomes an answerable question.
- **Wealth Domain** — the describing layer sees execution only through its consequences in ledgers, as it should: a household's net worth has no opinion about workflow. What the wealth view may someday *describe* — pending intents across portfolios, capital committed but not yet moved — it will read from this domain's records without owning or altering them.

The inherited pattern, third time now: **this domain guarantees an honest record of judgment and its consequences; every future domain stacks interpretation on that record without touching it.**

---

## 12. Design Principles

1. **Execution records decisions; transactions record facts.** Two permanent records, two kinds of fact — volitional and economic — and neither is ever entrusted to the other.
2. **Recommendations remain advisory, forever.** No idea acts on its own authority; the intelligence layer proposes and is never edited by what happened next.
3. **Humans remain accountable.** Every path from idea to money passes through a recorded human act or a human's explicit, revocable standing authorization — and the record always answers *whose word*.
4. **The lifecycle has one irreversible threshold, and all care concentrates there.** Before Execution Requested, everything is reversible and cheap; after it, everything is reconciliation with reality.
5. **Every verdict is a record — including no.** Rejections, expiries, deferrals, and overrides are first-class, permanent, attributed facts; silence is never counted as agreement or refusal.
6. **Intent and outcome are separate records, and their divergence is data.** Fills never rewrite intent; intent never disguises outcome; the gap between them is the raw material of execution quality.
7. **Replay depends only on transactions.** Portfolio truth is permanently independent of why trades happened; the decision record links to the ledger, never the reverse.
8. **Execution-caused events use the front door.** Resolution, attribution, validation, deduplication — no privileged path into the ledger exists for anyone, including the domain that moves the money.
9. **Accounting remains deterministic through every partial, failed, and retried execution** — because facts are recorded at reality's granularity, partiality lives in the decision record, and replay never sees a maybe.
10. **Uncertainty stops at the gate.** Drifted premises, stale advice, insufficient truth, in-flight corporate actions — all halt and surface before the door, where doubt is a conversation instead of a correction.
11. **Execution is observable.** Every state, every transition, every actor, every divergence — visible while live, auditable forever after; history is append-only here as everywhere.
12. **The decision record is the platform's second memory.** The ledger remembers what happened; this domain remembers what was meant, chosen, and declined — and the platform's ability to judge itself lives entirely in the space between the two.

---

## Related Documents

- [TRANSACTION_DOMAIN_MODEL.md](TRANSACTION_DOMAIN_MODEL.md) — the immutable facts execution causes and may never edit
- [BROKER_ACCOUNT_DOMAIN.md](BROKER_ACCOUNT_DOMAIN.md) — the custody seam: instructions out, witness evidence back, admission pipeline between
- [CORPORATE_ACTION_DOMAIN.md](CORPORATE_ACTION_DOMAIN.md) — the sibling adjudication domain, and the source of the events that interrupt in-flight intents
- [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) — the boundary whose replayed truth validation checks against
- [ASSET_REGISTRY.md](ASSET_REGISTRY.md) — the identity authority whose lifecycle status gates executability
- [../investment/OPTIMIZER_PHILOSOPHY.md](../investment/OPTIMIZER_PHILOSOPHY.md) — the intelligence layer whose advice enters this domain's lifecycle and never bypasses it
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the decision-attribution and override-classification precedents this domain generalizes
