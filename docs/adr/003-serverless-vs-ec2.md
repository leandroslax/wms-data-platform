# ADR-003: Serverless vs EC2

## Decision

Priorizar componentes serverless como Lambda, API Gateway e Redshift Serverless.

## Status

Accepted

## Context

O projeto e portfolio-first e precisa demonstrar elasticidade, baixo custo idle e boa separacao de responsabilidades.

## Outcome

Componentes stateful ou sempre ativos ficam minimizados; a operacao principal usa servicos gerenciados e sob demanda.
