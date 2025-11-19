#!/usr/bin/env python3
"""
Comprehensive Flow Call Graph Verification

Tests FlowRAG's ability to answer detailed questions about:
- Complete call chains (A → B → C → D)
- Multi-hop relationships (who calls whom)
- Data flow through services
- Function dependencies
- Entry-to-exit paths
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases.neo4j.client import Neo4jClient
from dotenv import load_dotenv
import json

load_dotenv()


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)


def print_test(number, question):
    """Print test question."""
    print(f"\n{'─' * 80}")
    print(f"Test {number}: {question}")
    print('─' * 80)


def test_direct_calls(client):
    """Test 1: What functions does MakeHTTPHandler directly call?"""
    print_test(1, "What functions does MakeHTTPHandler directly call?")

    query = """
    MATCH (handler {name: 'MakeHTTPHandler', namespace: 'sock_shop:payment'})-[:CALLS]->(called)
    RETURN called.name as function, called.file_path as file, called.line_start as line
    ORDER BY called.name
    """

    results = client.execute_query(query, {})

    if results:
        print(f"\n✅ MakeHTTPHandler directly calls {len(results)} functions:")
        for r in results:
            file_name = Path(r['file']).name if r['file'] else 'unknown'
            print(f"   • {r['function']} ({file_name}:{r['line']})")
    else:
        print("\n❌ No direct calls found")

    return len(results) > 0


def test_multi_hop_calls(client):
    """Test 2: What's the complete call chain from MakeHTTPHandler?"""
    print_test(2, "Complete call chain from MakeHTTPHandler (up to 3 levels deep)")

    query = """
    MATCH path = (entry {name: 'MakeHTTPHandler', namespace: 'sock_shop:payment'})-[:CALLS*1..3]->(called)
    WITH path, length(path) as depth
    RETURN
        [node in nodes(path) | node.name] as call_chain,
        depth,
        called.name as final_function,
        called.file_path as file
    ORDER BY depth, final_function
    LIMIT 20
    """

    results = client.execute_query(query, {})

    if results:
        print(f"\n✅ Found {len(results)} call chains:")

        by_depth = {}
        for r in results:
            depth = r['depth']
            if depth not in by_depth:
                by_depth[depth] = []
            by_depth[depth].append(r)

        for depth in sorted(by_depth.keys()):
            print(f"\n   Depth {depth} ({len(by_depth[depth])} chains):")
            for r in by_depth[depth][:5]:  # Show first 5 of each depth
                chain = ' → '.join(r['call_chain'])
                print(f"      {chain}")

            if len(by_depth[depth]) > 5:
                print(f"      ... and {len(by_depth[depth]) - 5} more")
    else:
        print("\n❌ No call chains found")

    return len(results) > 0


def test_reverse_calls(client):
    """Test 3: What functions call Authorise?"""
    print_test(3, "What functions call Authorise (reverse lookup)?")

    query = """
    MATCH (caller)-[:CALLS]->(target {name: 'Authorise', namespace: 'sock_shop:payment'})
    WHERE target.file_path CONTAINS 'service.go'
    RETURN DISTINCT
        caller.name as caller_function,
        caller.file_path as caller_file,
        caller.line_start as caller_line
    ORDER BY caller_function
    """

    results = client.execute_query(query, {})

    if results:
        print(f"\n✅ {len(results)} functions call Authorise:")
        for r in results:
            file_name = Path(r['caller_file']).name if r['caller_file'] else 'unknown'
            print(f"   • {r['caller_function']} ({file_name}:{r['caller_line']})")
    else:
        print("\n❌ No callers found")

        # Debug: check if Authorise exists
        debug_query = """
        MATCH (n {name: 'Authorise', namespace: 'sock_shop:payment'})
        RETURN n.file_path as file, n.line_start as line
        """
        debug_results = client.execute_query(debug_query, {})
        if debug_results:
            print(f"\n   💡 Authorise exists at: {debug_results[0]['file']}:{debug_results[0]['line']}")
            print("   💡 But no CALLS relationships found pointing to it")

    return len(results) > 0


def test_entry_to_service(client):
    """Test 4: Complete path from HTTP handler to service logic"""
    print_test(4, "Full path from HTTP entry point to Authorise service")

    query = """
    MATCH path = (entry {name: 'MakeHTTPHandler', namespace: 'sock_shop:payment'})
                 -[:CALLS*]->(service {name: 'Authorise', namespace: 'sock_shop:payment'})
    WHERE service.file_path CONTAINS 'service.go'
    WITH path, length(path) as depth
    RETURN
        [node in nodes(path) | node.name] as full_path,
        depth,
        [node in nodes(path) | node.file_path] as files
    ORDER BY depth
    LIMIT 5
    """

    results = client.execute_query(query, {})

    if results:
        print(f"\n✅ Found {len(results)} complete paths from entry to service:")
        for i, r in enumerate(results, 1):
            print(f"\n   Path {i} (depth {r['depth']}):")
            for j, func in enumerate(r['full_path']):
                file_name = Path(r['files'][j]).name if r['files'][j] else 'unknown'
                indent = "      " + ("   " * j)
                arrow = "└─→ " if j > 0 else ""
                print(f"{indent}{arrow}{func} ({file_name})")
    else:
        print("\n❌ No complete paths found")
        print("\n   💡 This suggests CALLS relationships may not be complete")

    return len(results) > 0


def test_function_call_count(client):
    """Test 5: Which functions are called most frequently?"""
    print_test(5, "Which functions are called most frequently (top 10)?")

    query = """
    MATCH (caller)-[:CALLS]->(called)
    WHERE called.namespace = 'sock_shop:payment'
    RETURN
        called.name as function,
        called.file_path as file,
        count(caller) as call_count
    ORDER BY call_count DESC
    LIMIT 10
    """

    results = client.execute_query(query, {})

    if results:
        print(f"\n✅ Most called functions:")
        for i, r in enumerate(results, 1):
            file_name = Path(r['file']).name if r['file'] else 'unknown'
            print(f"   {i}. {r['function']} - called {r['call_count']} times ({file_name})")
    else:
        print("\n❌ No call statistics available")

    return len(results) > 0


def test_layer_separation(client):
    """Test 6: Can we identify architectural layers?"""
    print_test(6, "Identify architectural layers (transport/endpoint/service)")

    # Transport layer
    transport_query = """
    MATCH (n)
    WHERE n.namespace = 'sock_shop:payment'
    AND n.file_path CONTAINS 'transport.go'
    AND n.type IN ['Function', 'Method']
    RETURN count(n) as count
    """

    # Endpoint layer
    endpoint_query = """
    MATCH (n)
    WHERE n.namespace = 'sock_shop:payment'
    AND n.file_path CONTAINS 'endpoints.go'
    AND n.type IN ['Function', 'Method']
    RETURN count(n) as count
    """

    # Service layer
    service_query = """
    MATCH (n)
    WHERE n.namespace = 'sock_shop:payment'
    AND n.file_path CONTAINS 'service.go'
    AND n.type IN ['Function', 'Method']
    RETURN count(n) as count
    """

    transport_count = client.execute_query(transport_query, {})[0]['count']
    endpoint_count = client.execute_query(endpoint_query, {})[0]['count']
    service_count = client.execute_query(service_query, {})[0]['count']

    print(f"\n✅ Layer separation:")
    print(f"   • Transport Layer (transport.go): {transport_count} functions")
    print(f"   • Endpoint Layer (endpoints.go): {endpoint_count} functions")
    print(f"   • Service Layer (service.go): {service_count} functions")

    # Cross-layer calls
    print(f"\n   Cross-layer call patterns:")

    cross_layer_query = """
    MATCH (transport)-[:CALLS]->(endpoint)-[:CALLS]->(service)
    WHERE transport.file_path CONTAINS 'transport.go'
    AND endpoint.file_path CONTAINS 'endpoints.go'
    AND service.file_path CONTAINS 'service.go'
    AND transport.namespace = 'sock_shop:payment'
    RETURN
        transport.name as transport_func,
        endpoint.name as endpoint_func,
        service.name as service_func
    LIMIT 5
    """

    cross_results = client.execute_query(cross_layer_query, {})

    if cross_results:
        print(f"   ✅ Found {len(cross_results)} cross-layer call chains:")
        for r in cross_results:
            print(f"      {r['transport_func']} → {r['endpoint_func']} → {r['service_func']}")
    else:
        print(f"   ❌ No cross-layer chains found")

    return transport_count > 0 and endpoint_count > 0 and service_count > 0


def test_decode_to_encode_flow(client):
    """Test 7: Complete request/response flow"""
    print_test(7, "Trace request flow: decode → endpoint → service → encode")

    query = """
    MATCH path = (decode)-[:CALLS*]->(encode)
    WHERE decode.namespace = 'sock_shop:payment'
    AND decode.name CONTAINS 'decode'
    AND encode.name CONTAINS 'encode'
    AND length(path) <= 4
    WITH path, length(path) as depth
    RETURN
        [node in nodes(path) | node.name] as flow,
        depth,
        decode.name as entry,
        encode.name as exit
    ORDER BY depth
    LIMIT 5
    """

    results = client.execute_query(query, {})

    if results:
        print(f"\n✅ Found {len(results)} complete request/response flows:")
        for i, r in enumerate(results, 1):
            print(f"\n   Flow {i}:")
            print(f"      Entry: {r['entry']}")
            print(f"      Path: {' → '.join(r['flow'])}")
            print(f"      Exit: {r['exit']}")
            print(f"      Depth: {r['depth']}")
    else:
        print("\n❌ No complete flows found")

    return len(results) > 0


def test_all_relationships(client):
    """Test 8: Count all CALLS relationships"""
    print_test(8, "Total CALLS relationships in payment service")

    query = """
    MATCH (a)-[r:CALLS]->(b)
    WHERE a.namespace = 'sock_shop:payment'
    RETURN count(r) as total_calls
    """

    result = client.execute_query(query, {})[0]
    total = result['total_calls']

    print(f"\n✅ Total CALLS relationships: {total}")

    # Breakdown by source file
    breakdown_query = """
    MATCH (a)-[r:CALLS]->(b)
    WHERE a.namespace = 'sock_shop:payment'
    WITH a.file_path as source_file, count(r) as call_count
    RETURN source_file, call_count
    ORDER BY call_count DESC
    """

    breakdown = client.execute_query(breakdown_query, {})

    if breakdown:
        print(f"\n   Breakdown by source file:")
        for r in breakdown:
            file_name = Path(r['source_file']).name if r['source_file'] else 'unknown'
            print(f"      • {file_name}: {r['call_count']} calls")

    return total > 0


def test_isolated_functions(client):
    """Test 9: Find functions with no calls (potential issues)"""
    print_test(9, "Functions with no outgoing or incoming calls")

    query = """
    MATCH (n)
    WHERE n.namespace = 'sock_shop:payment'
    AND n.type IN ['Function', 'Method']
    AND NOT (n)-[:CALLS]->()
    AND NOT ()-[:CALLS]->(n)
    RETURN n.name as function, n.file_path as file, n.line_start as line
    ORDER BY n.name
    LIMIT 10
    """

    results = client.execute_query(query, {})

    if results:
        print(f"\n⚠️  Found {len(results)} isolated functions:")
        for r in results:
            file_name = Path(r['file']).name if r['file'] else 'unknown'
            print(f"   • {r['function']} ({file_name}:{r['line']})")

        print(f"\n   💡 These may be:")
        print(f"      - Entry points (called externally)")
        print(f"      - Utility functions")
        print(f"      - Dead code")
    else:
        print("\n✅ All functions are connected in the call graph")

    return True


def test_specific_flow_question(client):
    """Test 10: Answer a specific flow question"""
    print_test(10, "When POST /paymentAuth arrives, what's the exact execution path?")

    print("\n   📍 Analyzing POST /paymentAuth flow...")

    # Get MakeHTTPHandler code to find the handler
    handler_query = """
    MATCH (n {name: 'MakeHTTPHandler', namespace: 'sock_shop:payment'})
    RETURN n.code as code
    LIMIT 1
    """

    handler = client.execute_query(handler_query, {})

    if handler and handler[0]['code']:
        code = handler[0]['code']

        # Extract handler chain from code
        import re
        pattern = r'Path\("/paymentAuth"\).*?e\.(AuthoriseEndpoint)\),\s*(\w+),\s*(\w+)'
        match = re.search(pattern, code, re.DOTALL)

        if match:
            endpoint = match.group(1)
            decoder = match.group(2)
            encoder = match.group(3)

            print(f"\n   ✅ Handler chain extracted from code:")
            print(f"      1. Entry: POST /paymentAuth")
            print(f"      2. Decoder: {decoder}")
            print(f"      3. Endpoint: {endpoint}")
            print(f"      4. Encoder: {encoder}")

            # Now trace through call graph
            print(f"\n   🔍 Tracing through call graph...")

            # Find what AuthoriseEndpoint calls
            endpoint_calls_query = """
            MATCH (endpoint {name: 'MakeAuthoriseEndpoint', namespace: 'sock_shop:payment'})
                  -[:CALLS*]->(service)
            WHERE service.file_path CONTAINS 'service.go'
            WITH service, length([(endpoint)-[:CALLS*]->(service)]) as depth
            RETURN DISTINCT service.name as service_func, depth
            ORDER BY depth
            LIMIT 5
            """

            service_calls = client.execute_query(endpoint_calls_query, {})

            if service_calls:
                print(f"\n   ✅ Complete flow:")
                print(f"      HTTP POST /paymentAuth")
                print(f"      ↓")
                print(f"      {decoder} (validates request)")
                print(f"      ↓")
                print(f"      {endpoint} (endpoint wrapper)")
                print(f"      ↓")
                for sc in service_calls:
                    print(f"      {sc['service_func']} (business logic, depth {sc['depth']})")
                print(f"      ↓")
                print(f"      {encoder} (formats response)")
                print(f"      ↓")
                print(f"      HTTP 200 OK")
                return True
            else:
                print(f"\n   ⚠️  Could not trace to service layer via call graph")
                print(f"   💡 Handler chain extracted, but CALLS relationships incomplete")

    return False


def main():
    """Run all verification tests."""
    print_header("FlowRAG Call Graph Verification")

    print("\nThis test suite verifies FlowRAG's ability to answer detailed questions")
    print("about service call graphs, execution flows, and architectural patterns.")

    client = Neo4jClient()
    client.connect()

    tests = [
        ("Direct Calls", test_direct_calls),
        ("Multi-hop Call Chains", test_multi_hop_calls),
        ("Reverse Lookup (Who calls X?)", test_reverse_calls),
        ("Entry to Service Path", test_entry_to_service),
        ("Call Frequency Analysis", test_function_call_count),
        ("Layer Separation", test_layer_separation),
        ("Request/Response Flow", test_decode_to_encode_flow),
        ("Total Relationships", test_all_relationships),
        ("Isolated Functions", test_isolated_functions),
        ("Specific Flow Question", test_specific_flow_question),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            passed = test_func(client)
            results[test_name] = "✅ PASS" if passed else "⚠️  PARTIAL"
        except Exception as e:
            results[test_name] = f"❌ FAIL: {e}"
            print(f"\n❌ Error: {e}")

    client.close()

    # Summary
    print_header("Test Results Summary")

    for test_name, result in results.items():
        print(f"   {result:15} {test_name}")

    passed = sum(1 for r in results.values() if "PASS" in r)
    partial = sum(1 for r in results.values() if "PARTIAL" in r)
    failed = sum(1 for r in results.values() if "FAIL" in r)

    print(f"\n   Total Tests: {len(tests)}")
    print(f"   ✅ Passed: {passed}")
    print(f"   ⚠️  Partial: {partial}")
    print(f"   ❌ Failed: {failed}")

    # Analysis
    print_header("Analysis & Recommendations")

    if passed >= 7:
        print("\n✅ EXCELLENT: FlowRAG has strong call graph tracking capabilities!")
        print("\n   You can reliably query:")
        print("   • Direct function calls")
        print("   • Multi-hop call chains")
        print("   • Architectural layers")
        print("   • Request/response flows")
    elif passed >= 5:
        print("\n⚠️  GOOD: FlowRAG has basic call graph tracking.")
        print("\n   Some advanced queries may need improvement:")
        print("   • Check CALLS relationship completeness")
        print("   • Verify cross-layer connections")
    else:
        print("\n❌ NEEDS IMPROVEMENT: Call graph tracking is incomplete.")
        print("\n   Recommendations:")
        print("   • Verify tree-sitter call extraction")
        print("   • Check CALLS relationship creation")
        print("   • Review parser implementation")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
