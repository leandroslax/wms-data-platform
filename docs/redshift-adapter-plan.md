# PostgreSQL Adapter Plan

## Objetivo
Definir a estratégia de implementação do adapter PostgreSQL para a API do WMS Data Platform.

## Papel do adapter
O adapter PostgreSQL será responsável por:
- encapsular a comunicação com o backend analítico
- executar consultas de serving no schema `gold`
- devolver payloads compatíveis com o contrato da API
- isolar detalhes de infraestrutura da camada de aplicação

## Estado atual
O adapter existe como contrato técnico:
- `app/api/adapters/postgres_adapter.py`

Neste momento:
- conexão configurada via variáveis de ambiente
- queries implementadas por endpoint do MVP
- a API serve dados reais do schema `gold`

## Responsabilidades do adapter
- abrir conexão com PostgreSQL via psycopg2 ou asyncpg
- executar queries analíticas no schema `gold`
- tratar erros de consulta
- padronizar payloads de retorno
- emitir sinais de observabilidade

## Métodos esperados
- `fetch_orders_summary()`
- `fetch_inventory_snapshot()`
- `fetch_movements_summary()`

## Dependências
- psycopg2 ou asyncpg
- configuração via variáveis de ambiente (`.env`)
- host, porta, database, schema, usuário, senha

## Regras de implementação
- não colocar SQL diretamente nas rotas
- manter compatibilidade com schemas atuais
- concentrar a lógica de acesso no adapter
- permitir troca futura de backend se necessário

## Estratégia de adoção
A transição esperada será:

1. manter `DataAccessService` como fachada
2. adapter recebe configuração via `settings`
3. adapter executa consultas reais no gold
4. `DataAccessService` delega ao adapter
5. rotas não precisam de alteração

## Próximos passos
1. confirmar schema `gold` populado pelo dbt
2. implementar queries reais no adapter
3. conectar o adapter ao `DataAccessService`
4. adicionar testes de integração
