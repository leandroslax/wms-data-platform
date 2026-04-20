{#
  generate_schema_name.sql
  Override do comportamento padrão do dbt que concatena profile schema + custom schema.
  Com este macro, modelos com +schema: silver ficam em "silver" (não em "gold_silver").
  Modelos sem custom schema usam o schema do profile (target.schema).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema | trim }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
