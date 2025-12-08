#!/usr/bin/env python3
"""
Test script for the TypeScript AST Parser.

Tests tree-sitter based parsing on the test-facade-service
DataGatheringService to verify it correctly extracts:
1. Await assignments
2. Field accesses
3. Class/method structures
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Enable the feature flag for testing
import os
os.environ["FLOWRAG_FEATURE_ENABLE_TYPESCRIPT_AST"] = "true"

from config.feature_flags import reset_feature_flags, get_feature_flags
reset_feature_flags()  # Reload flags with new env var

from ingestion.parsers.typescript_ast_parser import (
    TypeScriptASTParser,
    is_ast_available,
    get_typescript_ast_parser,
)


def test_ast_parser():
    """Test AST parser on DataGatheringService."""
    print("=" * 60)
    print("Testing TypeScript AST Parser")
    print("=" * 60)

    if not is_ast_available():
        print("❌ tree-sitter not available")
        return False

    # Check feature flag
    flags = get_feature_flags()
    print(f"\n🚩 Feature Flag: enable_typescript_ast = {flags.enable_typescript_ast}")

    # Read the test service file
    test_file = Path(__file__).parent.parent / "test-services/facade-service/src/services/data_gathering_service.ts"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    with open(test_file) as f:
        code = f.read()

    print(f"\n📄 Analyzing: {test_file.name}")
    print(f"   Lines: {len(code.splitlines())}")

    # Initialize parser
    parser = TypeScriptASTParser()

    # Test 1: Extract await assignments
    print(f"\n" + "=" * 60)
    print("1. Await Assignments (AST-based)")
    print("=" * 60)

    await_calls = parser.extract_await_assignments(code)
    print(f"\n📦 Found {len(await_calls)} await assignments:")
    for call in await_calls:
        print(f"   Line {call.line_number}: {call.variable_name} = await {call.call_chain}")
        if call.arguments:
            print(f"      Args: {call.arguments}")

    # Test 2: Extract field accesses
    print(f"\n" + "=" * 60)
    print("2. Field Accesses (AST-based)")
    print("=" * 60)

    field_accesses = parser.extract_field_accesses(code)

    # Filter to only show relevant field accesses (on our variable names)
    var_names = {call.variable_name for call in await_calls}
    relevant_accesses = [
        fa for fa in field_accesses
        if any(fa.object_name.endswith(v) or v in fa.object_name for v in var_names)
    ]

    print(f"\n🔍 Found {len(relevant_accesses)} relevant field accesses:")
    for access in relevant_accesses[:20]:  # Limit output
        opt_marker = "?." if access.is_optional else "."
        print(f"   Line {access.line_number}: {access.object_name}{opt_marker}{access.field_name}")

    # Test 3: Extract classes
    print(f"\n" + "=" * 60)
    print("3. Classes (AST-based)")
    print("=" * 60)

    classes = parser.extract_classes(code)
    print(f"\n📦 Found {len(classes)} classes:")
    for cls in classes:
        extends_info = f" extends {cls.extends}" if cls.extends else ""
        print(f"   {cls.name}{extends_info}")
        print(f"      Methods: {len(cls.methods)}")
        for method in cls.methods[:5]:  # Limit output
            async_marker = "async " if method.is_async else ""
            ret_type = f": {method.return_type}" if method.return_type else ""
            print(f"         • {async_marker}{method.name}(){ret_type}")

    # Validation
    print(f"\n" + "=" * 60)
    print("Validation")
    print("=" * 60)

    passed = 0
    failed = 0

    # Check await assignments
    expected_vars = [
        "customerData", "creditScore", "employmentData", "incomeData",
        "productData", "addressData", "fraudData", "complianceData",
        "riskScore", "auditData"
    ]

    found_vars = {call.variable_name for call in await_calls}
    for var in expected_vars:
        if var in found_vars:
            print(f"   ✅ Found await assignment: {var}")
            passed += 1
        else:
            print(f"   ❌ Missing await assignment: {var}")
            failed += 1

    # Check field accesses
    expected_fields = [
        ("customerData", "ssn"),
        ("customerData", "dateOfBirth"),
        ("creditScore", "reportId"),
    ]

    for obj, field in expected_fields:
        found = any(
            obj in fa.object_name and fa.field_name == field
            for fa in relevant_accesses
        )
        if found:
            print(f"   ✅ Found field access: {obj}.{field}")
            passed += 1
        else:
            print(f"   ❌ Missing field access: {obj}.{field}")
            failed += 1

    print(f"\n   Passed: {passed}/{passed + failed}")
    print(f"   Failed: {failed}/{passed + failed}")

    return failed == 0


if __name__ == "__main__":
    success = test_ast_parser()
    sys.exit(0 if success else 1)
