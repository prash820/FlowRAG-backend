"""
Analyze execution flows in Sock Shop microservices.

Usage:
    python3 analyze_flows.py                    # Show all entry points
    python3 analyze_flows.py --service payment  # Entry points for payment service
    python3 analyze_flows.py --trace <function> # Trace flow from specific function
    python3 analyze_flows.py --all              # Analyze all flows
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import argparse
import json
from databases.neo4j.client import Neo4jClient
from orchestrator.flow_detector import FlowDetector, EntryPointType


def list_entry_points(detector: FlowDetector, service: str = None):
    """List all detected entry points."""
    print("\n" + "=" * 80)
    print("API ENTRY POINTS DETECTED")
    print("=" * 80)

    entry_points = detector.detect_entry_points(service)

    if not entry_points:
        print("\n❌ No entry points found")
        return

    # Group by service
    by_service = {}
    for ep in entry_points:
        service_name = ep.service or "unknown"
        if service_name not in by_service:
            by_service[service_name] = []
        by_service[service_name].append(ep)

    # Display grouped results
    for service_name, eps in sorted(by_service.items()):
        print(f"\n📦 Service: {service_name}")
        print("-" * 80)

        # Group by type
        by_type = {}
        for ep in eps:
            type_name = ep.entry_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(ep)

        for type_name, type_eps in sorted(by_type.items()):
            print(f"\n  🔹 {type_name.upper()}: {len(type_eps)} endpoints")
            for ep in sorted(type_eps, key=lambda x: x.function_name):
                http_info = ""
                if ep.http_method:
                    http_info = f" [{ep.http_method}]"
                if ep.route:
                    http_info += f" {ep.route}"

                print(f"    • {ep.function_name}{http_info}")
                print(f"      {ep.file_path}:{ep.line_start}")

    print(f"\n" + "=" * 80)
    print(f"Total Entry Points: {len(entry_points)}")
    print("=" * 80)


def trace_flow(detector: FlowDetector, function_name: str, service: str = None):
    """Trace execution flow from a specific function."""
    print(f"\n🔍 Searching for function: {function_name}")

    # Find function by name
    query = """
    MATCH (n)
    WHERE n.name = $name
    AND n.type IN ['Function', 'Method']
    """

    if service:
        query += f"\nAND n.namespace = 'sock_shop:{service}'"

    query += "\nRETURN n.id as id, n.name as name, n.namespace as namespace"

    client = detector.client
    results = client.execute_query(query, {"name": function_name})

    if not results:
        print(f"❌ Function '{function_name}' not found")
        if not service:
            print("💡 Tip: Try specifying --service to narrow search")
        return

    if len(results) > 1:
        print(f"\n⚠️  Found {len(results)} functions with name '{function_name}':")
        for i, row in enumerate(results, 1):
            service_name = row['namespace'].split(':')[1] if ':' in row['namespace'] else row['namespace']
            print(f"  {i}. {service_name}::{row['name']}")
        print("\n💡 Please specify --service to select one")
        return

    # Build and visualize flow
    function_id = results[0]['id']
    print(f"✅ Found: {results[0]['namespace']}::{results[0]['name']}")
    print("\n🚀 Building execution flow...\n")

    try:
        flow = detector.build_execution_flow(function_id, max_depth=15)
        print(detector.visualize_flow(flow))

        # Show summary
        print("\n📊 Flow Summary:")
        print(f"  • Entry Type: {flow.entry_point.entry_type.value}")
        print(f"  • Max Depth: {flow.max_depth}")
        print(f"  • Functions Called: {len(flow.flow_nodes)}")

        # Count by type
        from collections import Counter
        type_counts = Counter(node.node_type.value for node in flow.flow_nodes)
        print(f"\n  Function Types:")
        for ftype, count in sorted(type_counts.items()):
            print(f"    - {ftype}: {count}")

    except Exception as e:
        print(f"❌ Error building flow: {e}")
        import traceback
        traceback.print_exc()


def analyze_all_flows(detector: FlowDetector, service: str = None, output_file: str = None):
    """Analyze all execution flows and save results."""
    print("\n" + "=" * 80)
    print("ANALYZING ALL EXECUTION FLOWS")
    print("=" * 80)

    entry_points = detector.detect_entry_points(service)
    print(f"\n📊 Found {len(entry_points)} entry points")

    if service:
        print(f"🔍 Filtering by service: {service}")

    print("\n🚀 Building execution flows...\n")

    flows = []
    successful = 0
    failed = 0

    for i, ep in enumerate(entry_points, 1):
        print(f"  [{i}/{len(entry_points)}] {ep.service}::{ep.function_name}...", end=" ")

        try:
            flow = detector.build_execution_flow(ep.function_id, max_depth=10)
            flows.append(flow.to_dict())
            successful += 1
            print(f"✅ ({len(flow.flow_nodes)} calls)")
        except Exception as e:
            failed += 1
            print(f"❌ {e}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Total Entry Points: {len(entry_points)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    if flows:
        # Analyze flows
        total_functions = sum(len(f['flow_nodes']) for f in flows)
        avg_depth = sum(f['max_depth'] for f in flows) / len(flows)

        print(f"\n  Total Functions in Flows: {total_functions}")
        print(f"  Average Flow Depth: {avg_depth:.1f}")

        # Find deepest flow
        deepest = max(flows, key=lambda f: f['max_depth'])
        print(f"\n  Deepest Flow:")
        print(f"    • Entry: {deepest['entry_point']['function_name']}")
        print(f"    • Service: {deepest['entry_point']['service']}")
        print(f"    • Depth: {deepest['max_depth']}")

        # Save to file
        if output_file:
            with open(output_file, 'w') as f:
                json.dump({
                    "summary": {
                        "total_entry_points": len(entry_points),
                        "successful_flows": successful,
                        "failed_flows": failed,
                        "total_functions": total_functions,
                        "average_depth": avg_depth
                    },
                    "flows": flows
                }, f, indent=2)
            print(f"\n✅ Results saved to: {output_file}")

    print("=" * 80)


def analyze_service_flow(detector: FlowDetector, service: str):
    """Analyze flows for a specific service in detail."""
    print("\n" + "=" * 80)
    print(f"SERVICE FLOW ANALYSIS: {service}")
    print("=" * 80)

    entry_points = detector.detect_entry_points(service)

    if not entry_points:
        print(f"\n❌ No entry points found for service: {service}")
        return

    print(f"\n📊 Found {len(entry_points)} entry points in {service}")

    # Analyze each entry point
    for i, ep in enumerate(entry_points, 1):
        print(f"\n{'─' * 80}")
        print(f"Entry Point {i}/{len(entry_points)}: {ep.function_name}")
        print(f"{'─' * 80}")

        try:
            flow = detector.build_execution_flow(ep.function_id, max_depth=10)
            print(detector.visualize_flow(flow))
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze execution flows in Sock Shop microservices"
    )
    parser.add_argument(
        "--service",
        help="Filter by service name (e.g., payment, user, catalogue)"
    )
    parser.add_argument(
        "--trace",
        metavar="FUNCTION",
        help="Trace execution flow from specific function"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all execution flows"
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Output file for flow analysis (JSON)"
    )
    parser.add_argument(
        "--analyze-service",
        metavar="SERVICE",
        help="Detailed analysis of all flows in a service"
    )

    args = parser.parse_args()

    # Connect to Neo4j
    print("🔌 Connecting to Neo4j...")
    client = Neo4jClient()
    client.connect()
    print("✅ Connected!\n")

    # Create flow detector
    detector = FlowDetector(client)

    # Execute requested action
    if args.trace:
        trace_flow(detector, args.trace, args.service)
    elif args.all:
        analyze_all_flows(detector, args.service, args.output or "flow_analysis.json")
    elif args.analyze_service:
        analyze_service_flow(detector, args.analyze_service)
    else:
        # Default: list entry points
        list_entry_points(detector, args.service)

    client.close()


if __name__ == "__main__":
    main()
