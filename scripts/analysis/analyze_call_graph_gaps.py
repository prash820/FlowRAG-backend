#!/usr/bin/env python3
"""
Analyze Call Graph Gaps

Identifies what SHOULD be connected but ISN'T in the call graph.
This helps us understand what's missing and verify flow tracking capability.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases.neo4j.client import Neo4jClient
from dotenv import load_dotenv
import re

load_dotenv()


def print_header(text):
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)


def analyze_calls_field_vs_relationships(client):
    """Compare 'calls' field content vs actual CALLS relationships."""
    print_header("Calls Field vs CALLS Relationships")

    query = """
    MATCH (n)
    WHERE n.namespace = 'sock_shop:payment'
    AND n.type IN ['Function', 'Method']
    AND n.calls IS NOT NULL
    RETURN n.name as function, n.file_path as file, n.calls as calls_field
    ORDER BY n.name
    """

    results = client.execute_query(query, {})

    print(f"\nFound {len(results)} functions with 'calls' field populated:")

    total_calls_in_field = 0
    total_relationships = 0

    for r in results:
        file_name = Path(r['file']).name if r['file'] else 'unknown'
        calls = r['calls_field'] or []

        # Count how many of these calls have relationships
        rel_query = """
        MATCH (a {name: $name, namespace: 'sock_shop:payment'})-[:CALLS]->(b)
        RETURN count(b) as rel_count
        """

        rel_result = client.execute_query(rel_query, {"name": r['function']})
        rel_count = rel_result[0]['rel_count']

        total_calls_in_field += len(calls)
        total_relationships += rel_count

        status = "✅" if rel_count > 0 else "❌"
        print(f"\n{status} {r['function']} ({file_name})")
        print(f"   Calls field: {len(calls)} functions → {', '.join(calls[:5])}")
        if len(calls) > 5:
            print(f"                ... and {len(calls) - 5} more")
        print(f"   CALLS rels:  {rel_count} relationships")

    print(f"\n{'─' * 80}")
    print(f"Total calls in 'calls' field: {total_calls_in_field}")
    print(f"Total CALLS relationships:    {total_relationships}")
    print(f"Conversion rate:              {(total_relationships/total_calls_in_field*100) if total_calls_in_field > 0 else 0:.1f}%")


def find_expected_connections(client):
    """Find connections that SHOULD exist based on code patterns."""
    print_header("Expected Connections (Based on Code Analysis)")

    # Pattern 1: Endpoint → Service
    print("\n📌 Pattern 1: Endpoint functions should call Service functions")

    endpoint_query = """
    MATCH (n)
    WHERE n.namespace = 'sock_shop:payment'
    AND n.file_path CONTAINS 'endpoints.go'
    AND n.name CONTAINS 'Endpoint'
    RETURN n.name as name, n.code as code
    """

    endpoints = client.execute_query(endpoint_query, {})

    for ep in endpoints:
        print(f"\n   {ep['name']}:")

        # Look for service calls in code
        code = ep.get('code', '')
        if code:
            # Pattern: s.Authorise(...)
            service_calls = re.findall(r's\.(\w+)\(', code)
            if service_calls:
                print(f"      Code calls: {', '.join(set(service_calls))}")

                # Check if relationships exist
                for svc_func in set(service_calls):
                    rel_query = """
                    MATCH (a {name: $endpoint_name, namespace: 'sock_shop:payment'})
                          -[:CALLS]->(b {name: $service_name, namespace: 'sock_shop:payment'})
                    WHERE b.file_path CONTAINS 'service.go'
                    RETURN count(b) as exists
                    """

                    rel_check = client.execute_query(rel_query, {
                        "endpoint_name": ep['name'],
                        "service_name": svc_func
                    })

                    exists = rel_check[0]['exists'] > 0
                    status = "✅" if exists else "❌"
                    print(f"      {status} Relationship to {svc_func}: {'EXISTS' if exists else 'MISSING'}")

    # Pattern 2: Decoder → Validation
    print("\n\n📌 Pattern 2: Decode functions should call validation")

    decode_query = """
    MATCH (n)
    WHERE n.namespace = 'sock_shop:payment'
    AND n.name CONTAINS 'decode'
    RETURN n.name as name, n.calls as calls
    """

    decoders = client.execute_query(decode_query, {})

    for dec in decoders:
        print(f"\n   {dec['name']}:")
        calls = dec.get('calls', [])
        if calls:
            print(f"      Calls: {', '.join(calls)}")
        else:
            print(f"      ❌ No calls extracted")


def analyze_layer_connectivity(client):
    """Analyze connectivity between architectural layers."""
    print_header("Layer Connectivity Analysis")

    layers = {
        "Transport": "transport.go",
        "Endpoint": "endpoints.go",
        "Service": "service.go",
        "Logging": "logging.go"
    }

    print("\nExpected flow: Transport → Endpoint → Service")
    print(f"{'─' * 80}\n")

    for from_layer, from_file in layers.items():
        for to_layer, to_file in layers.items():
            if from_layer == to_layer:
                continue

            query = """
            MATCH (a)-[:CALLS]->(b)
            WHERE a.namespace = 'sock_shop:payment'
            AND a.file_path CONTAINS $from_file
            AND b.file_path CONTAINS $to_file
            RETURN count(*) as connections
            """

            result = client.execute_query(query, {
                "from_file": from_file,
                "to_file": to_file
            })

            connections = result[0]['connections']
            status = "✅" if connections > 0 else "❌"

            if connections > 0 or (from_layer in ["Transport", "Endpoint"] and to_layer in ["Endpoint", "Service"]):
                print(f"{status} {from_layer:12} → {to_layer:12}: {connections} connections")


def verify_critical_paths(client):
    """Verify critical execution paths exist."""
    print_header("Critical Path Verification")

    critical_paths = [
        {
            "name": "MakeHTTPHandler → decodeAuthoriseRequest",
            "from": "MakeHTTPHandler",
            "to": "decodeAuthoriseRequest",
            "reason": "HTTP entry must call decoder"
        },
        {
            "name": "MakeAuthoriseEndpoint → Authorise (service)",
            "from": "MakeAuthoriseEndpoint",
            "to": "Authorise",
            "reason": "Endpoint must call service logic"
        },
        {
            "name": "encodeAuthoriseResponse → encodeError",
            "from": "encodeAuthoriseResponse",
            "to": "encodeError",
            "reason": "Response encoder handles errors"
        }
    ]

    for path in critical_paths:
        print(f"\n📍 {path['name']}")
        print(f"   Reason: {path['reason']}")

        # Direct relationship
        query = """
        MATCH (a {name: $from_name, namespace: 'sock_shop:payment'})
              -[:CALLS]->(b {name: $to_name, namespace: 'sock_shop:payment'})
        RETURN count(b) as direct
        """

        result = client.execute_query(query, {
            "from_name": path['from'],
            "to_name": path['to']
        })

        direct = result[0]['direct']

        if direct > 0:
            print(f"   ✅ Direct connection EXISTS ({direct} relationships)")
        else:
            print(f"   ❌ Direct connection MISSING")

            # Check if they exist but aren't connected
            exists_query = """
            MATCH (a {name: $name, namespace: 'sock_shop:payment'})
            RETURN count(a) as count
            """

            from_exists = client.execute_query(exists_query, {"name": path['from']})[0]['count']
            to_exists = client.execute_query(exists_query, {"name": path['to']})[0]['count']

            print(f"      {path['from']} exists: {from_exists > 0}")
            print(f"      {path['to']} exists: {to_exists > 0}")

            if from_exists > 0 and to_exists > 0:
                print(f"      💡 Both functions exist but aren't linked")


def show_what_works(client):
    """Show examples of what IS working."""
    print_header("What IS Working (Examples)")

    query = """
    MATCH (a)-[r:CALLS]->(b)
    WHERE a.namespace = 'sock_shop:payment'
    AND a.file_path CONTAINS 'endpoints.go'
    RETURN a.name as from_func, b.name as to_func, b.file_path as to_file
    LIMIT 5
    """

    results = client.execute_query(query, {})

    if results:
        print("\n✅ Working examples (Endpoint layer calls):")
        for r in results:
            to_file = Path(r['to_file']).name if r['to_file'] else 'unknown'
            print(f"   {r['from_func']:30} → {r['to_func']:30} ({to_file})")
    else:
        print("\n❌ No working examples found in Endpoint layer")

    # Show what the calls field contains
    print("\n\n📋 Sample 'calls' field content:")

    calls_query = """
    MATCH (n)
    WHERE n.namespace = 'sock_shop:payment'
    AND n.calls IS NOT NULL
    AND size(n.calls) > 0
    RETURN n.name as func, n.calls as calls, n.file_path as file
    LIMIT 5
    """

    calls_results = client.execute_query(calls_query, {})

    for r in calls_results:
        file_name = Path(r['file']).name if r['file'] else 'unknown'
        print(f"\n   {r['func']} ({file_name}):")
        print(f"      calls = {r['calls']}")


def main():
    """Run all analyses."""
    client = Neo4jClient()
    client.connect()

    analyze_calls_field_vs_relationships(client)
    find_expected_connections(client)
    analyze_layer_connectivity(client)
    verify_critical_paths(client)
    show_what_works(client)

    client.close()

    print("\n" + "=" * 80)
    print("\n💡 SUMMARY:")
    print("   The 'calls' field IS being populated by the parser")
    print("   But CALLS relationships are only created for functions in the same file/batch")
    print("   We need to create relationships AFTER all files are ingested")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
