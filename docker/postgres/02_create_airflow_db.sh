#!/usr/bin/env bash
# Cria o banco de dados 'airflow' para o Airflow metadata store.
# Executado pelo entrypoint do PostgreSQL antes do servidor aceitar conexões.
# CREATE DATABASE não pode rodar dentro de transação, por isso usamos \gexec.
set -e

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname   "$POSTGRES_DB"   \
     <<-EOSQL
SELECT 'CREATE DATABASE airflow OWNER ${POSTGRES_USER}'
WHERE  NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')
\gexec
EOSQL

echo "  [init] banco 'airflow' pronto."
