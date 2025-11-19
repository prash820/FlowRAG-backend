"""
Query Request Flow in Sock Shop Services

Shows complete request flow from HTTP endpoint to response:
- HTTP entry point (POST /paymentAuth)
- Decode request handler
- Endpoint middleware
- Business logic
- Encode response

Usage:
    python3 query_request_flow.py "payment"         # Show all endpoints in payment
    python3 query_request_flow.py "POST /paymentAuth"  # Show flow for specific endpoint
    python3 query_request_flow.py --all             # Show all service endpoints
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases.neo4j.client import Neo4jClient
import re
import argparse


def extract_http_endpoints_from_code(code: str, language: str) -> list:
    """Extract HTTP endpoint definitions from source code."""
    endpoints = []

    if language == "go":
        # Pattern: r.Methods("POST").Path("/paymentAuth").Handler(...)
        pattern = r'r\.Methods\("([A-Z]+)"\)\.Path\("(/[^"]+)"\)\.Handler'
        matches = re.finditer(pattern, code)
        for match in matches:
            method = match.group(1)
            path = match.group(2)
            endpoints.append({"method": method, "path": path})

    elif language == "javascript":
        # Pattern: app.get('/api/users', ...)
        patterns = [
            r'app\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]',
            r'router\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]',
        ]
        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)
                endpoints.append({"method": method, "path": path})

    elif language == "java":
        # Pattern: @GetMapping("/api/users")
        patterns = [
            r'@GetMapping\([\'"]([^\'"]+)[\'"]',
            r'@PostMapping\([\'"]([^\'"]+)[\'"]',
            r'@PutMapping\([\'"]([^\'"]+)[\'"]',
            r'@DeleteMapping\([\'"]([^\'"]+)[\'"]',
        ]
        for pattern in patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                method = pattern.split("Mapping")[0][1:]  # Extract method from annotation
                path = match.group(1)
                endpoints.append({"method": method, "path": path})

    return endpoints


def find_handler_functions(code: str, path: str, language: str) -> list:
    """Find handler function names for a specific endpoint."""
    handlers = []

    if language == "go":
        # Find the handler for this path
        # Pattern: Path("/paymentAuth").Handler(...(e.AuthoriseEndpoint), decodeAuthoriseRequest, encodeAuthoriseResponse...)
        pattern = rf'Path\("{re.escape(path)}"\)\.Handler\([^)]*\((e\.(\w+)Endpoint)\),\s*(\w+),\s*(\w+)'
        match = re.search(pattern, code)
        if match:
            endpoint_name = match.group(2)  # e.g., "Authorise"
            decoder = match.group(3)
            encoder = match.group(4)
            handlers = [
                {"type": "decoder", "name": decoder},
                {"type": "endpoint", "name": endpoint_name},
                {"type": "encoder", "name": encoder}
            ]

    return handlers


def build_request_flow(client: Neo4jClient, service: str = None):
    """Build complete request flow documentation."""
    print("\n" + "=" * 80)
    print("REQUEST FLOW ANALYSIS")
    print("=" * 80)

    # Get all HTTP handler functions
    query = """
    MATCH (n)
    WHERE n.namespace STARTS WITH 'sock_shop:'
    AND (n.name CONTAINS 'Handler' OR n.name CONTAINS 'MakeHTTP' OR n.name = 'main')
    AND n.code IS NOT NULL
    """

    if service:
        query += f"\nAND n.namespace = 'sock_shop:{service}'"

    query += "\nRETURN n.name as name, n.namespace as namespace, n.code as code, " \
             "n.language as language, n.file_path as file_path, n.line_start as line_start " \
             "ORDER BY n.namespace, n.name"

    results = client.execute_query(query, {})

    flows_by_service = {}

    for row in results:
        service_name = row['namespace'].split(':')[1] if ':' in row['namespace'] else "unknown"
        code = row.get('code', '')
        language = row.get('language', '').lower()

        # Extract endpoints from code
        endpoints = extract_http_endpoints_from_code(code, language)

        if not endpoints:
            continue

        if service_name not in flows_by_service:
            flows_by_service[service_name] = []

        for endpoint in endpoints:
            # Find handler functions for this endpoint
            handlers = find_handler_functions(code, endpoint['path'], language)

            flow = {
                "service": service_name,
                "method": endpoint['method'],
                "path": endpoint['path'],
                "entry_function": row['name'],
                "file": row.get('file_path', ''),
                "line": row.get('line_start', 0),
                "handlers": handlers,
                "language": language
            }
            flows_by_service[service_name].append(flow)

    # Display results
    for service_name, flows in sorted(flows_by_service.items()):
        print(f"\n{'=' * 80}")
        print(f"📦 SERVICE: {service_name.upper()}")
        print(f"{'=' * 80}")

        for flow in flows:
            print(f"\n🔹 {flow['method']} {flow['path']}")
            print(f"   └─ Entry: {flow['entry_function']} ({flow['file']}:{flow['line']})")

            if flow['handlers']:
                print(f"   └─ Flow:")
                for i, handler in enumerate(flow['handlers'], 1):
                    arrow = "   " if i < len(flow['handlers']) else "   "
                    print(f"{arrow}  {i}. {handler['type']}: {handler['name']}")

                    # Try to find this function and its calls
                    if handler['type'] == 'endpoint':
                        # Find the actual endpoint function
                        find_endpoint_flow(client, service_name, handler['name'])

    print(f"\n{'=' * 80}")


def find_endpoint_flow(client: Neo4jClient, service: str, endpoint_name: str):
    """Find the flow within an endpoint function."""
    # Find functions that might be called by this endpoint
    query = """
    MATCH (n)
    WHERE n.namespace = $namespace
    AND n.name = $endpoint_name
    AND n.type IN ['Function', 'Method']
    RETURN n.id as id, n.name as name, n.code as code, n.calls as calls
    """

    results = client.execute_query(query, {
        "namespace": f"sock_shop:{service}",
        "endpoint_name": endpoint_name
    })

    if not results:
        # Try with "Endpoint" suffix
        results = client.execute_query(query, {
            "namespace": f"sock_shop:{service}",
            "endpoint_name": f"{endpoint_name}Endpoint"
        })

    if results:
        endpoint = results[0]
        calls = endpoint.get('calls', [])

        if calls:
            print(f"        └─ Calls:")
            for call in calls[:5]:  # Show first 5 calls
                # Try to classify the call
                call_lower = call.lower()
                if any(word in call_lower for word in ['valid', 'check', 'verify']):
                    call_type = "validation"
                elif any(word in call_lower for word in ['author', 'auth']):
                    call_type = "authorization"
                elif any(word in call_lower for word in ['log', 'debug']):
                    call_type = "logging"
                elif any(word in call_lower for word in ['error', 'err']):
                    call_type = "error_handling"
                else:
                    call_type = "processing"

                print(f"           • {call} ({call_type})")

            if len(calls) > 5:
                print(f"           ... and {len(calls) - 5} more")


def show_specific_endpoint_flow(client: Neo4jClient, endpoint_spec: str):
    """Show detailed flow for a specific endpoint (e.g., 'POST /paymentAuth')."""
    parts = endpoint_spec.split(' ', 1)
    if len(parts) != 2:
        print(f"❌ Invalid endpoint format. Use: METHOD /path")
        print(f"   Example: POST /paymentAuth")
        return

    method, path = parts

    print("\n" + "=" * 80)
    print(f"DETAILED FLOW: {method} {path}")
    print("=" * 80)

    # Find the handler
    query = """
    MATCH (n)
    WHERE n.namespace STARTS WITH 'sock_shop:'
    AND n.code CONTAINS $path
    AND n.code CONTAINS $method
    RETURN n.name as name, n.namespace as namespace, n.code as code,
           n.language as language, n.file_path as file_path, n.line_start as line_start
    LIMIT 1
    """

    results = client.execute_query(query, {"path": path, "method": method})

    if not results:
        print(f"❌ Endpoint not found: {method} {path}")
        return

    handler = results[0]
    service_name = handler['namespace'].split(':')[1] if ':' in handler['namespace'] else "unknown"
    code = handler.get('code', '')
    language = handler.get('language', '').lower()

    print(f"\n📦 Service: {service_name}")
    print(f"📄 File: {handler.get('file_path', '')}:{handler.get('line_start', 0)}")
    print(f"🔧 Language: {language}")

    # Extract handler functions
    handlers = find_handler_functions(code, path, language)

    if handlers:
        print(f"\n🔄 Request Flow:")
        print(f"\n1. HTTP Request: {method} {path}")

        for i, h in enumerate(handlers, 2):
            print(f"\n{i}. {h['type'].upper()}: {h['name']}")

            # Get details about this function
            func_query = """
            MATCH (n)
            WHERE n.namespace = $namespace
            AND n.name = $function_name
            RETURN n.code as code, n.calls as calls, n.signature as signature,
                   n.file_path as file_path, n.line_start as line_start
            LIMIT 1
            """

            func_results = client.execute_query(func_query, {
                "namespace": handler['namespace'],
                "function_name": h['name']
            })

            if func_results:
                func = func_results[0]
                print(f"   📍 Location: {func.get('file_path', '')}:{func.get('line_start', 0)}")
                if func.get('signature'):
                    print(f"   📝 Signature: {func['signature']}")

                calls = func.get('calls', [])
                if calls:
                    print(f"   └─ Calls {len(calls)} functions:")
                    for call in calls[:10]:
                        print(f"      • {call}")
                    if len(calls) > 10:
                        print(f"      ... and {len(calls) - 10} more")

        print(f"\n{len(handlers) + 1}. HTTP Response")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Query request flows in Sock Shop"
    )
    parser.add_argument(
        "endpoint",
        nargs="?",
        help="Service name or 'METHOD /path' (e.g., 'payment' or 'POST /paymentAuth')"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all endpoints across all services"
    )

    args = parser.parse_args()

    print("🔌 Connecting to Neo4j...")
    client = Neo4jClient()
    client.connect()
    print("✅ Connected!\n")

    if args.endpoint and ' ' in args.endpoint:
        # Specific endpoint flow
        show_specific_endpoint_flow(client, args.endpoint)
    elif args.endpoint:
        # Service-specific flows
        build_request_flow(client, args.endpoint)
    else:
        # All services
        build_request_flow(client)

    client.close()


if __name__ == "__main__":
    main()
