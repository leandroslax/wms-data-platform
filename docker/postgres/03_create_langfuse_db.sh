#!/usr/bin/env bash
# Cria o banco de dados 'langfuse' para o LangFuse self-hosted.
# Executado pelo entrypoint do PostgreSQL antes do servidor aceitar conexões.
set -e

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname   "$POSTGRES_DB"   \
     <<-EOSQL
SELECT 'CREATE DATABASE langfuse OWNER ${POSTGRES_USER}'
WHERE  NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langfuse')
\gexec
EOSQL

echo "  [init] banco 'langfuse' pronto."
