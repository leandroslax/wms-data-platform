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
    dataemissao             TIMESTAMPTZ,
    data_ref                TIMESTAMPTZ,
    estadomovimento         TEXT,
    usuario                 TEXT,
    observacao              TEXT,
    _cdc_loaded_at          TIMESTAMPTZ DEFAULT now()
);

-- Migração segura: adiciona colunas novas se o container já existia
ALTER TABLE bronze.movements_entrada_saida
    ADD COLUMN IF NOT EXISTS dataemissao  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS data_ref     TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS bronze.products_snapshot (
    codigoproduto           TEXT,
    codigoestabelecimento   TEXT,
    descricaoproduto        TEXT,
    unidademedida           TEXT,
    classeproduto           TEXT,
    _cdc_loaded_at          TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────
-- Enriquecimento geográfico e climático
-- Populado pelo pipeline pipelines/enrichment/enrich_geo.py
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS bronze.geo_reference (
    entity_type     TEXT        NOT NULL,   -- 'warehouse' | 'company'
    entity_id       TEXT        NOT NULL,   -- codigoestabelecimento / codigodepositante
    cep             TEXT,                   -- CEP formatado (00000-000)
    logradouro      TEXT,                   -- logradouro via ViaCEP
    bairro          TEXT,                   -- bairro via ViaCEP
    localidade      TEXT,                   -- cidade via ViaCEP
    uf              TEXT,                   -- sigla do estado (SP, RJ, ...)
    estado          TEXT,                   -- nome completo do estado (IBGE)
    regiao          TEXT,                   -- macro-região (Norte, Sudeste, ...)
    ibge_code       TEXT,                   -- código IBGE do município (7 dígitos)
    latitude        NUMERIC(10,6),          -- centróide do estado (IBGE)
    longitude       NUMERIC(11,6),          -- centróide do estado (IBGE)
    _enriched_at    TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS bronze.weather_daily (
    location_uf         TEXT        NOT NULL,   -- sigla UF (SP, RJ, ...)
    weather_date        DATE        NOT NULL,   -- data de referência
    avg_temperature_c   NUMERIC(5,2),           -- temperatura média (°C)
    min_temperature_c   NUMERIC(5,2),           -- temperatura mínima (°C)
    max_temperature_c   NUMERIC(5,2),           -- temperatura máxima (°C)
    precipitation_mm    NUMERIC(8,2),           -- precipitação total (mm)
    weather_condition   TEXT,                   -- descrição em português (WMO)
    wind_speed_kmh      NUMERIC(6,2),           -- velocidade máx. do vento (km/h)
    _enriched_at        TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (location_uf, weather_date)
);

-- Banco 'airflow' criado pelo script 02_create_airflow_db.sh
