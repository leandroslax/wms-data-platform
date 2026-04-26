-- ─────────────────────────────────────────────────────────────────────────────
-- WMS Data Platform — Investigação de Churn e Orphan Movements
-- Uso: psql postgresql://wmsadmin:wmsadmin2026@localhost:5432/wms -f pipelines/validation/investigate_churn_and_orphans.sql
-- ─────────────────────────────────────────────────────────────────────────────

\echo ''
\echo '═══════════════════════════════════════════════════════'
\echo '  INVESTIGAÇÃO DE CHURN — CLIENTES PERDIDOS ABRIL/2026'
\echo '═══════════════════════════════════════════════════════'
\echo ''

-- ── 1. CLIENTES ATIVOS NO Q1/2026 QUE NÃO APARECEM EM ABRIL ─────────────────
\echo '── 1. CLIENTES PERDIDOS: ativos em jan-mar/2026, ausentes em abril/2026 ──'

WITH clientes_q1 AS (
    SELECT DISTINCT depositor_id
    FROM gold.mart_order_sla
    WHERE issued_at >= '2026-01-01'
      AND issued_at <  '2026-04-01'
),
clientes_abril AS (
    SELECT DISTINCT depositor_id
    FROM gold.mart_order_sla
    WHERE issued_at >= '2026-04-01'
      AND issued_at <  '2026-05-01'
),
perdidos AS (
    SELECT q1.depositor_id
    FROM clientes_q1 q1
    LEFT JOIN clientes_abril a ON a.depositor_id = q1.depositor_id
    WHERE a.depositor_id IS NULL
)
SELECT
    p.depositor_id                                          AS cliente_perdido,
    COUNT(o.order_id)                                       AS pedidos_q1,
    MIN(o.issued_at)::DATE                                  AS primeiro_pedido_q1,
    MAX(o.issued_at)::DATE                                  AS ultimo_pedido_q1,
    ROUND(AVG(o.total_value)::NUMERIC, 2)                   AS ticket_medio,
    SUM(o.total_value)                                      AS valor_total_q1,
    COUNT(*) FILTER (WHERE o.sla_status = 'late')           AS pedidos_atrasados,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE o.sla_status = 'late')
        / NULLIF(COUNT(*), 0), 1
    )                                                       AS pct_late
FROM perdidos p
JOIN gold.mart_order_sla o ON o.depositor_id = p.depositor_id
WHERE o.issued_at >= '2026-01-01'
  AND o.issued_at <  '2026-04-01'
GROUP BY p.depositor_id
ORDER BY valor_total_q1 DESC;

-- ── 2. RESUMO DO CHURN ────────────────────────────────────────────────────────
\echo ''
\echo '── 2. RESUMO DO CHURN ──'

WITH clientes_q1 AS (
    SELECT DISTINCT depositor_id
    FROM gold.mart_order_sla
    WHERE issued_at >= '2026-01-01' AND issued_at < '2026-04-01'
),
clientes_abril AS (
    SELECT DISTINCT depositor_id
    FROM gold.mart_order_sla
    WHERE issued_at >= '2026-04-01' AND issued_at < '2026-05-01'
),
perdidos AS (
    SELECT q1.depositor_id FROM clientes_q1 q1
    LEFT JOIN clientes_abril a ON a.depositor_id = q1.depositor_id
    WHERE a.depositor_id IS NULL
),
novos AS (
    SELECT a.depositor_id FROM clientes_abril a
    LEFT JOIN clientes_q1 q1 ON q1.depositor_id = a.depositor_id
    WHERE q1.depositor_id IS NULL
)
SELECT
    (SELECT COUNT(*) FROM clientes_q1)      AS clientes_ativos_q1,
    (SELECT COUNT(*) FROM clientes_abril)   AS clientes_ativos_abril,
    (SELECT COUNT(*) FROM perdidos)         AS clientes_perdidos,
    (SELECT COUNT(*) FROM novos)            AS clientes_novos_abril,
    ROUND(
        100.0 * (SELECT COUNT(*) FROM perdidos)
        / NULLIF((SELECT COUNT(*) FROM clientes_q1), 0), 1
    )                                       AS taxa_churn_pct;

-- ── 3. CLIENTES PERDIDOS COM ALTO % DE PEDIDOS ATRASADOS (possível causa) ────
\echo ''
\echo '── 3. HIPÓTESE: churn correlacionado com SLA late (threshold > 50%) ──'

WITH clientes_q1 AS (
    SELECT DISTINCT depositor_id FROM gold.mart_order_sla
    WHERE issued_at >= '2026-01-01' AND issued_at < '2026-04-01'
),
clientes_abril AS (
    SELECT DISTINCT depositor_id FROM gold.mart_order_sla
    WHERE issued_at >= '2026-04-01' AND issued_at < '2026-05-01'
),
perdidos AS (
    SELECT q1.depositor_id FROM clientes_q1 q1
    LEFT JOIN clientes_abril a ON a.depositor_id = q1.depositor_id
    WHERE a.depositor_id IS NULL
),
sla_perdidos AS (
    SELECT
        o.depositor_id,
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE o.sla_status IN ('late','at_risk')) AS em_risco,
        ROUND(100.0 * COUNT(*) FILTER (WHERE o.sla_status IN ('late','at_risk'))
            / NULLIF(COUNT(*),0), 1) AS pct_problemas_sla
    FROM gold.mart_order_sla o
    JOIN perdidos p ON p.depositor_id = o.depositor_id
    WHERE o.issued_at >= '2026-01-01' AND o.issued_at < '2026-04-01'
    GROUP BY o.depositor_id
)
SELECT
    depositor_id,
    total       AS pedidos_q1,
    em_risco    AS pedidos_com_problema_sla,
    pct_problemas_sla
FROM sla_perdidos
ORDER BY pct_problemas_sla DESC;

-- ── 4. NOVOS CLIENTES EM ABRIL (compensação parcial do churn) ────────────────
\echo ''
\echo '── 4. NOVOS CLIENTES EM ABRIL (estreantes) ──'

WITH clientes_q1 AS (
    SELECT DISTINCT depositor_id FROM gold.mart_order_sla
    WHERE issued_at >= '2026-01-01' AND issued_at < '2026-04-01'
)
SELECT
    o.depositor_id,
    COUNT(*)                AS pedidos_abril,
    MIN(o.issued_at)::DATE  AS primeiro_pedido,
    SUM(o.total_value)      AS valor_total
FROM gold.mart_order_sla o
LEFT JOIN clientes_q1 q1 ON q1.depositor_id = o.depositor_id
WHERE o.issued_at >= '2026-04-01'
  AND o.issued_at <  '2026-05-01'
  AND q1.depositor_id IS NULL
GROUP BY o.depositor_id
ORDER BY valor_total DESC;

\echo ''
\echo '═══════════════════════════════════════════════════════'
\echo '  INVESTIGAÇÃO DE ORPHAN MOVEMENTS'
\echo '═══════════════════════════════════════════════════════'
\echo ''

-- ── 5. CLASSIFICAÇÃO DOS ORPHAN MOVEMENTS ────────────────────────────────────
\echo '── 5. ORPHAN MOVEMENTS — distribuição por tipo e período ──'

WITH orphans AS (
    SELECT m.*
    FROM bronze.movements_entrada_saida m
    WHERE m.estadomovimento = '8'
      AND NOT EXISTS (
          SELECT 1 FROM bronze.orders_documento o
          WHERE o.codigodepositante = m.codigodepositante
            AND o.dataemissao <= m.datamovimento
      )
)
SELECT
    DATE_TRUNC('month', datamovimento)::DATE    AS mes,
    estadomovimento                             AS estado,
    COUNT(*)                                    AS total,
    COUNT(DISTINCT codigodepositante)           AS depositantes_distintos,
    COUNT(DISTINCT codigoproduto)               AS produtos_distintos,
    MIN(datamovimento)::DATE                    AS data_min,
    MAX(datamovimento)::DATE                    AS data_max
FROM orphans
GROUP BY 1, 2
ORDER BY 1 DESC;

-- ── 6. ORPHAN MOVEMENTS ANTERIORES AO PERÍODO DE EXTRAÇÃO ────────────────────
\echo ''
\echo '── 6. Orphan movements anteriores ao primeiro pedido no bronze ──'

SELECT
    CASE
        WHEN m.datamovimento < (SELECT MIN(dataemissao) FROM bronze.orders_documento)
        THEN 'anterior_ao_periodo_de_extracao'
        ELSE 'dentro_do_periodo'
    END                                             AS classificacao,
    COUNT(*)                                        AS total,
    MIN(m.datamovimento)::DATE                      AS data_min,
    MAX(m.datamovimento)::DATE                      AS data_max
FROM bronze.movements_entrada_saida m
WHERE m.estadomovimento = '8'
  AND NOT EXISTS (
      SELECT 1 FROM bronze.orders_documento o
      WHERE o.codigodepositante = m.codigodepositante
        AND o.dataemissao <= m.datamovimento
  )
GROUP BY 1;

\echo ''
\echo '═══════════════════════════════════════════════════════'
\echo '  INVESTIGAÇÃO CONCLUÍDA'
\echo '═══════════════════════════════════════════════════════'
\echo ''
