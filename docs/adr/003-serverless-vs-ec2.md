# ADR-003: dbt-postgres para Transformação e Serving

## Decision

Usar dbt Core com o adapter dbt-postgres tanto para transformação entre camadas quanto para materialização dos marts de serving.

## Status

Accepted

## Context

O projeto precisa de uma camada de transformação clara, testável e documentável, conectada à mesma instância PostgreSQL usada para ingestão. O uso de um único engine evita a necessidade de sincronização entre sistemas distintos.

## Outcome

dbt-postgres compila os modelos SQL e os materializa como tabelas ou views nos schemas `silver` e `gold` do PostgreSQL. A API e o Grafana consomem diretamente do `gold`. Não há dependência de engines separados de transformação ou serving.
