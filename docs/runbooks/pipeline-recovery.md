# Runbook: Pipeline Recovery

**Versão:** 2.0  
**Última atualização:** 2026-04-26  
**Audiência:** Engenharia de Dados, DevOps  
**Tempo estimado de recuperação:** 30–90 minutos dependendo da janela afetada

---

## 1. Visão Geral

Este runbook cobre a recuperação de falhas na pipeline de dados do WMS Data Platform, que segue a arquitetura:

```
Oracle WMS → Airflow (extração cx_Oracle) → bronze (PostgreSQL)
                                                  ↓
                                         dbt → silver → gold
```

Falhas podem ocorrer em qualquer camada. As seções abaixo cobrem diagnóstico e recovery por ponto de falha.

---

## 2. Diagnóstico Rápido (< 5 min)

### 2.1 Validação de integridade

Execute o script de validação completo antes de qualquer ação:

```bash
psql $DATABASE_URL -f pipelines/validation/validate_pipeline.sql
```

O script verifica:
- Contagens e intervalo de datas por tabela bronze
- Gaps de watermark (dias sem ingestão nos últimos 90 dias)
- Duplicatas por chave primária
- Orphan movements sem order correspondente
- Cobertura do campo `delivered_at` / `delivered_at_proxy`
- Freshness de cada tabela (horas desde última carga)
- Contagem dos 5 marts gold

### 2.2 Verificar DAGs no Airflow

```bash
# Abrir UI do Airflow
open http://localhost:8080

# Ou via CLI
docker exec -it airflow-scheduler airflow dags list-runs \
    --dag-id wms_extraction_dag --state failed --limit 5
```

### 2.3 Verificar logs da API e containers

```bash
# Status dos containers
docker compose ps

# Logs recentes da extração
docker compose logs airflow-scheduler --tail 100 | grep -E "ERROR|WARN|checkpoint"

# Logs do PostgreSQL
docker compose logs postgres --tail 50
```

---

## 3. Cenários de Falha e Recovery

### 3.1 Falha na Extração Oracle → Bronze

**Sintomas:** Tabelas bronze sem registros novos, DAG com status `failed`, freshness > 24h.

**Causas comuns:**
- Conexão Oracle instável (timeout, credenciais expiradas)
- Watermark corrompido ou adiantado demais
- Schema Oracle alterado (coluna renomeada)

**Recovery:**

```bash
# 1. Verificar checkpoint atual
psql $DATABASE_URL -c "
SELECT entity_name, last_value, updated_at
FROM bronze.extraction_checkpoint
ORDER BY updated_at DESC;"

# 2. Se watermark estiver corrompido, resetar para janela segura
psql $DATABASE_URL -c "
UPDATE bronze.extraction_checkpoint
SET last_value = '2026-03-01 00:00:00'
WHERE entity_name = 'orders_documento';"

# 3. Reexecutar extração manualmente
python pipelines/extraction/oracle_to_postgres.py --mode incremental

# 4. Ou forçar reprocessamento de janela específica
python pipelines/extraction/oracle_to_postgres.py \
    --mode full_90d \
    --start-date 2026-03-01 \
    --end-date 2026-04-01
```

### 3.2 Falha no dbt (Bronze → Silver → Gold)

**Sintomas:** Marts gold desatualizados, dbt run com erros, dados silver inconsistentes com bronze.

**Recovery:**

```bash
# 1. Ver status dos modelos dbt
cd transform/dbt_wms
dbt test --project-dir . 2>&1 | grep -E "FAIL|WARN|ERROR"

# 2. Reprocessar modelos afetados (ex: marts dependentes de mart_order_sla)
dbt run --select mart_order_sla+ --full-refresh

# 3. Reprocessar toda a camada gold
dbt run --select marts.* --full-refresh

# 4. Rodar testes após recovery
dbt test --project-dir .
```

**Nota:** O modelo `mart_order_sla` usa `incremental_strategy=merge`. Se o `delivered_at` estiver ausente no Oracle, o mart usa `delivered_at_proxy` (primeiro movimento de saída do depositante após emissão). Isso é esperado — não é falha.

### 3.3 Dados Faltantes — Gap de Dias

**Sintomas:** Script de validação aponta dias sem ingestão.

**Recovery com reprocessamento por janela:**

```bash
# Reprocessar gap específico (ex: 2026-04-10 a 2026-04-15)
python pipelines/extraction/oracle_to_postgres.py \
    --mode incremental \
    --start-date 2026-04-10 \
    --end-date 2026-04-15

# Após reprocessar bronze, reprocessar silver e gold
cd transform/dbt_wms
dbt run --full-refresh --select staging.* marts.*
```

### 3.4 Duplicatas na Bronze

**Sintomas:** Script de validação retorna registros com `ocorrencias > 1`.

**Recovery:**

```bash
# Deduplicar orders_documento (mantém registro mais recente)
psql $DATABASE_URL -c "
DELETE FROM bronze.orders_documento
WHERE ctid NOT IN (
    SELECT MAX(ctid)
    FROM bronze.orders_documento
    GROUP BY sequenciadocumento
);"

# Deduplicar movements_entrada_saida
psql $DATABASE_URL -c "
DELETE FROM bronze.movements_entrada_saida
WHERE ctid NOT IN (
    SELECT MAX(ctid)
    FROM bronze.movements_entrada_saida
    GROUP BY sequenciamovimento
);"

# Reprocessar gold após deduplicação
cd transform/dbt_wms && dbt run --full-refresh --select marts.*
```

### 3.5 Falha no Enriquecimento Geográfico

**Sintomas:** `bronze.geo_reference` vazia ou `mart_geo_performance` com NULLs em `uf`/`estado`.

**Recovery:**

```bash
python pipelines/enrichment/enrich_geo.py

# Verificar resultado
psql $DATABASE_URL -c "
SELECT entity_type, COUNT(*) FROM bronze.geo_reference GROUP BY 1;"
```

---

## 4. Validação Pós-Recovery

Após qualquer recovery, execute a sequência completa:

```bash
# 1. Validação de integridade
psql $DATABASE_URL -f pipelines/validation/validate_pipeline.sql

# 2. Testes dbt
cd transform/dbt_wms && dbt test

# 3. Teste de API
curl http://localhost:8000/health
curl http://localhost:8000/orders/summary

# 4. Confirmar freshness
psql $DATABASE_URL -c "
SELECT tabela, ultima_carga,
       ROUND(EXTRACT(EPOCH FROM NOW() - ultima_carga)/3600, 1) AS horas_atras
FROM (
    SELECT 'orders' AS tabela, MAX(_cdc_loaded_at) AS ultima_carga FROM bronze.orders_documento
    UNION ALL
    SELECT 'movements',        MAX(_cdc_loaded_at) FROM bronze.movements_entrada_saida
) t;"
```

---

## 5. SLAs de Recovery

| Cenário | Severidade | Tempo máximo aceitável |
|---|---|---|
| Extração parada > 24h | P0 | Recovery em 2h |
| Gap de 1–3 dias | P1 | Recovery em 4h |
| Duplicatas nos marts | P1 | Recovery em 4h |
| dbt run falhando | P1 | Recovery em 2h |
| Enriquecimento geo desatualizado | P2 | Recovery em 24h |

---

## 6. Contatos e Escalação

| Papel | Responsabilidade |
|---|---|
| Eng. Dados | Extração Oracle, scripts Python, checkpoints |
| DBA Oracle | Acesso Oracle, validação `delivered_at`, schema changes |
| DevOps | Containers Docker, Airflow, conectividade de rede |

---

## 7. Histórico de Incidentes

| Data | Descrição | Causa Raiz | Resolução |
|---|---|---|---|
| 2026-04-26 | `delivered_at` ausente no Oracle WMS | Campo `DATAENTREGA` não preenchido na instalação local | Implementado `delivered_at_proxy` via movimento de saída (estadomovimento=8) |
| 2026-04-26 | Queda de 16,6% clientes ativos em abril | Em investigação | Ver task #2 — análise de churn |
