# ADR-001: Delta Lake vs Parquet

## Decision

Usar um formato de tabela ACID no data lake, em vez de parquet solto.

## Status

Accepted

## Context

O projeto precisa de schema evolution, deduplicacao, time travel e reconciliacao entre batch e CDC.

## Outcome

O design arquitetural permanece orientado a tabelas transacionais no lake. A estrategia definida para este projeto e usar Iceberg como formato oficial de tabela no lakehouse AWS.
