# Oracle WMS Entities

## Core transactional entities

- `orders`: outbound and inbound order headers and lifecycle milestones
- `inventory`: on-hand stock by SKU, lot, location, and warehouse
- `movements`: stock movements between bins, docks, and process states
- `tasks`: operational work items such as picking, putaway, replenishment, counting
- `operators`: workforce metadata and productivity attribution

## Low-volatility reference data

- `master_data`: SKU, customer, supplier, carrier, location, and warehouse reference tables

## Modeling rule

Bronze keeps source fidelity. Silver normalizes types and grain. Gold answers operational and executive questions.
