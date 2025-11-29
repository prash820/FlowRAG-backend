#!/usr/bin/env python3
"""
Test API route detection across Go, JavaScript, and Java parsers.

This script tests the route extraction functionality without full ingestion.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.parsers.go_parser import GoParser
from ingestion.parsers.javascript_parser import JavaScriptParser
from ingestion.parsers.java_parser import JavaParser
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test file paths
SOCK_SHOP_BASE = Path("/Users/prashanthboovaragavan/Documents/workspace/sock-shop-services")

TEST_FILES = {
    "go": SOCK_SHOP_BASE / "user/api/transport.go",
    "javascript": SOCK_SHOP_BASE / "front-end/api/user/index.js",
    "java": SOCK_SHOP_BASE / "carts/src/main/java/works/weave/socks/cart/controllers/CartsController.java"
}


def test_go_route_detection():
    """Test Go route detection (gorilla/mux)."""
    logger.info("\n" + "="*80)
    logger.info("Testing Go Route Detection (gorilla/mux)")
    logger.info("="*80)

    file_path = TEST_FILES["go"]
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return

    parser = GoParser()
    code = file_path.read_text()

    # Parse the file
    tree = parser.parser.parse(bytes(code, "utf8"))

    # Extract routes
    routes = parser.extract_api_routes(tree.root_node, code, str(file_path))

    logger.info(f"\nFile: {file_path.name}")
    logger.info(f"Routes found: {len(routes)}")

    for i, route in enumerate(routes, 1):
        logger.info(f"\n  {i}. {route.method} {route.path}")
        logger.info(f"     Handler: {route.handler}")
        logger.info(f"     Framework: {route.framework}")

    return routes


def test_javascript_route_detection():
    """Test JavaScript route detection (Express)."""
    logger.info("\n" + "="*80)
    logger.info("Testing JavaScript Route Detection (Express)")
    logger.info("="*80)

    file_path = TEST_FILES["javascript"]
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return

    parser = JavaScriptParser()
    code = file_path.read_text()

    # Parse the file
    import esprima
    tree = esprima.parseScript(code, {'loc': True, 'tolerant': True})

    # Extract routes
    routes = parser.extract_api_routes(tree, str(file_path))

    logger.info(f"\nFile: {file_path.name}")
    logger.info(f"Routes found: {len(routes)}")

    for i, route in enumerate(routes, 1):
        logger.info(f"\n  {i}. {route.method} {route.path}")
        logger.info(f"     Handler: {route.handler}")
        logger.info(f"     Framework: {route.framework}")
        if route.middleware:
            logger.info(f"     Middleware: {', '.join(route.middleware)}")

    return routes


def test_java_route_detection():
    """Test Java route detection (Spring Boot)."""
    logger.info("\n" + "="*80)
    logger.info("Testing Java Route Detection (Spring Boot)")
    logger.info("="*80)

    file_path = TEST_FILES["java"]
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        logger.info("Looking for any Java controller files...")

        # Try to find any Java file with annotations
        java_files = list((SOCK_SHOP_BASE / "carts").rglob("*.java"))
        if java_files:
            file_path = java_files[0]
            logger.info(f"Using: {file_path}")
        else:
            logger.warning("No Java files found")
            return

    parser = JavaParser()
    code = file_path.read_text()

    # Parse the file
    tree = parser.parser.parse(bytes(code, "utf8"))

    # Extract routes
    routes = parser.extract_api_routes(tree.root_node, code, str(file_path))

    logger.info(f"\nFile: {file_path.name}")
    logger.info(f"Routes found: {len(routes)}")

    for i, route in enumerate(routes, 1):
        logger.info(f"\n  {i}. {route.method} {route.path}")
        logger.info(f"     Handler: {route.handler}")
        logger.info(f"     Framework: {route.framework}")

    return routes


def main():
    """Run all tests."""
    logger.info("🧪 API Route Detection Test Suite")
    logger.info("="*80 + "\n")

    results = {}

    # Test Go
    try:
        go_routes = test_go_route_detection()
        results["go"] = len(go_routes) if go_routes else 0
    except Exception as e:
        logger.error(f"Go test failed: {e}")
        results["go"] = 0

    # Test JavaScript
    try:
        js_routes = test_javascript_route_detection()
        results["javascript"] = len(js_routes) if js_routes else 0
    except Exception as e:
        logger.error(f"JavaScript test failed: {e}")
        results["javascript"] = 0

    # Test Java
    try:
        java_routes = test_java_route_detection()
        results["java"] = len(java_routes) if java_routes else 0
    except Exception as e:
        logger.error(f"Java test failed: {e}")
        results["java"] = 0

    # Summary
    logger.info("\n" + "="*80)
    logger.info("📊 Test Summary")
    logger.info("="*80)
    logger.info(f"\nGo routes detected: {results['go']}")
    logger.info(f"JavaScript routes detected: {results['javascript']}")
    logger.info(f"Java routes detected: {results['java']}")
    logger.info(f"\nTotal routes detected: {sum(results.values())}")

    if sum(results.values()) > 0:
        logger.info("\n✅ API route detection is working!")
    else:
        logger.warning("\n⚠️  No routes detected - check file paths and parser implementation")


if __name__ == "__main__":
    main()
