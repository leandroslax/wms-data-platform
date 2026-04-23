# ADR-002: Extração Batch com cx_Oracle

## Decision

Usar extração incremental via cx_Oracle com checkpoint em vez de CDC por streaming.

## Status

Accepted

## Context

O volume de dados do Oracle WMS não justifica infraestrutura de streaming. A extração incremental com controle de checkpoint garante confiabilidade, simplicidade e não depende de acesso ao redo log ou de serviços de captura de mudanças externos.

## Outcome

Os extractors Python leem tabelas Oracle com filtros de data/sequência, registram o checkpoint do último registro processado e são orquestrados pelo Airflow local. Esse modelo é suficiente para o volume atual e elimina dependências de infraestrutura complexa.
