# Serving And Agents Pattern

## Structured path

`AnalystAgent` should prefer SQL over PostgreSQL gold marts and curated serving views for exact metrics.

## Semantic path

`ResearchAgent` should retrieve runbooks, ADRs, incident notes, and platform docs from the Qdrant vector store.

## Synthesis path

`ReporterAgent` should combine exact analytical facts with semantic operational context.

## Product rule

The API layer should expose deterministic operational endpoints even when the agent layer is unavailable.
