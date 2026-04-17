# Redshift Adapter Plan

## Objetivo
Definir a estratégia de implementação futura do adapter Redshift para a API do WMS Data Platform.

## Papel do adapter
O adapter Redshift será responsável por:
- encapsular a comunicação com o backend analítico
- executar consultas de serving
- devolver payloads compatíveis com o contrato da API
- isolar detalhes de infraestrutura da camada de aplicação

## Estado atual
O adapter existe apenas como contrato técnico:
- `app/api/adapters/redshift_adapter.py`

Neste momento:
- não existe conexão ativa
- não existe driver configurado
- não existem queries reais em execução
- a API continua servindo mocks via `DataAccessService`

## Motivo dessa preparação
Criar o adapter antes da conexão real permite:
- consolidar a arquitetura da aplicação
- separar responsabilidades
- facilitar testes futuros
- preparar a transição para serving real sem retrabalho estrutural

## Responsabilidades futuras do adapter
- abrir conexão segura com Redshift
- executar queries analíticas
- tratar erros de consulta
- padronizar payloads de retorno
- emitir sinais de observabilidade

## Métodos esperados
- `fetch_orders_summary()`
- `fetch_inventory_snapshot()`
- `fetch_movements_summary()`

## Dependências futuras esperadas
A implementação real pode exigir:
- driver Python compatível com Redshift
- credenciais vindas de Secrets Manager
- configuração de host, porta, database, schema e usuário
- política de timeout
- tratamento explícito de exceções

## Regras de implementação
- não colocar SQL diretamente nas rotas
- manter compatibilidade com schemas atuais
- concentrar a lógica de acesso no adapter
- permitir troca futura de backend se necessário

## Estratégia de adoção
A transição esperada será:

1. manter `DataAccessService` como fachada
2. adicionar modo configurável de backend
3. conectar `RedshiftAdapter`
4. trocar a implementação mockada por consulta real
5. validar contrato dos endpoints sem alterar as rotas

## Próximos passos
1. criar camada de configuração analítica
2. definir estratégia de credenciais
3. implementar queries reais no adapter
4. conectar o adapter ao `DataAccessService`
5. adicionar testes de integração
