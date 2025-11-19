"""
Demo script to analyze the Flux workflow using Neo4j graph traversal
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases.neo4j.client import Neo4jClient
from config import get_settings

settings = get_settings()
neo4j_client = Neo4jClient()

def analyze_workflow():
    """Analyze the Flux workflow structure."""

    print("\n📊 FLUX LIGHT NODE WORKFLOW ANALYSIS")
    print("=" * 80)

    # Get document info
    doc_query = """
    MATCH (d:Document {namespace: 'flux_setup_guide'})
    RETURN d.title as title, d.author as author, d.document_type as doc_type
    """
    doc_info = neo4j_client.execute_query(doc_query, {})[0]
    print(f"\n📄 Document: {doc_info['title']}")
    print(f"   Author: {doc_info['author']}")
    print(f"   Type: {doc_info['doc_type']}\n")

    # Get phases
    phases_query = """
    MATCH (d:Document {namespace: 'flux_setup_guide'})-[:HAS_PHASE]->(p:Phase)
    RETURN p.name as phase, p.step_number as num
    ORDER BY p.step_number
    """
    phases = neo4j_client.execute_query(phases_query, {})
    print(f"📋 Workflow Phases ({len(phases)} total):\n")
    for phase in phases:
        print(f"   {phase['num']}. {phase['phase']}")

    # Get steps per phase
    print(f"\n🔍 Detailed Phase Breakdown:\n")
    for phase in phases:
        steps_query = """
        MATCH (p:Phase {namespace: 'flux_setup_guide', name: $phase_name})-[:CONTAINS]->(s:Step)
        RETURN s.name as step, s.estimated_time as time
        ORDER BY s.id
        """
        steps = neo4j_client.execute_query(steps_query, {"phase_name": phase['phase']})
        print(f"   Phase {phase['num']}: {phase['phase']} ({len(steps)} steps)")
        for step in steps:
            print(f"      • {step['step']} ({step['time']})")
        print()

    # Get dependency relationships
    deps_query = """
    MATCH (s1:Step {namespace: 'flux_setup_guide'})-[:DEPENDS_ON]->(s2:Step)
    RETURN s1.name as from_step, s2.name as to_step
    """
    deps = neo4j_client.execute_query(deps_query, {})
    print(f"🔗 Dependencies ({len(deps)} total):\n")
    if deps:
        for dep in deps[:10]:  # Show first 10
            print(f"   {dep['from_step']}")
            print(f"      → requires: {dep['to_step']}")
    else:
        print("   No explicit dependencies defined (sequential workflow)")

    # Get parallel steps
    parallel_query = """
    MATCH (s1:Step {namespace: 'flux_setup_guide'})-[:PARALLEL_WITH]->(s2:Step)
    RETURN DISTINCT s1.name as step1, s2.name as step2
    """
    parallel = neo4j_client.execute_query(parallel_query, {})
    print(f"\n⚡ Parallel Execution Opportunities ({len(parallel)} pairs):\n")
    if parallel:
        for pair in parallel:
            print(f"   {pair['step1']}")
            print(f"      ⚡ can run with: {pair['step2']}")
    else:
        print("   No parallel execution opportunities (sequential workflow)")

    # Get critical path
    print(f"\n⏱️  Critical Path Analysis:\n")
    critical_query = """
    MATCH path = (start:Step {namespace: 'flux_setup_guide'})-[:FOLLOWS*]->(end:Step)
    WHERE NOT exists((start)<-[:FOLLOWS]-())
    AND NOT exists((end)-[:FOLLOWS]->())
    RETURN nodes(path) as steps
    LIMIT 1
    """
    try:
        critical_paths = neo4j_client.execute_query(critical_query, {})
        if critical_paths:
            steps_list = critical_paths[0]['steps']
            print(f"   Critical path has {len(steps_list)} sequential steps")
            print(f"   First step: {steps_list[0]['name']}")
            print(f"   Last step: {steps_list[-1]['name']}")
        else:
            print("   No FOLLOWS relationships found (phases are independent)")
    except Exception as e:
        print(f"   Analysis note: {str(e)[:100]}")

    # Summary
    total_steps_query = """
    MATCH (s:Step {namespace: 'flux_setup_guide'})
    RETURN count(s) as total
    """
    total_steps = neo4j_client.execute_query(total_steps_query, {})[0]['total']

    print(f"\n" + "=" * 80)
    print(f"📈 Summary:")
    print(f"   • Total Phases: {len(phases)}")
    print(f"   • Total Steps: {total_steps}")
    print(f"   • Dependencies: {len(deps)}")
    print(f"   • Parallel Opportunities: {len(parallel)}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    analyze_workflow()
