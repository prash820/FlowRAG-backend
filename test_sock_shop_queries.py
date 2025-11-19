"""
Test FlowRAG queries against Sock Shop architecture.
Validates that FlowRAG can accurately answer questions about the ingested codebase.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases.neo4j.client import Neo4jClient
import json

# Test queries based on SOCK_SHOP_ARCHITECTURE.md
TEST_QUERIES = [
    {
        "id": 1,
        "question": "What services are in the Sock Shop architecture?",
        "cypher": """
            MATCH (n {namespace: "sock_shop"})
            WITH DISTINCT n.file_path as path
            WITH split(path, '/') as parts
            WITH parts[size(parts)-3] as service
            WHERE service IS NOT NULL AND service <> ''
            RETURN DISTINCT service
            ORDER BY service
        """,
        "expected": ["catalogue", "front-end", "payment", "user"],
        "type": "list"
    },
    {
        "id": 2,
        "question": "What language is the payment service written in?",
        "cypher": """
            MATCH (n {namespace: "sock_shop"})
            WHERE n.file_path CONTAINS 'payment/'
            RETURN DISTINCT n.language as language
            LIMIT 1
        """,
        "expected": "go",
        "type": "value"
    },
    {
        "id": 3,
        "question": "How many functions are in the payment service?",
        "cypher": """
            MATCH (n {namespace: "sock_shop"})
            WHERE n.file_path CONTAINS 'payment/'
            AND n.type IN ['Function', 'Method']
            RETURN count(n) as count
        """,
        "expected_min": 15,
        "type": "count"
    },
    {
        "id": 4,
        "question": "What structs/classes exist in the catalogue service?",
        "cypher": """
            MATCH (n:Class {namespace: "sock_shop"})
            WHERE n.file_path CONTAINS 'catalogue/'
            RETURN n.name as name
            ORDER BY name
        """,
        "expected_min": 5,
        "type": "list"
    },
    {
        "id": 5,
        "question": "What are the main Go files in the payment service?",
        "cypher": """
            MATCH (n {namespace: "sock_shop"})
            WHERE n.file_path CONTAINS 'payment/'
            AND n.language = 'go'
            WITH DISTINCT split(n.file_path, '/')[-1] as filename
            RETURN filename
            ORDER BY filename
        """,
        "expected": ["endpoints.go", "logging.go", "service.go", "transport.go", "wiring.go"],
        "type": "list"
    },
    {
        "id": 6,
        "question": "What functions are in transport.go of the payment service?",
        "cypher": """
            MATCH (n {namespace: "sock_shop"})
            WHERE n.file_path CONTAINS 'payment/transport.go'
            AND n.type IN ['Function', 'Method']
            RETURN n.name as function_name, n.line_start as line
            ORDER BY line
        """,
        "expected_min": 6,
        "type": "list"
    },
    {
        "id": 7,
        "question": "How many code units were extracted from the user service?",
        "cypher": """
            MATCH (n {namespace: "sock_shop"})
            WHERE n.file_path CONTAINS 'user/'
            RETURN count(n) as total_units
        """,
        "expected_min": 50,
        "type": "count"
    },
    {
        "id": 8,
        "question": "What JavaScript files are in the front-end service?",
        "cypher": """
            MATCH (n {namespace: "sock_shop", language: "javascript"})
            WITH DISTINCT split(n.file_path, '/')[-1] as filename
            WHERE filename ENDS WITH '.js'
            RETURN filename
            ORDER BY filename
            LIMIT 10
        """,
        "expected_min": 5,
        "type": "list"
    },
    {
        "id": 9,
        "question": "Show me functions that have 'New' in their name (constructors)",
        "cypher": """
            MATCH (n {namespace: "sock_shop"})
            WHERE n.name STARTS WITH 'New' OR n.name STARTS WITH 'new'
            RETURN n.name as name, n.language as language, split(n.file_path, '/')[-1] as file
            ORDER BY name
            LIMIT 10
        """,
        "expected_min": 3,
        "type": "list"
    },
    {
        "id": 10,
        "question": "What is the total count of all code units ingested?",
        "cypher": """
            MATCH (n {namespace: "sock_shop"})
            RETURN count(n) as total
        """,
        "expected_min": 100,  # Should be much more based on our parser tests
        "type": "count"
    }
]


def run_query(client, test):
    """Run a single test query and validate results."""
    print(f"\n{'='*80}")
    print(f"Query {test['id']}: {test['question']}")
    print(f"{'='*80}")
    print(f"Cypher:\n{test['cypher']}")

    try:
        result = client.execute_query(test['cypher'], {})

        if test['type'] == 'value':
            # Single value expected
            if result and len(result) > 0:
                actual = result[0][list(result[0].keys())[0]]
                expected = test['expected']
                status = "✅ PASS" if actual == expected else "❌ FAIL"
                print(f"\nResult: {actual}")
                print(f"Expected: {expected}")
                print(f"Status: {status}")
                return actual == expected
            else:
                print(f"\n❌ FAIL: No results returned")
                return False

        elif test['type'] == 'count':
            # Count comparison
            if result and len(result) > 0:
                actual = result[0][list(result[0].keys())[0]]
                expected_min = test.get('expected_min', 0)
                status = "✅ PASS" if actual >= expected_min else "❌ FAIL"
                print(f"\nResult: {actual}")
                print(f"Expected (minimum): {expected_min}")
                print(f"Status: {status}")
                return actual >= expected_min
            else:
                print(f"\n❌ FAIL: No results returned")
                return False

        elif test['type'] == 'list':
            # List of results
            if 'expected' in test:
                # Exact list match
                actual = [row[list(row.keys())[0]] for row in result]
                expected = test['expected']
                # Check if all expected items are in actual
                matches = all(item in actual for item in expected)
                status = "✅ PASS" if matches else "⚠️ PARTIAL"
                print(f"\nResults ({len(actual)} items):")
                for item in actual[:10]:
                    print(f"  - {item}")
                if len(actual) > 10:
                    print(f"  ... and {len(actual) - 10} more")
                print(f"\nExpected items: {expected}")
                print(f"All expected found: {matches}")
                print(f"Status: {status}")
                return matches
            else:
                # Just check minimum count
                expected_min = test.get('expected_min', 0)
                actual_count = len(result)
                status = "✅ PASS" if actual_count >= expected_min else "❌ FAIL"
                print(f"\nResults ({actual_count} items):")
                for row in result[:10]:
                    print(f"  - {row}")
                if actual_count > 10:
                    print(f"  ... and {actual_count - 10} more")
                print(f"\nExpected (minimum): {expected_min}")
                print(f"Status: {status}")
                return actual_count >= expected_min

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def main():
    """Run all test queries and generate report."""
    print("="*80)
    print("SOCK SHOP FLOWRAG TESTING")
    print("="*80)
    print("\nConnecting to Neo4j...")

    client = Neo4jClient()
    client.connect()

    print("✅ Connected!\n")

    # Run all queries
    results = []
    for test in TEST_QUERIES:
        passed = run_query(client, test)
        results.append({
            "id": test["id"],
            "question": test["question"],
            "passed": passed
        })

    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"\nTotal Queries: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Pass Rate: {pass_rate:.1f}%")

    print(f"\n{'='*80}")
    print("DETAILED RESULTS")
    print(f"{'='*80}")
    for r in results:
        status = "✅ PASS" if r['passed'] else "❌ FAIL"
        print(f"{status} | Q{r['id']}: {r['question']}")

    print(f"\n{'='*80}")

    # Save results
    with open('sock_shop_query_results.json', 'w') as f:
        json.dump({
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": pass_rate
            },
            "results": results
        }, f, indent=2)

    print(f"\n✅ Results saved to sock_shop_query_results.json")

    client.close()

    return pass_rate >= 80  # Return success if 80%+ pass rate


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
