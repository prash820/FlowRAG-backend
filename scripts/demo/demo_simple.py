"""
Simple FlowRAG Demo - Standalone version
Shows what services are running and provides sample API calls
"""
import httpx
from qdrant_client import QdrantClient
from neo4j import GraphDatabase

def check_services():
    """Check if all services are accessible"""
    print("\n🔍 Checking FlowRAG Services...\n")

    services = {
        "Neo4j": {"url": "bolt://localhost:7687", "status": "❌"},
        "Qdrant": {"url": "http://localhost:6333", "status": "❌"},
        "Redis": {"url": "localhost:6379", "status": "❌"}
    }

    # Check Neo4j
    try:
        driver = GraphDatabase.driver(
            services["Neo4j"]["url"],
            auth=("neo4j", "your-password-here")
        )
        driver.verify_connectivity()
        services["Neo4j"]["status"] = "✅"
        driver.close()
    except Exception as e:
        services["Neo4j"]["error"] = str(e)[:50]

    # Check Qdrant
    try:
        client = QdrantClient(host="localhost", port=6333, timeout=5)
        client.get_collections()
        services["Qdrant"]["status"] = "✅"
    except Exception as e:
        services["Qdrant"]["error"] = str(e)[:50]

    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2)
        r.ping()
        services["Redis"]["status"] = "✅"
    except:
        try:
            # If redis package not installed, just check if port is open
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 6379))
            if result == 0:
                services["Redis"]["status"] = "✅ (port open)"
            sock.close()
        except Exception as e:
            services["Redis"]["error"] = str(e)[:50]

    # Print status
    for name, info in services.items():
        status = info["status"]
        url = info["url"]
        print(f"{status} {name:10} - {url}")
        if "error" in info:
            print(f"          Error: {info['error']}")

    all_up = all(info["status"].startswith("✅") for info in services.values())

    if all_up:
        print("\n✨ All services are running!\n")
        demo_features()
    else:
        print("\n⚠️  Some services are down. Please start them with:")
        print("   docker start flowrag-neo4j flowrag-qdrant flowrag-redis\n")

def demo_features():
    """Show what features are available"""
    print("=" * 60)
    print("📊 FlowRAG DEMO - What's Ready")
    print("=" * 60)

    features = {
        "✅ Infrastructure": [
            "Neo4j graph database (for code relationships)",
            "Qdrant vector database (for semantic search)",
            "Redis cache (for performance)"
        ],
        "✅ Parsers": [
            "Python AST parser (ingestion/parsers/python_parser.py)",
            "JavaScript parser (ingestion/parsers/javascript_parser.py)",
            "tree-sitter multi-language support (40+ languages)"
        ],
        "✅ Flow Analysis": [
            "Parallel group detection (orchestrator/flow/flow_analyzer.py)",
            "Critical path calculation",
            "Speedup estimation",
            "Dependency graph builder"
        ],
        "✅ Database Clients": [
            "Neo4j client with full CRUD (databases/neo4j/client.py)",
            "Qdrant client with vector search (databases/qdrant/client.py)",
            "Schema management & migrations"
        ],
        "⚠️  Missing (MVP Day 1)": [
            "Call graph extraction - returns empty [] (python_parser.py:346)",
            "This is THE critical feature we need to implement first!"
        ],
        "🚀 UI Available": [
            "Web interface at ui/app.py",
            "Semantic search endpoint",
            "Flow visualization endpoint",
            "LLM-powered code explanations"
        ]
    }

    for category, items in features.items():
        print(f"\n{category}")
        for item in items:
            print(f"  • {item}")

    print("\n" + "=" * 60)
    print("📝 NEXT STEPS")
    print("=" * 60)
    print("""
To see a working demo with real data:

1. Fix call graph extraction (MVP Day 1, Task 1.1):
   - Open: ingestion/parsers/python_parser.py
   - Find line 346: def _extract_calls()
   - Implement AST visitor pattern to extract function calls

2. Ingest a sample project:
   - python3 scripts/ingest_codebase.py /path/to/code

3. Start the UI:
   - python3 ui/app.py
   - Visit: http://localhost:8000

4. Query the system:
   - Semantic search: "How does authentication work?"
   - Flow analysis: "Show me the pipeline execution flow"
    """)

    print("\n🎯 Current Status: Infrastructure 80% complete!")
    print("   Just need to fill in call graph extraction + UI polish")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_services()
