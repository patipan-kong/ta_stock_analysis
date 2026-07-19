# M34 Finding Register

**Status:** Empty template. No findings have been created.

**Governing protocol:**
`../../../M34_WP1_charter_and_audit_protocol.md`

**Working-artifact rules:** `../README.md`

## Use

This register is the canonical record of M34 findings. A potential concern is
not entered as verified merely because its name, label, or implementation
looks suspicious. It must follow WP1 discovery and verification.

Allowed lifecycle states are `DRAFT`, `VERIFIED`, `CLASSIFIED`,
`IN_ARCHITECTURAL_REVIEW`, `DISPOSITION_APPROVED`, `CLOSED`,
`NEEDS_EVIDENCE`, `DISPUTED`, and `RETURNED_TO_ARB`.

Allowed blocking states are `ARB_STOP`, `M34_1_BLOCKER`,
`CONDITIONAL_BLOCKER`, `NON_BLOCKING`, and `PENDING_VERIFICATION`.

## Record template

```markdown
## M34-F-NNNN - <short factual title>

- Status: DRAFT
- Primary type: <WP1 finding type>
- Secondary types: <sorted WP1 finding types | NONE>
- Severity: <CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL>
- Blocking status: <ARB_STOP | M34_1_BLOCKER | CONDITIONAL_BLOCKER | NON_BLOCKING | PENDING_VERIFICATION>
- Confidence: <VERIFIED | PARTIAL | UNKNOWN>
- Work package: <M34-WP#>
- Affected user questions: <1-5, sorted | NONE>
- Affected corpus ids: <sorted M34-C-NNNN ids>
- Affected surfaces/contracts: <stable locators | NONE>
- Owning domain: <one WP1 owner | UNKNOWN_OWNERSHIP>
- Evidence steward: <identity or approved role>
- Evidence ids: <sorted M34-E-NNNN ids>
- Related finding ids: <sorted M34-F-NNNN ids | NONE>
- Review ids: <sorted M34-R-NNNN ids | PENDING>
- Decision id: <M34-D-NNNN | PENDING>

### Description

<What is observed, without implementation design.>

### Evidence limitations and conflicts

<Missing evidence, bounded searches, environment limitations, competing
claims, or NONE.>

### Owner and authority

<One concept owner, governing reference, and any ownership dispute.>

### Constitutional concern

<Exact principle and governing artifact.>

### Proposed disposition

<One WP1 permitted disposition and rationale. No implementation design.>

### Readiness effect

<Exact effect on the M34 outcome and M34.1 GO/NO-GO.>

### Review record

- Verified by / UTC: PENDING
- Domain-owner response / UTC: PENDING
- Architectural reviewer / UTC: PENDING
- Decision authority / UTC: PENDING
- Approved disposition: PENDING
- Closure evidence ids: PENDING
- Closure review id: PENDING
```

## Records

No records. Finding discovery is outside the current task.

