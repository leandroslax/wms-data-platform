# DAG Orchestration Pattern

## Target DAG set

1. `extract_wms`
2. `transform_dbt`
3. `quality_check`
4. `load_warehouse`
5. `embed_rag`
6. `freshness_monitor`

## Sequencing rule

Extraction lands raw or normalized assets first. dbt transforms only after extract success. Quality gates block warehouse loads. Embeddings run on documentation cadence, not transaction cadence.

## Implementation rule

Each DAG should own one operational responsibility and express dependencies through scheduling or explicit dataset contracts rather than mixing all concerns in one graph.
