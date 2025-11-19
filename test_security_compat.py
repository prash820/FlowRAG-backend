#!/usr/bin/env python3
"""
Test script to verify backward compatibility of security features.

This ensures that:
1. All existing functionality works with security disabled (default)
2. Security modules can be imported without errors
3. Schemas validate correctly with enhanced validation
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")

    try:
        from config import get_settings
        print("  ✓ config.get_settings")
    except Exception as e:
        print(f"  ✗ config.get_settings: {e}")
        return False

    try:
        from api.security.auth import verify_api_key, get_current_user
        print("  ✓ api.security.auth")
    except Exception as e:
        print(f"  ✗ api.security.auth: {e}")
        return False

    try:
        from api.security.validation import validate_file_path, validate_namespace
        print("  ✓ api.security.validation")
    except Exception as e:
        print(f"  ✗ api.security.validation: {e}")
        return False

    try:
        from api.security.rate_limit import get_rate_limiter
        print("  ✓ api.security.rate_limit")
    except Exception as e:
        print(f"  ✗ api.security.rate_limit: {e}")
        return False

    try:
        from api.schemas.ingest import IngestFileRequest, IngestDirectoryRequest
        print("  ✓ api.schemas.ingest")
    except Exception as e:
        print(f"  ✗ api.schemas.ingest: {e}")
        return False

    try:
        from api.schemas.query import QueryRequest
        print("  ✓ api.schemas.query")
    except Exception as e:
        print(f"  ✗ api.schemas.query: {e}")
        return False

    try:
        from api.middleware.cors import setup_cors, get_allowed_origins
        print("  ✓ api.middleware.cors")
    except Exception as e:
        print(f"  ✗ api.middleware.cors: {e}")
        return False

    return True


def test_settings():
    """Test that settings load correctly with new security fields."""
    print("\nTesting settings configuration...")

    try:
        from config import get_settings
        settings = get_settings()

        # Check existing fields still work
        assert hasattr(settings, 'app_name'), "Missing app_name"
        assert hasattr(settings, 'env'), "Missing env"
        assert hasattr(settings, 'debug'), "Missing debug"
        print(f"  ✓ Basic settings: env={settings.env}, debug={settings.debug}")

        # Check new security fields
        assert hasattr(settings, 'enable_security'), "Missing enable_security"
        assert hasattr(settings, 'enable_rate_limiting'), "Missing enable_rate_limiting"
        assert hasattr(settings, 'enable_path_validation'), "Missing enable_path_validation"
        print(f"  ✓ Security settings: security={settings.enable_security}, rate_limit={settings.enable_rate_limiting}")

        # Verify defaults (security should be disabled in dev)
        if settings.env == "development" and settings.debug:
            assert settings.enable_security == False, "Security should be disabled by default in dev"
            assert settings.enable_rate_limiting == False, "Rate limiting should be disabled by default in dev"
            print("  ✓ Development mode defaults correct")

        return True
    except Exception as e:
        print(f"  ✗ Settings test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schemas():
    """Test that schemas work with enhanced validation."""
    print("\nTesting schema validation...")

    try:
        from api.schemas.ingest import IngestFileRequest
        from api.schemas.query import QueryRequest

        # Test valid ingest request
        request = IngestFileRequest(
            file_path="/valid/path/to/file.py",
            namespace="test_namespace"
        )
        print(f"  ✓ IngestFileRequest: {request.namespace}")

        # Test valid query request
        query = QueryRequest(
            query="What is this code doing?",
            namespace="test_namespace"
        )
        print(f"  ✓ QueryRequest: {query.query[:30]}...")

        # Test invalid namespace (should fail)
        try:
            bad_request = IngestFileRequest(
                file_path="/some/file.py",
                namespace="../etc/passwd"
            )
            print("  ✗ Namespace validation not working (should have rejected '..')")
            return False
        except ValueError as e:
            print(f"  ✓ Namespace validation working: blocked '..'")

        # Test path traversal prevention
        try:
            bad_path = IngestFileRequest(
                file_path="../../../etc/passwd",
                namespace="test"
            )
            print("  ✗ Path validation not working (should have rejected '..')")
            return False
        except ValueError as e:
            print(f"  ✓ Path validation working: blocked traversal")

        return True
    except Exception as e:
        print(f"  ✗ Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cors():
    """Test CORS configuration."""
    print("\nTesting CORS configuration...")

    try:
        from api.middleware.cors import get_allowed_origins
        from config import get_settings

        settings = get_settings()
        origins = get_allowed_origins()

        print(f"  ✓ CORS origins loaded: {len(origins)} origins")

        # In development, should have localhost origins
        if settings.env == "development":
            assert any("localhost" in o for o in origins), "Should have localhost origins in dev"
            print(f"  ✓ Development CORS includes localhost")

        return True
    except Exception as e:
        print(f"  ✗ CORS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("FlowRAG Security Backward Compatibility Test")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Module Imports", test_imports()))
    results.append(("Settings Configuration", test_settings()))
    results.append(("Schema Validation", test_schemas()))
    results.append(("CORS Configuration", test_cors()))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All tests passed! Security features are backward compatible.")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
