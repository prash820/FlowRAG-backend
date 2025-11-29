#!/bin/bash
# QBlock Platform - Sequential Ingestion (one service at a time)

echo "Starting QBlock platform ingestion (6 services)..."
echo "=================================================="

# 1. OrderManagementSystem (Flutter/Dart)
echo ""
echo "[1/6] Ingesting OrderManagementSystem (Flutter mobile app)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/OrderManagementSystem",
    "namespace": "qblock-mobile",
    "recursive": true,
    "file_patterns": ["*.dart"],
    "generate_documentation": true
  }' | python3 -m json.tool

# 2. LabelCreationOrchestrator (TypeScript)
echo ""
echo "[2/6] Ingesting LabelCreationOrchestrator (Label service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/LabelCreationOrchestrator",
    "namespace": "qblock-label-service",
    "recursive": true,
    "file_patterns": ["*.ts", "*.js"],
    "generate_documentation": true
  }' | python3 -m json.tool

# 3. ShopKeyProvider (Next.js/TypeScript)
echo ""
echo "[3/6] Ingesting ShopKeyProvider (Auth service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/ShopKeyProvider",
    "namespace": "qblock-auth-service",
    "recursive": true,
    "file_patterns": ["*.ts", "*.tsx", "*.js"],
    "generate_documentation": true
  }' | python3 -m json.tool

# 4. ShopDataProvider (TypeScript)
echo ""
echo "[4/6] Ingesting ShopDataProvider (Shop data service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/ShopDataProvider",
    "namespace": "qblock-shop-data",
    "recursive": true,
    "file_patterns": ["*.ts", "*.js"],
    "generate_documentation": true
  }' | python3 -m json.tool

# 5. TransactionDataProvider (TypeScript)
echo ""
echo "[5/6] Ingesting TransactionDataProvider (Transaction service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/TransactionDataProvider",
    "namespace": "qblock-transaction-data",
    "recursive": true,
    "file_patterns": ["*.ts", "*.js"],
    "generate_documentation": true
  }' | python3 -m json.tool

# 6. MetricsJs (JavaScript)
echo ""
echo "[6/6] Ingesting MetricsJs (Metrics service)..."
curl -s -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/Users/prashanthboovaragavan/Documents/workspace/qblock/MetricsJs",
    "namespace": "qblock-metrics",
    "recursive": true,
    "file_patterns": ["*.js", "*.ts"],
    "generate_documentation": true
  }' | python3 -m json.tool

echo ""
echo "=================================================="
echo "QBlock platform ingestion complete!"
