{#
  compat.sql — Cross-database compatibility macros
  PostgreSQL  ←→  DuckDB

  Usage in models:
    {{ wms_epoch('delivered_at') }}   instead of  unix_timestamp(delivered_at)
    {{ wms_hour('movement_date') }}   instead of  hour(movement_date)
    {{ wms_today() }}                 instead of  current_date()
#}

{# ── wms_epoch: seconds since epoch from a timestamp column ── #}
{% macro wms_epoch(col) %}
  {%- if target.type in ('glue', 'spark') -%}
    unix_timestamp({{ col }})
  {%- elif target.type == 'duckdb' -%}
    epoch({{ col }})
  {%- else -%}
    EXTRACT(EPOCH FROM ({{ col }})::timestamptz)::bigint
  {%- endif -%}
{% endmacro %}

{# ── wms_hour: hour component of a timestamp ─────────────── #}
{% macro wms_hour(col) %}
  {%- if target.type in ('glue', 'spark') -%}
    hour({{ col }})
  {%- else -%}
    EXTRACT(HOUR FROM {{ col }})::int
  {%- endif -%}
{% endmacro %}

{# ── wms_today: current date (no parentheses in SQL standard) #}
{% macro wms_today() %}
  {%- if target.type in ('glue', 'spark') -%}
    current_date()
  {%- else -%}
    CURRENT_DATE
  {%- endif -%}
{% endmacro %}

{# ── wms_round: round(val, precision) — Spark accepts float, PG needs numeric ── #}
{% macro wms_round(col, precision) %}
  {%- if target.type in ('glue', 'spark') -%}
    round({{ col }}, {{ precision }})
  {%- else -%}
    round(({{ col }})::numeric, {{ precision }})
  {%- endif -%}
{% endmacro %}

{# ── wms_source_exists: check whether an optional source table exists ────────── #}
{% macro wms_source_exists(source_name, table_name) %}
  {% if execute %}
    {% set src = source(source_name, table_name) %}
    {% set relation = adapter.get_relation(
      database=src.database,
      schema=src.schema,
      identifier=src.identifier
    ) %}
    {{ return(relation is not none) }}
  {% else %}
    {{ return(false) }}
  {% endif %}
{% endmacro %}
