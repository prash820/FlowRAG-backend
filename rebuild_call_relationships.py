#!/usr/bin/env python3
"""
Rebuild CALLS Relationships from 'calls' Field

The parser correctly extracts function calls into the 'calls' field,
but relationships are only created during ingestion if both functions
are in the same batch.

This script creates missing CALLS relationships by:
1. Reading the 'calls' field from each function
2. Finding matching functions in the graph
3. Creating CALLS relationships
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases.neo4j.client import Neo4jClient
from dotenv import load_dotenv

load_dotenv()


def rebuild_relationships(client, namespace="sock_shop:payment", dry_run=False):
    """Rebuild CALLS relationships from 'calls' field."""

    print("=" * 80)
    print("REBUILDING CALLS RELATIONSHIPS")
    print("=" * 80)

    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")

    # Get all functions with calls
    query = """
    MATCH (n)
    WHERE n.namespace STARTS WITH $namespace
    AND n.type IN ['Function', 'Method']
    AND n.calls IS NOT NULL
    AND size(n.calls) > 0
    RETURN n.id as id, n.name as name, n.calls as calls, n.namespace as namespace
    """

    functions = client.execute_query(query, {"namespace": namespace})

    print(f"\nFound {len(functions)} functions with calls to process\n")

    total_calls = 0
    new_relationships = 0
    existing_relationships = 0
    not_found = 0

    for func in functions:
        func_id = func['id']
        func_name = func['name']
        calls = func['calls'] or []
        func_namespace = func['namespace']

        total_calls += len(calls)

        print(f"Processing {func_name} ({len(calls)} calls)...")

        for called_name in calls:
            # Clean up the called name (remove receiver prefix like 's.', 'logger.', etc.)
            clean_name = called_name
            if '.' in called_name:
                parts = called_name.split('.')
                # If it looks like a method call (e.g., s.Authorise), try the method name
                if len(parts) == 2 and parts[0] in ['s', 'ctx', 'w', 'r', 'logger', 'client']:
                    clean_name = parts[1]

            # Try to find the called function in the same namespace
            find_query = """
            MATCH (target)
            WHERE target.namespace = $namespace
            AND (target.name = $called_name OR target.name = $clean_name)
            AND target.type IN ['Function', 'Method']
            RETURN target.id as target_id, target.name as target_name
            LIMIT 1
            """

            targets = client.execute_query(find_query, {
                "namespace": func_namespace,
                "called_name": called_name,
                "clean_name": clean_name
            })

            if targets:
                target_id = targets[0]['target_id']

                # Check if relationship already exists
                check_query = """
                MATCH (a {id: $from_id})-[r:CALLS]->(b {id: $to_id})
                RETURN count(r) as exists
                """

                check = client.execute_query(check_query, {
                    "from_id": func_id,
                    "to_id": target_id
                })

                if check[0]['exists'] > 0:
                    existing_relationships += 1
                    print(f"   ✓ {called_name} → {targets[0]['target_name']} (exists)")
                else:
                    if not dry_run:
                        # Create relationship
                        create_query = """
                        MATCH (a {id: $from_id}), (b {id: $to_id})
                        MERGE (a)-[r:CALLS]->(b)
                        RETURN r
                        """

                        client.execute_query(create_query, {
                            "from_id": func_id,
                            "to_id": target_id
                        })

                    new_relationships += 1
                    print(f"   ✅ {called_name} → {targets[0]['target_name']} (created)")
            else:
                not_found += 1
                # Don't print for stdlib functions
                if not any(prefix in called_name for prefix in ['fmt.', 'http.', 'json.', 'time.', 'log.', 'os.', 'ioutil.', 'prometheus.', 'stdopentracing.']):
                    print(f"   ⚠️  {called_name} (not found in graph)")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total function calls processed:  {total_calls}")
    print(f"Existing relationships:          {existing_relationships}")
    print(f"{'Would create' if dry_run else 'Created'} new relationships: {new_relationships}")
    print(f"Not found (external/stdlib):     {not_found}")
    print(f"\nConversion rate: {((existing_relationships + new_relationships) / total_calls * 100) if total_calls > 0 else 0:.1f}%")
    print("=" * 80)

    return new_relationships


def verify_critical_paths(client):
    """Verify critical paths after rebuild."""
    print("\n" + "=" * 80)
    print("VERIFYING CRITICAL PATHS")
    print("=" * 80)

    critical_paths = [
        ("MakeAuthoriseEndpoint", "Authorise", "Endpoint → Service"),
        ("MakeHealthEndpoint", "Health", "Endpoint → Service"),
        ("encodeAuthoriseResponse", "encodeError", "Response → Error"),
        ("MakeEndpoints", "MakeAuthoriseEndpoint", "Setup → Endpoint"),
    ]

    for from_func, to_func, description in critical_paths:
        query = """
        MATCH (a {name: $from_name, namespace: 'sock_shop:payment'})
              -[:CALLS]->(b {name: $to_name, namespace: 'sock_shop:payment'})
        RETURN count(b) as count
        """

        result = client.execute_query(query, {
            "from_name": from_func,
            "to_name": to_func
        })

        count = result[0]['count']
        status = "✅" if count > 0 else "❌"

        print(f"{status} {description:25} ({from_func} → {to_func}): {count} connections")


def show_flow_example(client):
    """Show an example complete flow."""
    print("\n" + "=" * 80)
    print("EXAMPLE COMPLETE FLOW")
    print("=" * 80)

    query = """
    MATCH path = (entry {name: 'MakeAuthoriseEndpoint', namespace: 'sock_shop:payment'})
                 -[:CALLS*1..3]->(target)
    WHERE target.file_path CONTAINS 'service.go'
    WITH path, length(path) as depth
    RETURN [node in nodes(path) | node.name] as chain, depth
    ORDER BY depth
    LIMIT 5
    """

    results = client.execute_query(query, {})

    if results:
        print("\n✅ Complete flow from MakeAuthoriseEndpoint to service:")
        for r in results:
            chain_str = " → ".join(r['chain'])
            print(f"   Depth {r['depth']}: {chain_str}")
    else:
        print("\n❌ No complete flow found yet")
        print("   This means Endpoint → Service connections still missing")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Rebuild CALLS relationships")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--namespace", default="sock_shop:payment", help="Namespace to process")

    args = parser.parse_args()

    client = Neo4jClient()
    client.connect()

    # Rebuild relationships
    new_rels = rebuild_relationships(client, args.namespace, args.dry_run)

    if not args.dry_run and new_rels > 0:
        # Verify critical paths
        verify_critical_paths(client)

        # Show example flow
        show_flow_example(client)

        print("\n✅ Call graph rebuild complete!")
        print("\nNext steps:")
        print("   python3 verify_flow_call_graph.py  # Re-run verification")
        print("   python3 demo_flow.py                # See flows in action")
    elif args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")

    client.close()


if __name__ == "__main__":
    main()
