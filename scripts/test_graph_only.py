#!/usr/bin/env python3
"""
Test GraphRAG functionality using only Neo4j (without Qdrant).
Demonstrates code parsing, graph loading, and querying.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from databases.neo4j.schema import NodeLabel, RelationType
from databases.neo4j.client import Neo4jClient
from ingestion.parsers.python_parser import PythonParser
from ingestion.loaders.neo4j_loader import Neo4jLoader


# Sample Python code to analyze
SAMPLE_CODE = '''"""Sample module for testing GraphRAG."""

def process_data(data):
    """Process input data through pipeline."""
    cleaned = clean_data(data)
    validated = validate_data(cleaned)
    return transform_data(validated)

def clean_data(data):
    """Remove empty items from data."""
    return [item.strip() for item in data if item]

def validate_data(data):
    """Validate data items."""
    return [item for item in data if len(item) > 0]

def transform_data(data):
    """Transform data to uppercase."""
    return [item.upper() for item in data]

class DataProcessor:
    """Data processing class."""

    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config

    def run(self, data):
        """Execute processing pipeline."""
        return process_data(data)
'''


def print_section(title):
    """Print section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def test_neo4j_connection():
    """Test Neo4j connection."""
    print_section("1. Testing Neo4j Connection")

    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "your-password-here")
        )

        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            value = result.single()["test"]

        driver.close()
        print("✓ Connected to Neo4j successfully")
        return True
    except Exception as e:
        print(f"✗ Neo4j connection failed: {e}")
        return False


def test_parse_code():
    """Parse sample Python code."""
    print_section("2. Parsing Python Code")

    try:
        parser = PythonParser()
        result = parser.parse_string(
            code=SAMPLE_CODE,
            namespace="test_graph",
            file_path="sample.py"
        )

        print(f"✓ Parsed successfully:")
        print(f"  - Modules: {len(result.modules)}")
        print(f"  - Functions: {len(result.functions)}")
        print(f"  - Classes: {len(result.classes)}")
        print(f"  - Methods: {len(result.methods)}")

        print("\n  Functions found:")
        for func in result.functions:
            print(f"    • {func.name}() - {func.docstring[:50] if func.docstring else 'No docs'}...")

        print("\n  Classes found:")
        for cls in result.classes:
            print(f"    • {cls.name} - {cls.docstring[:50] if cls.docstring else 'No docs'}...")

        return result
    except Exception as e:
        print(f"✗ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_load_to_neo4j(parse_result):
    """Load parsed code into Neo4j."""
    print_section("3. Loading Code into Neo4j Graph")

    try:
        neo4j_client = Neo4jClient()
        loader = Neo4jLoader()

        # Load the parsed result
        result = loader.load_parse_result(parse_result)

        print(f"✓ Loaded to Neo4j:")
        print(f"  - Nodes created: {result['nodes_created']}")
        print(f"  - Relationships created: {result['relationships_created']}")

        return neo4j_client
    except Exception as e:
        print(f"✗ Loading failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_query_graph(neo4j_client):
    """Query the graph to demonstrate GraphRAG."""
    print_section("4. Querying the Knowledge Graph")

    namespace = "test_graph"

    # Query 1: Find all functions
    print("\n📊 Query 1: All Functions")
    query = """
    MATCH (f:Function {namespace: $namespace})
    RETURN f.name as name, f.docstring as doc
    ORDER BY f.name
    """
    results = neo4j_client.execute_query(query, {"namespace": namespace})
    for r in results:
        print(f"  • {r['name']}() - {r['doc'][:60] if r['doc'] else 'No docs'}...")

    # Query 2: Find function call relationships
    print("\n📊 Query 2: Function Call Graph")
    query = """
    MATCH (f:Function {namespace: $namespace, name: $name})-[r:CALLS]->(called:Function)
    RETURN f.name as caller, called.name as called
    """
    results = neo4j_client.execute_query(
        query,
        {"namespace": namespace, "name": "process_data"}
    )
    print(f"  process_data() calls:")
    for r in results:
        print(f"    → {r['called']}()")

    # Query 3: Reverse - who calls this function?
    print("\n📊 Query 3: Reverse Dependencies")
    query = """
    MATCH (caller:Function)-[r:CALLS]->(f:Function {namespace: $namespace, name: $name})
    RETURN caller.name as caller
    """
    results = neo4j_client.execute_query(
        query,
        {"namespace": namespace, "name": "clean_data"}
    )
    print(f"  clean_data() is called by:")
    for r in results:
        print(f"    ← {r['caller']}()")

    # Query 4: Find classes and their methods
    print("\n📊 Query 4: Class Structure")
    query = """
    MATCH (c:Class {namespace: $namespace})-[r:CONTAINS]->(m:Method)
    RETURN c.name as class, collect(m.name) as methods
    """
    results = neo4j_client.execute_query(query, {"namespace": namespace})
    for r in results:
        print(f"  class {r['class']}:")
        for method in r['methods']:
            print(f"    • {method}()")

    # Query 5: Find execution flow (process_data pipeline)
    print("\n📊 Query 5: Execution Flow Analysis")
    query = """
    MATCH path = (f:Function {namespace: $namespace, name: $name})-[:CALLS*]->(end)
    WHERE NOT (end)-[:CALLS]->()
    RETURN [node in nodes(path) | node.name] as flow
    LIMIT 5
    """
    results = neo4j_client.execute_query(
        query,
        {"namespace": namespace, "name": "process_data"}
    )
    print(f"  Execution flows from process_data():")
    for i, r in enumerate(results, 1):
        flow = " → ".join(r['flow'])
        print(f"    {i}. {flow}")

    # Query 6: Get complete context for a function
    print("\n📊 Query 6: Complete Function Context")
    query = """
    MATCH (f:Function {namespace: $namespace, name: $name})
    OPTIONAL MATCH (f)-[:CALLS]->(calls:Function)
    OPTIONAL MATCH (calledBy:Function)-[:CALLS]->(f)
    RETURN
        f.name as name,
        f.docstring as doc,
        f.code as code,
        collect(DISTINCT calls.name) as calls,
        collect(DISTINCT calledBy.name) as called_by
    """
    results = neo4j_client.execute_query(
        query,
        {"namespace": namespace, "name": "process_data"}
    )

    if results:
        r = results[0]
        print(f"  Function: {r['name']}()")
        print(f"  Description: {r['doc']}")
        print(f"  Calls: {', '.join(r['calls']) if r['calls'] else 'None'}")
        print(f"  Called by: {', '.join(r['called_by']) if r['called_by'] else 'None'}")
        print(f"\n  Code:")
        for line in r['code'].split('\n')[:5]:
            print(f"    {line}")
        print("    ...")


def cleanup(neo4j_client):
    """Clean up test data."""
    print_section("5. Cleanup")

    try:
        query = "MATCH (n {namespace: 'test_graph'}) DETACH DELETE n"
        neo4j_client.execute_query(query, {})
        print("✓ Cleaned up test data from Neo4j")
    except Exception as e:
        print(f"⚠ Cleanup warning: {e}")


def main():
    """Run the GraphRAG test."""
    print("\n" + "="*70)
    print("  GraphRAG Test - Neo4j Only (No Vector Search)")
    print("="*70)
    print("\nThis demonstrates core GraphRAG functionality:")
    print("  • Code parsing with AST analysis")
    print("  • Graph knowledge base construction")
    print("  • Relationship-based querying")
    print("  • Execution flow analysis")

    # Step 1: Test connection
    if not test_neo4j_connection():
        print("\n❌ Cannot connect to Neo4j. Make sure it's running:")
        print("   docker compose up -d neo4j")
        return 1

    # Step 2: Parse code
    parse_result = test_parse_code()
    if not parse_result:
        return 1

    # Step 3: Load to Neo4j
    neo4j_client = test_load_to_neo4j(parse_result)
    if not neo4j_client:
        return 1

    # Step 4: Query the graph
    try:
        test_query_graph(neo4j_client)
    except Exception as e:
        print(f"\n✗ Query failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 5: Cleanup
    cleanup(neo4j_client)

    print("\n" + "="*70)
    print("  ✓ GraphRAG Test Complete!")
    print("="*70)
    print("\n💡 Key Takeaways:")
    print("  • Parsed Python code and extracted structure")
    print("  • Built knowledge graph in Neo4j")
    print("  • Queried relationships (calls, dependencies)")
    print("  • Analyzed execution flows")
    print("  • Retrieved contextual information")
    print("\nThis is the foundation of GraphRAG - combining code")
    print("understanding with graph-based retrieval!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
