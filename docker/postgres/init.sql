-- ─────────────────────────────────────────────────────────────
-- WMS Data Platform — PostgreSQL init
-- Cria schemas (bronze/silver/gold) + database airflow
-- Executado automaticamente na primeira inicialização do container
-- ─────────────────────────────────────────────────────────────

-- Schemas da plataforma no banco wms
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- ── Bronze tables (espelho das tabelas Oracle WMS) ────────────

CREATE TABLE IF NOT EXISTS bronze.orders_documento (
    sequenciadocumento      TEXT,
    numerodocumento         TEXT,
    seriedocumento          TEXT,
    tipodocumento           TEXT,
    codigoempresa           TEXT,
    codigodepositante       TEXT,
    dataemissao             TIMESTAMPTZ,
    dataentrega             TIMESTAMPTZ,
    valortotaldocumento     NUMERIC(15,2),
    sequenciaintegracao     TEXT,
    _cdc_loaded_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bronze.orders_documentodetalhe (
    sequenciadocumento      TEXT,
    sequenciaitemdetalhe    TEXT,
    codigoproduto           TEXT,
    quantidade              NUMERIC(15,4),
    _cdc_loaded_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bronze.inventory_produtoestoque (
    sequenciaestoque        TEXT,
    codigoproduto           TEXT,
    codigoestabelecimento   TEXT,
    codigoempresa           TEXT,
    estoqueideal            INTEGER,
    estoqueminimo           INTEGER,
    estoquemaximo           INTEGER,
    estoqueseguranca        INTEGER,
    pontoreposicao          INTEGER,
    consumomedio            NUMERIC(15,4),
    classeproduto           TEXT,
    _cdc_loaded_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bronze.movements_entrada_saida (
    sequenciamovimento      TEXT,
    codigoproduto           TEXT,
    codigoestabelecimento   TEXT,
    codigodepositante       TEXT,
    quantidadeanterior      INTEGER,
    quantidadeatual         INTEGER,
    datamovimento           TIMESTAMPTZ,
    estadomovimento         TEXT,
    usuario                 TEXT,
    observacao              TEXT,
    _cdc_loaded_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bronze.products_snapshot (
    codigoproduto           TEXT,
    codigoestabelecimento   TEXT,
    descricaoproduto        TEXT,
    unidademedida           TEXT,
    classeproduto           TEXT,
    _cdc_loaded_at          TIMESTAMPTZ DEFAULT now()
);

-- ── Database para o Airflow ───────────────────────────────────
-- Precisa ser criado fora de uma transação; usando DO com exception
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow') THEN
        PERFORM dblink_exec('dbname=wms', 'CREATE DATABASE airflow OWNER wmsadmin');
    END IF;
EXCEPTION WHEN OTHERS THEN
    NULL; -- dblink pode não estar disponível; cria via script externo
END $$;
