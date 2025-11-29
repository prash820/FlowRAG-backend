#!/bin/bash
# QBlock Platform - Sequential Ingestion WITH Documentation
# This ingests code + generates and stores documentation chunks as vectors

echo "🚀 Starting QBlock Platform Ingestion (6 services)"
echo "Features: Code parsing + Documentation generation + Vector storage"
echo "=================================================================="

# Service 1: OrderManagementSystem (Flutter/Dart)
echo ""
echo "[1/6] qblock-mobile (Flutter app)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/OrderManagementSystem",
    "namespace": "qblock-mobile",
    "recursive": true,
    "file_patterns": ["*.dart"],
    "generate_documentation": true
  }' | python3 -c "import json, sys; d=json.load(sys.stdin); print(f'  ✓ Files:{d.get(\"files_processed\",0)} Nodes:{d.get(\"nodes_created\",0)} Vectors:{d.get(\"vectors_stored\",0)} Time:{d.get(\"processing_time\",0):.1f}s')"

# Service 2: LabelCreationOrchestrator (TypeScript)
echo ""
echo "[2/6] qblock-label-service (Label service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/LabelCreationOrchestrator",
    "namespace": "qblock-label-service",
    "recursive": true,
    "file_patterns": ["*.ts", "*.js"],
    "generate_documentation": true
  }' | python3 -c "import json, sys; d=json.load(sys.stdin); print(f'  ✓ Files:{d.get(\"files_processed\",0)} Nodes:{d.get(\"nodes_created\",0)} Vectors:{d.get(\"vectors_stored\",0)} Time:{d.get(\"processing_time\",0):.1f}s')"

# Service 3: ShopKeyProvider (Next.js/TypeScript)
echo ""
echo "[3/6] qblock-auth-service (Auth service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/ShopKeyProvider",
    "namespace": "qblock-auth-service",
    "recursive": true,
    "file_patterns": ["*.ts", "*.tsx", "*.js"],
    "generate_documentation": true
  }' | python3 -c "import json, sys; d=json.load(sys.stdin); print(f'  ✓ Files:{d.get(\"files_processed\",0)} Nodes:{d.get(\"nodes_created\",0)} Vectors:{d.get(\"vectors_stored\",0)} Time:{d.get(\"processing_time\",0):.1f}s')"

# Service 4: ShopDataProvider (TypeScript)
echo ""
echo "[4/6] qblock-shop-data (Shop data service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/ShopDataProvider",
    "namespace": "qblock-shop-data",
    "recursive": true,
    "file_patterns": ["*.ts", "*.js"],
    "generate_documentation": true
  }' | python3 -c "import json, sys; d=json.load(sys.stdin); print(f'  ✓ Files:{d.get(\"files_processed\",0)} Nodes:{d.get(\"nodes_created\",0)} Vectors:{d.get(\"vectors_stored\",0)} Time:{d.get(\"processing_time\",0):.1f}s')"

# Service 5: TransactionDataProvider (TypeScript)
echo ""
echo "[5/6] qblock-transaction-data (Transaction service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/TransactionDataProvider",
    "namespace": "qblock-transaction-data",
    "recursive": true,
    "file_patterns": ["*.ts", "*.js"],
    "generate_documentation": true
  }' | python3 -c "import json, sys; d=json.load(sys.stdin); print(f'  ✓ Files:{d.get(\"files_processed\",0)} Nodes:{d.get(\"nodes_created\",0)} Vectors:{d.get(\"vectors_stored\",0)} Time:{d.get(\"processing_time\",0):.1f}s')"

# Service 6: MetricsJs (JavaScript)
echo ""
echo "[6/6] qblock-metrics (Metrics service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/MetricsJs",
    "namespace": "qblock-metrics",
    "recursive": true,
    "file_patterns": ["*.js", "*.ts"],
    "generate_documentation": true
  }' | python3 -c "import json, sys; d=json.load(sys.stdin); print(f'  ✓ Files:{d.get(\"files_processed\",0)} Nodes:{d.get(\"nodes_created\",0)} Vectors:{d.get(\"vectors_stored\",0)} Time:{d.get(\"processing_time\",0):.1f}s')"

echo ""
echo "=================================================================="
echo "✅ QBlock platform ingestion complete!"
echo ""
echo "Next step: Build cross-service relationships"
echo "  cd flowrag-master && ./venv/bin/python3 ../build_service_relationships.py --config ../qblock_service_mappings.json"
