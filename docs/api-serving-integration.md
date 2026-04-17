# API Serving Integration

## Objetivo
Documentar como a API do WMS Data Platform deve evoluir da camada mockada atual para o serving analítico real.

## Estado atual
A API está organizada em:
- routes
- schemas
- services
- data access

Neste momento:
- as rotas já representam o contrato do MVP
- os schemas já representam o payload esperado
- os services encapsulam a lógica de aplicação
- o `DataAccessService` ainda retorna dados mockados

## Motivo da abordagem atual
Essa abordagem permite:
- estabilizar o contrato da API antes do backend analítico final
- desenvolver em paralelo com infra, dbt e ingestão
- reduzir acoplamento prematuro
- deixar a transição para Redshift mais simples

## Camadas da API

### Routes
Responsáveis por:
- expor endpoints HTTP
- receber requests
- devolver responses validadas

### Schemas
Responsáveis por:
- definir contratos de resposta
- validar o payload exposto ao cliente

### Services
Responsáveis por:
- encapsular regra de aplicação
- orquestrar a chamada à camada de acesso a dados

### DataAccessService
Responsável por:
- centralizar a leitura analítica
- esconder detalhes de query
- permitir troca de backend sem alterar rotas

## Estratégia de evolução
A evolução esperada é:

1. manter o contrato atual dos endpoints
2. manter os métodos públicos do `DataAccessService`
3. substituir a implementação mockada por consultas reais
4. conectar essa implementação ao Redshift
5. adicionar tratamento de erro, timeout e observabilidade

## Métodos atuais da camada de acesso
- `fetch_orders_summary()`
- `fetch_inventory_snapshot()`
- `fetch_movements_summary()`

## Contrato futuro
Cada método deve:
- executar consulta em marts analíticos
- retornar payload compatível com os schemas atuais
- registrar contexto de erro
- manter previsibilidade de resposta

## Benefício arquitetural
Essa separação permite:
- plugar Redshift depois
- criar testes por camada
- trocar backend sem reescrever endpoints
- manter clareza para entrevista técnica

## Próximos passos
1. criar camada de configuração para conexão analítica
2. preparar adapter futuro para Redshift
3. implementar queries reais quando a camada de serving estiver pronta
4. adicionar testes para a camada de serviços
