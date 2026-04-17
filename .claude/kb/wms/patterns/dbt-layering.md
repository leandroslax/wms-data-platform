# dbt Layering Pattern

## Staging

Mirror source tables closely, fix types, handle nulls, and standardize naming.

## Intermediate

Apply business joins, derive operational facts, deduplicate CDC effects, and align grains.

## Marts

Publish warehouse KPIs such as picking performance, inventory health, SLA, productivity, stockout risk, and geo performance.

## Rule

Do not hide business logic in API code when it belongs in dbt models.
