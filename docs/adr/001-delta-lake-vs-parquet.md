# ADR-001: Medallion no PostgreSQL

## Decision

Usar arquitetura medallion (bronze / silver / gold) em schemas PostgreSQL, em vez de um data lake em arquivos ou formatos de tabela externos.

## Status

Accepted

## Context

O projeto precisa de separação clara entre dados brutos, normalizados e analíticos, com contratos explícitos entre camadas, rastreabilidade e suporte a evolução de schema. A solução deve funcionar localmente sem dependências de infraestrutura externa.

## Outcome

A estratégia adotada é o uso de schemas `bronze`, `silver` e `gold` no mesmo PostgreSQL local. O dbt-postgres gerencia as transformações entre camadas. Isso garante portabilidade, zero custo de infraestrutura e simplicidade operacional.
