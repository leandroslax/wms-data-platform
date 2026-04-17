# WMS Data Platform MVP Scope

## Objetivo
Definir o escopo mínimo viável da primeira versão funcional da plataforma de dados WMS.

## Decisão
O MVP será construído sobre 3 entidades principais:

- Orders
- Inventory
- Movements

## Justificativa
Essas 3 entidades oferecem o melhor equilíbrio entre:
- valor analítico
- clareza arquitetural
- facilidade de explicação em entrevista
- utilidade para API, dashboards e agentes

## O que entra no MVP

### 1. Orders
Casos de uso:
- volume de pedidos
- status operacionais
- atraso e throughput
- análise por produto

### 2. Inventory
Casos de uso:
- saldo disponível
- estoque alocado
- posição por local
- monitoramento de disponibilidade

### 3. Movements
Casos de uso:
- rastreabilidade operacional
- entradas, saídas e transferências
- análise de fluxo no armazém
- suporte a produtividade e gargalos

## O que fica fora do MVP inicial
Estas entidades continuam no roadmap, mas não bloqueiam a primeira entrega:
- Operators
- Tasks
- Master Data completo
- camada RAG completa
- agentes multi-step mais avançados
- dashboards executivos completos
- serving avançado no Redshift

## Entregáveis do MVP

### Infraestrutura
- backend remoto Terraform
- S3 bronze/silver/gold
- Secrets Manager
- KMS
- ECR
- Lambda base
- monitoring essencial

### Pipeline
- extractor para Orders
- extractor para Inventory
- extractor para Movements
- persistência bronze
- padronização silver

### Transformação
- stg_orders
- stg_inventory
- stg_movements
- fct_orders
- fct_inventory_snapshot
- fct_movements

### Serving
- base para API FastAPI
- consultas analíticas iniciais
- contrato para futura exposição via agentes

## Critérios de pronto do MVP
- as 3 entidades estão mapeadas da origem até silver/gold
- os artefatos Terraform principais aplicam com sucesso
- existe imagem publicada no ECR
- Lambdas base sobem sem erro
- dbt possui staging e marts iniciais
- documentação explica claramente o fluxo fim a fim

## Próximos passos após o MVP
1. adicionar Operators e Tasks
2. enriquecer dimensões de produto e localização
3. conectar serving analítico ao Redshift
4. adicionar RAG com runbooks
5. ativar agentes de análise e relatório
