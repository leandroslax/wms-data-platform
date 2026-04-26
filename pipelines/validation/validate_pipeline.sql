-- ─────────────────────────────────────────────────────────────────────────────
-- WMS Data Platform — Pipeline Integrity Validation
-- Execute contra o PostgreSQL local para confirmar saúde dos dados.
-- Uso: psql $DATABASE_URL -f pipelines/validation/validate_pipeline.sql
-- ─────────────────────────────────────────────────────────────────────────────

\echo ''
\echo '═══════════════════════════════════════════════════════'
\echo '  WMS DATA PLATFORM — VALIDAÇÃO DE INTEGRIDADE'
\echo '═══════════════════════════════════════════════════════'
\echo ''

-- ── 1. CONTAGENS POR CAMADA ───────────────────────────────────────────────────
\echo '── 1. CONTAGENS POR CAMADA ──'

SELECT
    'bronze.orders_documento'       AS tabela,
    COUNT(*)                        AS total_registros,
    MIN(dataemissao)                AS data_min,
    MAX(dataemissao)                AS data_max,
    COUNT(*) FILTER (WHERE dataemissao IS NULL) AS nulls_watermark
FROM bronze.orders_documento

UNION ALL

SELECT
    'bronze.movements_entrada_saida',
    COUNT(*),
    MIN(datamovimento),
    MAX(datamovimento),
    COUNT(*) FILTER (WHERE datamovimento IS NULL)
FROM bronze.movements_entrada_saida

UNION ALL

SELECT
    'bronze.products_snapshot',
    COUNT(*),
    NULL, NULL,
    COUNT(*) FILTER (WHERE codigoproduto IS NULL)
FROM bronze.products_snapshot

UNION ALL

SELECT
    'bronze.inventory_produtoestoque',
    COUNT(*),
    NULL, NULL,
    COUNT(*) FILTER (WHERE codigoproduto IS NULL)
FROM bronze.inventory_produtoestoque;

-- ── 2. GAPS DE WATERMARK (dias sem ingestão) ──────────────────────────────────
\echo ''
\echo '── 2. GAPS DE WATERMARK (dias sem ingestão — últimos 90 dias) ──'

WITH series AS (
    SELECT generate_series(
        CURRENT_DATE - INTERVAL '90 days',
        CURRENT_DATE - INTERVAL '1 day',
        '1 day'
    )::DATE AS dia
),
ingested_orders AS (
    SELECT DATE(dataemissao) AS dia
    FROM bronze.orders_documento
    WHERE dataemissao >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY 1
),
ingested_movements AS (
    SELECT DATE(datamovimento) AS dia
    FROM bronze.movements_entrada_saida
    WHERE datamovimento >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY 1
)
SELECT
    s.dia,
    CASE WHEN o.dia IS NULL THEN '❌ SEM DADOS' ELSE '✅ OK' END AS orders,
    CASE WHEN m.dia IS NULL THEN '❌ SEM DADOS' ELSE '✅ OK' END AS movements
FROM series s
LEFT JOIN ingested_orders    o ON o.dia = s.dia
LEFT JOIN ingested_movements m ON m.dia = s.dia
WHERE o.dia IS NULL OR m.dia IS NULL
ORDER BY s.dia DESC
LIMIT 20;

-- ── 3. DUPLICATAS NA BRONZE ───────────────────────────────────────────────────
\echo ''
\echo '── 3. DUPLICATAS NA BRONZE ──'

SELECT
    'orders_documento'  AS tabela,
    sequenciadocumento  AS chave,
    COUNT(*)            AS ocorrencias
FROM bronze.orders_documento
GROUP BY sequenciadocumento
HAVING COUNT(*) > 1
LIMIT 10;

SELECT
    'movements_entrada_saida' AS tabela,
    sequenciamovimento        AS chave,
    COUNT(*)                  AS ocorrencias
FROM bronze.movements_entrada_saida
GROUP BY sequenciamovimento
HAVING COUNT(*) > 1
LIMIT 10;

-- ── 4. ORPHAN RECORDS (movements sem order) ───────────────────────────────────
\echo ''
\echo '── 4. ORPHAN MOVEMENTS (sem order correspondente no mesmo depositante) ──'

SELECT
    COUNT(*) AS movements_sem_order
FROM bronze.movements_entrada_saida m
WHERE m.estadomovimento = '8'
  AND NOT EXISTS (
      SELECT 1 FROM bronze.orders_documento o
      WHERE o.codigodepositante = m.codigodepositante
        AND o.dataemissao       <= m.datamovimento
  );

-- ── 5. COBERTURA DO CAMPO delivered_at (crítico para SLA) ────────────────────
\echo ''
\echo '── 5. COBERTURA DO CAMPO delivered_at / delivered_at_proxy (gold.mart_order_sla) ──'

SELECT
    COUNT(*)                                                    AS total_pedidos,
    COUNT(*) FILTER (WHERE delivered_at IS NOT NULL)            AS com_delivered_at_real,
    COUNT(*) FILTER (WHERE delivered_at IS NULL
                      AND delivered_at_proxy IS NOT NULL)       AS apenas_proxy,
    COUNT(*) FILTER (WHERE delivered_at IS NULL
                      AND delivered_at_proxy IS NULL)           AS sem_nenhum,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE resolved_delivered_at IS NOT NULL) / NULLIF(COUNT(*),0),
    1) AS pct_com_data_resolucao
FROM gold.mart_order_sla;

-- ── 6. DISTRIBUIÇÃO DE STATUS SLA ────────────────────────────────────────────
\echo ''
\echo '── 6. DISTRIBUIÇÃO DE STATUS SLA (últimos 6 meses) ──'

SELECT
    sla_status,
    COUNT(*)                                                AS total,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)     AS pct
FROM gold.mart_order_sla
WHERE issued_at >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY sla_status
ORDER BY total DESC;

-- ── 7. CLIENTES ATIVOS: EVOLUÇÃO MENSAL (base para análise de churn) ─────────
\echo ''
\echo '── 7. CLIENTES ATIVOS POR MÊS (últimos 6 meses) ──'

SELECT
    DATE_TRUNC('month', issued_at)::DATE    AS mes,
    COUNT(DISTINCT depositor_id)            AS clientes_ativos,
    COUNT(*)                                AS total_pedidos
FROM gold.mart_order_sla
WHERE issued_at >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY 1
ORDER BY 1 DESC;

-- ── 8. SAÚDE DOS MARTS GOLD ───────────────────────────────────────────────────
\echo ''
\echo '── 8. CONTAGEM DOS MARTS GOLD ──'

SELECT 'mart_order_sla'          AS mart, COUNT(*) AS linhas FROM gold.mart_order_sla
UNION ALL
SELECT 'mart_inventory_health',           COUNT(*) FROM gold.mart_inventory_health
UNION ALL
SELECT 'mart_picking_performance',        COUNT(*) FROM gold.mart_picking_performance
UNION ALL
SELECT 'mart_operator_productivity',      COUNT(*) FROM gold.mart_operator_productivity
UNION ALL
SELECT 'mart_stockout_risk',              COUNT(*) FROM gold.mart_stockout_risk
ORDER BY 1;

-- ── 9. FRESHNESS — últimas cargas por tabela ──────────────────────────────────
\echo ''
\echo '── 9. FRESHNESS — ÚLTIMA CARGA POR TABELA ──'

SELECT
    tabela,
    ultima_carga,
    EXTRACT(EPOCH FROM (NOW() - ultima_carga)) / 3600 AS horas_atras
FROM (
    SELECT 'bronze.orders_documento'       AS tabela, MAX(_cdc_loaded_at) AS ultima_carga FROM bronze.orders_documento
    UNION ALL
    SELECT 'bronze.movements_entrada_saida',           MAX(_cdc_loaded_at) FROM bronze.movements_entrada_saida
    UNION ALL
    SELECT 'bronze.products_snapshot',                 MAX(_cdc_loaded_at) FROM bronze.products_snapshot
    UNION ALL
    SELECT 'bronze.inventory_produtoestoque',          MAX(_cdc_loaded_at) FROM bronze.inventory_produtoestoque
) t
ORDER BY ultima_carga DESC;

\echo ''
\echo '═══════════════════════════════════════════════════════'
\echo '  VALIDAÇÃO CONCLUÍDA'
\echo '═══════════════════════════════════════════════════════'
\echo ''
