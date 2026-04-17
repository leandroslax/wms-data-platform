# ADR-002: Glue vs Redshift for Transform

## Decision

Separar transformacao serverless e serving analitico.

## Status

Accepted

## Context

Glue simplifica a escrita e transformacao de tabelas Iceberg com Spark gerenciado, enquanto Redshift atende melhor workloads de serving e consultas de baixa latencia.

## Outcome

dbt sera preparado para Glue no fluxo principal e Redshift Serverless sera mantido para serving e consumo orientado a produto.
