#!/usr/bin/env python3
"""
FlowRAG Demo - Show Complete Request Flows

Demonstrates the full flow detection capabilities.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases.neo4j.client import Neo4jClient
from orchestrator.flow_detector import FlowDetector
import re


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)


def print_subheader(text):
    """Print a formatted subheader."""
    print("\n" + "-" * 80)
    print(text)
    print("-" * 80)


def demo_payment_flow():
    """Demonstrate payment service flow."""
    print_header("DEMO: Payment Service Request Flow")

    client = Neo4jClient()
    client.connect()

    # Get MakeHTTPHandler code
    query = """
    MATCH (n)
    WHERE n.namespace = "sock_shop:payment"
    AND n.name = "MakeHTTPHandler"
    RETURN n.code as code, n.file_path as file, n.line_start as line
    LIMIT 1
    """

    results = client.execute_query(query, {})

    if results:
        code = results[0]['code']
        file_path = results[0]['file']
        line = results[0]['line']

        print(f"\n📄 Entry Point: MakeHTTPHandler")
        print(f"   Location: {file_path}:{line}")

        # Extract POST /paymentAuth
        post_pattern = r'Methods\("POST"\)\.Path\("(/paymentAuth)"\).*?e\.(AuthoriseEndpoint)\),\s*(\w+),\s*(\w+)'
        match = re.search(post_pattern, code, re.DOTALL)

        if match:
            path = match.group(1)
            endpoint = match.group(2)
            decoder = match.group(3)
            encoder = match.group(4)

            print_subheader("POST /paymentAuth - Request Flow")

            print("\n🌐 Step 1: HTTP Request Arrives")
            print(f"   POST {path}")
            print("   Body: {\"amount\": 100.00}")

            print("\n📥 Step 2: Request Decoding")
            print(f"   Function: {decoder}")

            # Get decoder details
            decoder_query = """
            MATCH (n)
            WHERE n.namespace = "sock_shop:payment"
            AND n.name = $name
            RETURN n.file_path as file, n.line_start as line, n.signature as sig
            LIMIT 1
            """
            decoder_result = client.execute_query(decoder_query, {"name": decoder})
            if decoder_result:
                print(f"   Location: {decoder_result[0]['file']}:{decoder_result[0]['line']}")
                print(f"   Signature: {decoder_result[0]['sig']}")
                print("   → Reads HTTP request body")
                print("   → Unmarshals JSON to AuthoriseRequest")
                print("   → Validates amount field")

            print("\n🎯 Step 3: Endpoint Processing")
            print(f"   Function: {endpoint}")

            # Get endpoint details
            endpoint_query = """
            MATCH (n)
            WHERE n.namespace = "sock_shop:payment"
            AND n.name = $name
            RETURN n.file_path as file, n.line_start as line
            LIMIT 1
            """
            endpoint_result = client.execute_query(endpoint_query, {"name": endpoint})
            if endpoint_result:
                print(f"   Location: {endpoint_result[0]['file']}:{endpoint_result[0]['line']}")
                print("   → Wraps service call")
                print("   → Applies middleware (circuit breaker)")

            print("\n💼 Step 4: Business Logic")
            print("   Function: Authorise")

            # Get service details
            service_query = """
            MATCH (n)
            WHERE n.namespace = "sock_shop:payment"
            AND n.name = "Authorise"
            AND n.file_path CONTAINS "service.go"
            RETURN n.file_path as file, n.line_start as line, n.signature as sig, n.calls as calls
            LIMIT 1
            """
            service_result = client.execute_query(service_query, {})
            if service_result:
                print(f"   Location: {service_result[0]['file']}:{service_result[0]['line']}")
                print(f"   Signature: {service_result[0]['sig']}")
                print("   → Checks amount > declineOverAmount")
                print("   → Returns Authorisation{Authorised: true/false}")
                if service_result[0].get('calls'):
                    print(f"   → Internal calls: {', '.join(service_result[0]['calls'][:3])}")

            print("\n📤 Step 5: Response Encoding")
            print(f"   Function: {encoder}")

            # Get encoder details
            encoder_result = client.execute_query(decoder_query, {"name": encoder})
            if encoder_result:
                print(f"   Location: {encoder_result[0]['file']}:{encoder_result[0]['line']}")
                print(f"   Signature: {encoder_result[0]['sig']}")
                print("   → Converts AuthoriseResponse to JSON")
                print("   → Sets Content-Type header")
                print("   → Writes HTTP response")

            print("\n✅ Step 6: HTTP Response Sent")
            print("   Status: 200 OK")
            print("   Body: {\"authorised\": true}")

        # Extract GET /health
        health_pattern = r'Methods\("GET"\)\.Path\("(/health)"\).*?e\.(HealthEndpoint)\),\s*(\w+),\s*(\w+)'
        health_match = re.search(health_pattern, code, re.DOTALL)

        if health_match:
            path = health_match.group(1)
            endpoint = health_match.group(2)
            decoder = health_match.group(3)
            encoder = health_match.group(4)

            print_subheader("GET /health - Health Check Flow")

            print("\n🌐 HTTP Request: GET /health")
            print(f"   📥 Decoder: {decoder}")
            print(f"   🎯 Endpoint: {endpoint}")
            print(f"   💼 Service: Health")
            print(f"   📤 Encoder: {encoder}")
            print("   ✅ Response: [{\"status\": \"ok\"}]")

    # Show all endpoints
    print_subheader("All Detected Endpoints")

    endpoints_query = """
    MATCH (n)
    WHERE n.namespace = "sock_shop:payment"
    AND n.code CONTAINS "Methods("
    RETURN DISTINCT n.name as handler, n.file_path as file
    """

    endpoints = client.execute_query(endpoints_query, {})

    print("\n📍 Entry Point Handlers:")
    for ep in endpoints:
        print(f"   • {ep['handler']} ({Path(ep['file']).name})")

    # Count functions by type
    print_subheader("Function Classification")

    stats_query = """
    MATCH (n)
    WHERE n.namespace = "sock_shop:payment"
    AND n.type IN ['Function', 'Method']
    RETURN count(n) as total
    """

    total = client.execute_query(stats_query, {})

    decode_query = """
    MATCH (n)
    WHERE n.namespace = "sock_shop:payment"
    AND n.type IN ['Function', 'Method']
    AND (toLower(n.name) CONTAINS 'decode' OR toLower(n.name) CONTAINS 'encode')
    RETURN count(n) as count
    """

    encode_count = client.execute_query(decode_query, {})

    endpoint_query = """
    MATCH (n)
    WHERE n.namespace = "sock_shop:payment"
    AND n.type IN ['Function', 'Method']
    AND toLower(n.name) CONTAINS 'endpoint'
    RETURN count(n) as count
    """

    endpoint_count = client.execute_query(endpoint_query, {})

    service_query = """
    MATCH (n)
    WHERE n.namespace = "sock_shop:payment"
    AND n.file_path CONTAINS "service.go"
    AND n.type IN ['Function', 'Method']
    RETURN count(n) as count
    """

    service_count = client.execute_query(service_query, {})

    print(f"\n   Total Functions: {total[0]['total']}")
    print(f"   Transport Layer (encode/decode): {encode_count[0]['count']}")
    print(f"   Endpoint Layer: {endpoint_count[0]['count']}")
    print(f"   Service Layer: {service_count[0]['count']}")

    client.close()

    print("\n" + "=" * 80)


def demo_all_services():
    """Show entry points for all services."""
    print_header("DEMO: All Services Entry Points")

    client = Neo4jClient()
    client.connect()

    query = """
    MATCH (n)
    WHERE n.namespace STARTS WITH 'sock_shop:'
    AND (n.name CONTAINS 'Handler' OR n.name CONTAINS 'MakeHTTP' OR n.name = 'main')
    WITH DISTINCT split(n.namespace, ':')[1] as service
    RETURN service
    ORDER BY service
    """

    services = client.execute_query(query, {})

    for svc in services:
        service_name = svc['service']
        print(f"\n📦 Service: {service_name}")

        # Count entry points
        count_query = """
        MATCH (n)
        WHERE n.namespace = $namespace
        AND (n.name CONTAINS 'Handler' OR n.name CONTAINS 'MakeHTTP' OR n.name = 'main')
        RETURN count(n) as count
        """

        count = client.execute_query(count_query, {"namespace": f"sock_shop:{service_name}"})
        print(f"   Entry Points: {count[0]['count']}")

        # Get handler function
        handler_query = """
        MATCH (n)
        WHERE n.namespace = $namespace
        AND n.name CONTAINS 'Handler'
        RETURN n.name as name, n.file_path as file
        LIMIT 1
        """

        handler = client.execute_query(handler_query, {"namespace": f"sock_shop:{service_name}"})
        if handler:
            print(f"   Main Handler: {handler[0]['name']}")
            print(f"   File: {Path(handler[0]['file']).name}")

    client.close()
    print("\n" + "=" * 80)


def main():
    """Run all demos."""
    try:
        demo_payment_flow()
        demo_all_services()

        print("\n✅ Demo Complete!")
        print("\nNext Steps:")
        print("  • Run: python3 analyze_flows.py")
        print("  • Run: python3 query_request_flow.py payment")
        print("  • Run: python3 query_flowrag.py 'How does payment work?'")
        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
