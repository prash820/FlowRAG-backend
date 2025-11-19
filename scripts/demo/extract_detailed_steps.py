"""
Extract detailed step-by-step instructions from the Flux workflow
Useful for creating execution checklists
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases.neo4j.client import Neo4jClient
from config import get_settings

settings = get_settings()
neo4j_client = Neo4jClient()

def extract_execution_plan():
    """Extract complete execution plan with all dependencies resolved."""

    print("\n" + "=" * 80)
    print("FLUX LIGHT NODE SETUP - COMPLETE EXECUTION PLAN")
    print("=" * 80)

    # Get all phases in order
    phases_query = """
    MATCH (d:Document {namespace: 'flux_setup_guide'})-[:HAS_PHASE]->(p:Phase)
    RETURN p.name as phase, p.step_number as phase_num
    ORDER BY p.step_number
    """
    phases = neo4j_client.execute_query(phases_query, {})

    step_counter = 1

    for phase in phases:
        print(f"\n{'='*80}")
        print(f"PHASE {phase['phase_num']}: {phase['phase']}")
        print(f"{'='*80}\n")

        # Get all steps in this phase with their dependencies
        steps_query = """
        MATCH (p:Phase {namespace: 'flux_setup_guide', name: $phase_name})-[:CONTAINS]->(s:Step)
        OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dep:Step)
        OPTIONAL MATCH (s)-[:PARALLEL_WITH]->(par:Step)
        RETURN
            s.id as id,
            s.name as name,
            s.description as description,
            s.estimated_time as time,
            collect(DISTINCT dep.name) as dependencies,
            collect(DISTINCT par.name) as parallel_steps
        ORDER BY s.id
        """

        steps = neo4j_client.execute_query(steps_query, {"phase_name": phase['phase']})

        for step in steps:
            print(f"Step {step_counter}: {step['name']}")
            print(f"{'─' * 80}")

            # Description
            if step['description']:
                # Wrap long descriptions
                desc = step['description']
                if len(desc) > 76:
                    words = desc.split()
                    lines = []
                    current_line = []
                    current_length = 0

                    for word in words:
                        if current_length + len(word) + 1 > 76:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                            current_length = len(word)
                        else:
                            current_line.append(word)
                            current_length += len(word) + 1

                    if current_line:
                        lines.append(' '.join(current_line))

                    for line in lines:
                        print(f"  {line}")
                else:
                    print(f"  {desc}")

            # Time estimate
            print(f"  ⏱️  Estimated Time: {step['time']}")

            # Dependencies
            if step['dependencies'] and step['dependencies'][0]:
                print(f"  ⚠️  Prerequisites:")
                for dep in step['dependencies']:
                    if dep:
                        print(f"     • {dep}")

            # Parallel execution
            if step['parallel_steps'] and step['parallel_steps'][0]:
                print(f"  ⚡ Can run in parallel with:")
                for par in step['parallel_steps']:
                    if par:
                        print(f"     • {par}")

            print(f"  ☐ Not Started\n")
            step_counter += 1

    # Summary
    print(f"{'='*80}")
    print(f"TOTAL STEPS: {step_counter - 1}")
    print(f"{'='*80}\n")

    print("📋 EXECUTION CHECKLIST")
    print("─" * 80)
    print("Use this checklist to track your progress:")
    print("  ☐ Not Started")
    print("  ⏳ In Progress")
    print("  ✅ Completed")
    print("  ❌ Failed/Blocked")
    print()
    print("💡 TIP: Steps with ⚡ parallel markers can be executed simultaneously")
    print("         to reduce total setup time!")
    print()

if __name__ == "__main__":
    extract_execution_plan()
