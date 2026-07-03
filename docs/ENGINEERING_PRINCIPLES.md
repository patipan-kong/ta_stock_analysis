# Engineering Principles

These principles apply to all code changes.

## Reuse Before Create

Before implementing any change:

- Search for existing implementations.
- Search for similar configuration.
- Search for existing helper functions.
- Search for duplicated business rules.
- Reuse existing services whenever possible.

Do not introduce parallel implementations without a clear architectural reason.

---

## Single Source of Truth

Business rules should exist in one authoritative location.

Avoid:

- duplicated configuration
- duplicated constants
- duplicated calculations
- duplicated business rules

If duplication is unavoidable, document why.

---

## Configuration

Avoid introducing new hardcoded values.

Prefer:

- Portfolio Settings
- Policy Engine
- Shared configuration

instead of local constants or fallback literals.

---

## Architecture

Before creating a new module or service:

- Identify the existing owner of the responsibility.
- Extend the existing implementation whenever appropriate.
- Avoid creating overlapping responsibilities.

---

## Refactoring

When modifying existing features:

- Prefer improving existing code over rewriting.
- Preserve compatibility whenever possible.
- Remove obsolete code after migration.

---

## Failure Handling

Avoid silent failures.

If a component falls back to degraded behavior:

- Log the reason.
- Include stack trace where appropriate.
- Make the degraded mode observable.

---

## Code Review Checklist

Before submitting changes, verify:

- No duplicated business rules.
- No duplicated configuration.
- No unnecessary fallback values.
- Existing helper functions reused.
- Existing services reused.
- Single Source of Truth preserved.

## Data Ownership

Before adding a new field, calculation, or configuration:

Identify the authoritative source.

Do not recalculate or duplicate data that already exists elsewhere.

If multiple components require the same information,
share the existing source instead of creating another copy.

## Shared Schemas

If multiple AI layers exchange similar data,
reuse the same schema and normalization rules.

Avoid introducing layer-specific field names
unless the semantics genuinely differ.

## System Integration

When extending an existing feature:

Trace upstream and downstream dependencies.

Verify that:

- existing call sites still work
- prompt builders still receive required data
- adapters remain compatible
- fallback paths still behave correctly


------------------------------------------------

Never allow critical subsystems to fail silently.

Every degraded mode must be observable.

Fallbacks are acceptable.
Silent failures are not.