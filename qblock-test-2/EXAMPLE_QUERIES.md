# FlowRAG Example Queries for QBlock

## Single Service Queries

### Query 1: Find a specific class
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the OrderService class and what does it do?",
    "namespace": "qblock-mobile"
  }' | jq '.answer'
```

### Query 2: Understand a function
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does fetchOrders work?",
    "namespace": "qblock-mobile"
  }' | jq '.answer'
```

### Query 3: Find usage patterns
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Where is ShopifyService used?",
    "namespace": "qblock-shop-data"
  }' | jq '.answer'
```

## Cross-Service Queries

### Query 4: End-to-end order flow
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does OMS get orders from Shopify?",
    "namespace": "qblock-mobile",
    "include_cross_service": true
  }' | jq '.answer'
```

### Query 5: Label creation process
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does the label creation process work from mobile app to label service?",
    "namespace": "qblock-mobile",
    "include_cross_service": true
  }' | jq '.answer'
```

### Query 6: Authentication flow
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does the mobile app authenticate with shop credentials?",
    "namespace": "qblock-mobile",
    "include_cross_service": true
  }' | jq '.answer'
```

### Query 7: Cross-service data flow
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What happens when ShopDataProvider fetches Etsy orders?",
    "namespace": "qblock-shop-data",
    "include_cross_service": true
  }' | jq '.answer'
```

## Advanced Queries

### Query 8: With flow analysis
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the complete checkout flow?",
    "namespace": "qblock-mobile",
    "include_flow_analysis": true,
    "include_cross_service": true
  }' | jq '.'
```

### Query 9: High token context for complex queries
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain the entire order management architecture",
    "namespace": "qblock-mobile",
    "include_cross_service": true,
    "max_context_tokens": 8000,
    "max_results": 20
  }' | jq '.answer'
```

## Response Structure

```json
{
  "answer": "The generated response from LLM...",
  "query": "Original query",
  "intent": "SEMANTIC",
  "intent_confidence": 0.85,
  "context_items": [
    {
      "content": "Code or documentation content",
      "source_type": "code",
      "relevance_score": 0.92,
      "citation": "qblock-mobile:OrderService",
      "metadata": {
        "file_path": "/path/to/file.dart",
        "line_start": 42
      }
    }
  ],
  "sources_count": 5,
  "flow_analysis": null,
  "model": "gpt-4",
  "tokens_used": 1250,
  "retrieval_time": 0.45,
  "total_time": 2.31
}
```

## Testing Commands

### Check API Health
```bash
curl http://localhost:8000/health
```

### List Available Namespaces (via Neo4j)
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "List all available services",
    "namespace": "qblock-mobile"
  }'
```

### Streaming Response
```bash
curl -X POST http://localhost:8000/api/v1/query/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does OrderService work?",
    "namespace": "qblock-mobile"
  }'
```

## Python Client Example

```python
import requests

def query_flowrag(question: str, namespace: str, cross_service: bool = False):
    response = requests.post(
        "http://localhost:8000/api/v1/query",
        json={
            "query": question,
            "namespace": namespace,
            "include_cross_service": cross_service,
            "max_results": 10
        }
    )
    result = response.json()
    return result["answer"]

# Single service query
answer = query_flowrag(
    "What does OrderService do?",
    "qblock-mobile"
)
print(answer)

# Cross-service query
answer = query_flowrag(
    "How does OMS get orders from Shopify?",
    "qblock-mobile",
    cross_service=True
)
print(answer)
```
