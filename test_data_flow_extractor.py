#!/usr/bin/env python3
"""
Test script for the Data Flow Extractor.

Tests the new data flow extraction feature on the test-facade-service
DataGatheringService to verify it correctly identifies:
1. Variable assignments from async calls
2. Data dependencies between calls
3. Parallelization wave computation
"""

import sys
import json
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.parsers.data_flow_extractor import (
    get_data_flow_extractor,
    DependencyType,
)


def test_data_flow_extraction():
    """Test data flow extraction on DataGatheringService."""
    print("=" * 60)
    print("Testing Data Flow Extractor")
    print("=" * 60)

    # Read the test service file
    test_file = Path(__file__).parent.parent / "test-services/facade-service/src/services/data_gathering_service.ts"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    with open(test_file) as f:
        code = f.read()

    print(f"\n📄 Analyzing: {test_file.name}")
    print(f"   Lines: {len(code.splitlines())}")

    # Extract data flows
    extractor = get_data_flow_extractor(use_ast=False)
    result = extractor.extract_from_code(
        code=code,
        file_path=str(test_file),
        namespace="test-facade-service",
        language="typescript",
    )

    # Report assignments found
    print(f"\n📦 Variable Assignments Found: {len(extractor.assignments)}")
    print("-" * 40)
    for var_name, assignment in extractor.assignments.items():
        print(f"   {var_name} = await {assignment.source_call} (line {assignment.line_number})")

    # Report data flows found
    data_flows = result["data_flows"]
    print(f"\n🔀 Data Flow Edges Found: {len(data_flows)}")
    print("-" * 40)
    for edge in data_flows:
        dep_type = "?" if edge.is_conditional else "→"
        print(f"   {edge.source_call}.{edge.field} {dep_type} {edge.target_call}")
        if edge.is_conditional:
            print(f"      (conditional: {edge.condition})")

    # Report dependency graph
    print(f"\n📊 Dependency Graph:")
    print("-" * 40)
    for op, deps in result["dependency_graph"].items():
        if deps:
            print(f"   {op}")
            for dep in deps:
                print(f"      └── depends on: {dep}")
        else:
            print(f"   {op} (no dependencies)")

    # Report parallelization waves
    waves = result["waves"]
    print(f"\n🌊 Parallelization Waves: {len(waves)}")
    print("-" * 40)
    for wave in waves:
        print(f"\n   Wave {wave.wave_number}:")
        for op in wave.operations:
            print(f"      • {op}")
        if wave.depends_on_waves:
            print(f"      (after waves: {wave.depends_on_waves})")

    # Validate expected results
    print("\n" + "=" * 60)
    print("Validation")
    print("=" * 60)

    # Check for expected dependencies
    expected_deps = [
        ("creditClient.getCreditScore", "customerClient.getCustomerData"),
        ("employmentClient.verifyEmployment", "customerClient.getCustomerData"),
        ("incomeClient.verifyIncome", "creditClient.getCreditScore"),
        ("addressClient.verifyAddress", "customerClient.getCustomerData"),
        ("fraudClient.detectFraud", "creditClient.getCreditScore"),
        ("riskClient.calculateRiskScore", "fraudClient.detectFraud"),
    ]

    found_deps = set()
    for edge in data_flows:
        found_deps.add((edge.target_call, edge.source_call))

    passed = 0
    failed = 0
    for target, source in expected_deps:
        # Normalize call names (may have different prefixes)
        found = False
        for ft, fs in found_deps:
            if source.split('.')[-1] in fs and target.split('.')[-1] in ft:
                found = True
                break

        if found:
            print(f"   ✅ {source} → {target}")
            passed += 1
        else:
            print(f"   ❌ Missing: {source} → {target}")
            failed += 1

    print(f"\n   Passed: {passed}/{len(expected_deps)}")
    print(f"   Failed: {failed}/{len(expected_deps)}")

    # Check wave count
    if len(waves) >= 3:
        print(f"   ✅ Multiple waves detected ({len(waves)} waves)")
    else:
        print(f"   ⚠️  Only {len(waves)} waves detected (expected 3+)")

    return failed == 0


if __name__ == "__main__":
    success = test_data_flow_extraction()
    sys.exit(0 if success else 1)
