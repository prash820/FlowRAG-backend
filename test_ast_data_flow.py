#!/usr/bin/env python3
"""
Test script for AST-based data flow extraction.

Compares regex-based vs AST-based data flow extraction to validate
that the AST parser provides accurate results.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Enable feature flags for testing
import os
os.environ["FLOWRAG_FEATURE_ENABLE_TYPESCRIPT_AST"] = "true"
os.environ["FLOWRAG_FEATURE_ENABLE_DATA_FLOW_RELATIONSHIPS"] = "true"
os.environ["FLOWRAG_FEATURE_ENABLE_PARALLELIZATION_WAVES"] = "true"

from config.feature_flags import reset_feature_flags, get_feature_flags
reset_feature_flags()  # Reload flags with new env vars

from ingestion.parsers.data_flow_extractor import DataFlowExtractor
from ingestion.parsers.typescript_ast_parser import is_ast_available


def test_ast_data_flow():
    """Test AST-based data flow extraction."""
    print("=" * 60)
    print("Testing AST-Based Data Flow Extraction")
    print("=" * 60)

    # Check prerequisites
    if not is_ast_available():
        print("tree-sitter not available")
        return False

    flags = get_feature_flags()
    print(f"\nFeature Flags:")
    print(f"  enable_typescript_ast: {flags.enable_typescript_ast}")
    print(f"  enable_data_flow_relationships: {flags.enable_data_flow_relationships}")
    print(f"  enable_parallelization_waves: {flags.enable_parallelization_waves}")

    # Read the test service file
    test_file = Path(__file__).parent.parent / "test-services/facade-service/src/services/data_gathering_service.ts"

    if not test_file.exists():
        print(f"\nTest file not found: {test_file}")
        return False

    with open(test_file) as f:
        code = f.read()

    print(f"\nAnalyzing: {test_file.name}")
    print(f"Lines: {len(code.splitlines())}")

    # Test 1: Regex-based extraction (baseline)
    print(f"\n" + "=" * 60)
    print("1. Regex-Based Extraction (Baseline)")
    print("=" * 60)

    regex_extractor = DataFlowExtractor(use_ast=False)
    regex_result = regex_extractor.extract_from_code(
        code=code,
        file_path=str(test_file),
        namespace="test",
        language="typescript"
    )

    print(f"\nRegex Results:")
    print(f"  Assignments: {len(regex_extractor.assignments)}")
    print(f"  Data Flows: {len(regex_result['data_flows'])}")
    print(f"  Waves: {len(regex_result['waves'])}")

    regex_vars = set(regex_extractor.assignments.keys())
    print(f"  Variables: {sorted(regex_vars)}")

    # Test 2: AST-based extraction
    print(f"\n" + "=" * 60)
    print("2. AST-Based Extraction")
    print("=" * 60)

    ast_extractor = DataFlowExtractor(use_ast=True)
    ast_result = ast_extractor.extract_from_code(
        code=code,
        file_path=str(test_file),
        namespace="test",
        language="typescript"
    )

    print(f"\nAST Results:")
    print(f"  Assignments: {len(ast_extractor.assignments)}")
    print(f"  Data Flows: {len(ast_result['data_flows'])}")
    print(f"  Waves: {len(ast_result['waves'])}")

    ast_vars = set(ast_extractor.assignments.keys())
    print(f"  Variables: {sorted(ast_vars)}")

    # Compare results
    print(f"\n" + "=" * 60)
    print("3. Comparison")
    print("=" * 60)

    # Variables found
    both_vars = regex_vars & ast_vars
    only_regex = regex_vars - ast_vars
    only_ast = ast_vars - regex_vars

    print(f"\nVariables found by both: {len(both_vars)}")
    print(f"Only in regex: {sorted(only_regex) if only_regex else 'None'}")
    print(f"Only in AST: {sorted(only_ast) if only_ast else 'None'}")

    # Data flows comparison
    regex_flows = {(e.source_call, e.target_call, e.field) for e in regex_result['data_flows']}
    ast_flows = {(e.source_call, e.target_call, e.field) for e in ast_result['data_flows']}

    both_flows = regex_flows & ast_flows
    only_regex_flows = regex_flows - ast_flows
    only_ast_flows = ast_flows - regex_flows

    print(f"\nData flows found by both: {len(both_flows)}")
    print(f"Only in regex: {len(only_regex_flows)}")
    print(f"Only in AST: {len(only_ast_flows)}")

    # Validation
    print(f"\n" + "=" * 60)
    print("4. Validation")
    print("=" * 60)

    passed = 0
    failed = 0

    # Expected variables
    expected_vars = [
        "customerData", "creditScore", "employmentData", "incomeData",
        "productData", "addressData", "fraudData", "complianceData",
        "riskScore", "auditData"
    ]

    print("\nAST Variable Detection:")
    for var in expected_vars:
        if var in ast_vars:
            print(f"  [OK] {var}")
            passed += 1
        else:
            print(f"  [MISSING] {var}")
            failed += 1

    # Expected data flows (source -> target via field)
    # Note: Method names must match actual code (verifyEmployment, verifyIncome)
    expected_flows = [
        ("customerClient.getCustomerData", "creditClient.getCreditScore", "ssn"),
        ("customerClient.getCustomerData", "creditClient.getCreditScore", "dateOfBirth"),
        ("customerClient.getCustomerData", "employmentClient.verifyEmployment", "employerInfo"),
        ("creditClient.getCreditScore", "incomeClient.verifyIncome", "reportId"),
    ]

    print("\nAST Data Flow Detection:")
    for source, target, field in expected_flows:
        found = any(
            source in e.source_call and target in e.target_call and e.field == field
            for e in ast_result['data_flows']
        )
        if found:
            print(f"  [OK] {source} --[{field}]--> {target}")
            passed += 1
        else:
            print(f"  [MISSING] {source} --[{field}]--> {target}")
            failed += 1

    # Debug: Show all detected data flows
    print("\n  All detected AST data flows:")
    for e in ast_result['data_flows']:
        print(f"    {e.source_call} --[{e.field}]--> {e.target_call}")

    # Summary
    print(f"\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"\nPassed: {passed}/{passed + failed}")
    print(f"Failed: {failed}/{passed + failed}")

    if failed == 0:
        print("\nAST-based data flow extraction is working correctly!")
    else:
        print("\nSome validations failed. Review output above.")

    # Show wave comparison
    print(f"\n" + "=" * 60)
    print("Parallelization Waves Comparison")
    print("=" * 60)

    print("\nRegex Waves:")
    for wave in regex_result['waves']:
        print(f"  Wave {wave.wave_number}: {len(wave.operations)} operations")
        for op in wave.operations[:3]:
            print(f"    - {op}")
        if len(wave.operations) > 3:
            print(f"    ... and {len(wave.operations) - 3} more")

    print("\nAST Waves:")
    for wave in ast_result['waves']:
        print(f"  Wave {wave.wave_number}: {len(wave.operations)} operations")
        for op in wave.operations[:3]:
            print(f"    - {op}")
        if len(wave.operations) > 3:
            print(f"    ... and {len(wave.operations) - 3} more")

    return failed == 0


if __name__ == "__main__":
    success = test_ast_data_flow()
    sys.exit(0 if success else 1)
