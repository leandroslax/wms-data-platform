-- Migração: adiciona colunas dataemissao e data_ref à tabela de movimentos
-- Executar com: docker compose exec postgres psql -U wmsadmin -d wms -f /docker-entrypoint-initdb.d/migrate_movements.sql
-- ou: docker compose exec postgres psql -U wmsadmin -d wms < docker/postgres/migrate_movements.sql

ALTER TABLE bronze.movements_entrada_saida
    ADD COLUMN IF NOT EXISTS dataemissao  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS data_ref     TIMESTAMPTZ;

\echo 'Migration concluída: colunas dataemissao e data_ref adicionadas.'
