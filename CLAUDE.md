# Portfolio Intelligence Platform Instructions

## Before starting any task

Read the following project documents first:

Required Reading

- ENGINEERING_PRINCIPLES.md
- ARCHITECTURE.md
- OPTIMIZER_PHILOSOPHY.md
- PORTFOLIO_CALCULATION_RULES.md
- DECISION_LOG.md

Read additional documents only when relevant.

Examples:

- docs/DECISION_LOG.md
  - when changing business rules
  - when refactoring existing architecture
  - when replacing an existing implementation

Do not read by default:

- docs/FUTURE_EXPERIMENTS.md
- docs/archive/
- docs/debug-notes/

The `docs/` directory is the authoritative source of project knowledge.
Avoid duplicating project rules inside CLAUDE.md.

If you are modifying an existing feature,
search DECISION_LOG.md for related architectural decisions before changing behavior.

### Optimizer-related work
Before modifying any optimizer logic, execution logic, policy logic,
or AI evaluation logic, read these documents first:

1. docs/engineering/ENGINEERING_PRINCIPLES.md
2. docs/architecture/ARCHITECTURE.md
3. docs/investment/OPTIMIZER_PHILOSOPHY.md
4. docs/investment/PORTFOLIO_CALCULATION_RULES.md
5. docs/engineering/DECISION_LOG.md (if relevant)

Do not modify optimizer behavior without understanding the philosophy described in OPTIMIZER_PHILOSOPHY.md.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
