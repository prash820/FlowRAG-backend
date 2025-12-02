# QBlock Service Dependency Graph

## Visual Representation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           QBLOCK PLATFORM ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────────┐
                              │   qblock-mobile      │
                              │ (OrderManagementSystem)│
                              │    Flutter App       │
                              │    185 nodes         │
                              └──────────┬───────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  qblock-shop-data   │    │ qblock-label-service│    │ qblock-auth-service │
│ (ShopDataProvider)  │    │(LabelCreationOrch.) │    │  (ShopKeyProvider)  │
│  Next.js/TypeScript │    │     TypeScript      │    │  Next.js/TypeScript │
│    146 nodes        │    │      49 nodes       │    │      32 nodes       │
└─────────┬───────────┘    └─────────────────────┘    └─────────────────────┘
          │                          ▲
          │                          │
          └──────────────────────────┘
                  (1 API call)


┌─────────────────────┐    ┌─────────────────────┐
│qblock-transaction-  │    │   qblock-metrics    │
│       data          │    │    (MetricsJs)      │
│(TransactionDataProv)│    │    JavaScript       │
│    JavaScript       │    │      5 nodes        │
│     15 nodes        │    │                     │
│   [STANDALONE]      │    │   [STANDALONE]      │
└─────────────────────┘    └─────────────────────┘
          │
          ▼
   ┌──────────────┐
   │  Etsy APIs   │
   │ (External)   │
   └──────────────┘
```

## CALLS_API Relationships in Neo4j

### qblock-mobile → qblock-shop-data (2 calls)

| Source | Target URL | Method |
|--------|------------|--------|
| OrderService | shopdataprovider.app.runonflux.io/api/getAllPendingOrders | GET |
| OrderService | shopdataprovider.app.runonflux.io/api/orders | GET |

### qblock-mobile → qblock-label-service (1 call)

| Source | Target URL | Method |
|--------|------------|--------|
| LabelService | labelcreationorchestrator.app.runonflux.io/api/shipping | POST |

### qblock-mobile → qblock-auth-service (1 call)

| Source | Target URL | Method |
|--------|------------|--------|
| ShopKeyProvider | shopkeyprovider.app.runonflux.io/api/shop-credentials | GET |

### qblock-shop-data → qblock-label-service (1 call)

| Source | Target URL | Method |
|--------|------------|--------|
| getAllPendingOrders | labelcreationorchestrator.app.runonflux.io/api/shipping/shipments | POST |

## Cypher Query to View All Relationships

```cypher
-- View all cross-service relationships
MATCH (source)-[r:CALLS_API]->(target)
RETURN source.namespace as from_service,
       source.name as from_class,
       r.target_url as api_endpoint,
       r.http_method as method,
       target.namespace as to_service
ORDER BY from_service
```

## Service Communication Patterns

### Pattern 1: Mobile → Backend
```
OMS App → ShopDataProvider → External APIs (Shopify/Etsy)
```

### Pattern 2: Mobile → Label Service
```
OMS App → LabelCreationOrchestrator → Shipping Providers
```

### Pattern 3: Backend → Backend
```
ShopDataProvider → LabelCreationOrchestrator (for Etsy order shipping info)
```

### Pattern 4: Mobile → Auth
```
OMS App → ShopKeyProvider (for API credentials)
```

## Node Counts by Type

| Namespace | Classes | Functions | Total |
|-----------|---------|-----------|-------|
| qblock-mobile | ~50 | ~135 | 185 |
| qblock-shop-data | ~40 | ~106 | 146 |
| qblock-label-service | ~15 | ~34 | 49 |
| qblock-auth-service | ~10 | ~22 | 32 |
| qblock-transaction-data | ~5 | ~10 | 15 |
| qblock-metrics | ~2 | ~3 | 5 |

## URL Mapping Configuration

The following URL patterns are used to detect cross-service calls:

```json
{
  "shopdataprovider.app.runonflux.io": "qblock-shop-data",
  "labelcreationorchestrator.app.runonflux.io": "qblock-label-service",
  "shopkeyprovider.app.runonflux.io": "qblock-auth-service",
  "transactiondataprovider.app.runonflux.io": "qblock-transaction-data",
  "metricsjs.app.runonflux.io": "qblock-metrics"
}
```
