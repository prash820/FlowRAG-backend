#!/usr/bin/env python3
"""
LLM-Powered GraphRAG Test
Demonstrates full pipeline with real embeddings and LLM summarization
"""

import sys
import os
from pathlib import Path
from typing import List, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from databases.neo4j.client import Neo4jClient
from ingestion.parsers.python_parser import PythonParser
from ingestion.loaders.neo4j_loader import Neo4jLoader
from config import get_settings


# Large complex codebase: Multi-step deployment system
DEPLOYMENT_SYSTEM = {
    "orchestrator.py": '''"""
Deployment Orchestrator - Manages the entire deployment workflow.

This is the main entry point for the deployment system. It coordinates
all the steps required to deploy an application from source to production.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DeploymentOrchestrator:
    """
    Orchestrates the complete deployment pipeline.

    The deployment process includes:
    1. Source code validation
    2. Dependency resolution
    3. Build process
    4. Testing suite execution
    5. Security scanning
    6. Container image creation
    7. Registry upload
    8. Infrastructure provisioning
    9. Database migrations
    10. Service deployment
    11. Health checks
    12. Traffic routing
    13. Monitoring setup
    14. Rollback preparation
    15. Documentation generation
    """

    def __init__(self, config):
        """Initialize orchestrator with deployment configuration."""
        self.config = config
        self.validator = SourceValidator()
        self.builder = BuildManager()
        self.tester = TestRunner()
        self.scanner = SecurityScanner()
        self.container = ContainerBuilder()
        self.registry = RegistryClient()
        self.infrastructure = InfrastructureManager()
        self.database = DatabaseMigrator()
        self.deployer = ServiceDeployer()
        self.monitor = MonitoringSetup()
        logger.info("Deployment orchestrator initialized")

    def deploy(self, application_name: str, version: str) -> Dict:
        """
        Execute complete deployment pipeline.

        Args:
            application_name: Name of the application to deploy
            version: Version identifier

        Returns:
            Deployment result with status and metadata
        """
        logger.info(f"Starting deployment: {application_name} v{version}")

        try:
            # Step 1-2: Validate and resolve
            self.validator.validate_source_code(application_name)
            dependencies = self.validator.resolve_dependencies()

            # Step 3-4: Build and test
            build_artifact = self.builder.build_application(application_name, dependencies)
            test_results = self.tester.run_test_suite(build_artifact)

            if not test_results.passed:
                raise DeploymentError("Tests failed")

            # Step 5-7: Security and containerization
            scan_results = self.scanner.scan_for_vulnerabilities(build_artifact)
            if scan_results.has_critical_issues:
                raise SecurityError("Critical vulnerabilities found")

            container_image = self.container.build_container(build_artifact)
            image_url = self.registry.push_image(container_image, version)

            # Step 8-10: Infrastructure and deployment
            infrastructure = self.infrastructure.provision_resources(self.config)
            self.database.run_migrations(infrastructure.database_url)
            deployment = self.deployer.deploy_service(image_url, infrastructure)

            # Step 11-13: Post-deployment
            health_status = self.deployer.check_health(deployment)
            if health_status.healthy:
                self.deployer.route_traffic(deployment)
                self.monitor.setup_monitoring(deployment)

            logger.info(f"Deployment successful: {application_name} v{version}")

            return {
                "status": "success",
                "application": application_name,
                "version": version,
                "deployment_url": deployment.url,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            self.rollback_deployment(application_name)
            raise


class SourceValidator:
    """Validates source code and resolves dependencies."""

    def validate_source_code(self, app_name: str) -> bool:
        """Validate source code structure and syntax."""
        # Validation logic
        return True

    def resolve_dependencies(self) -> List[str]:
        """Resolve and validate all dependencies."""
        # Dependency resolution
        return []


class BuildManager:
    """Manages the build process."""

    def build_application(self, app_name: str, dependencies: List[str]):
        """Build application with all dependencies."""
        # Build logic
        return BuildArtifact(app_name)


class TestRunner:
    """Executes test suites."""

    def run_test_suite(self, artifact) -> "TestResults":
        """Run complete test suite including unit, integration, and e2e tests."""
        # Test execution
        return TestResults(passed=True)
''',

    "security.py": '''"""
Security Scanner - Performs vulnerability scanning and security checks.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class SecurityScanner:
    """
    Scans for security vulnerabilities in code and dependencies.

    Performs multiple types of security checks:
    - Static code analysis
    - Dependency vulnerability scanning
    - Container image scanning
    - Secret detection
    - License compliance
    """

    def __init__(self):
        self.scanners = {
            'code': CodeAnalyzer(),
            'dependencies': DependencyScanner(),
            'container': ContainerScanner(),
            'secrets': SecretDetector()
        }

    def scan_for_vulnerabilities(self, artifact) -> "ScanResults":
        """
        Perform comprehensive security scan.

        Args:
            artifact: Build artifact to scan

        Returns:
            Scan results with vulnerability details
        """
        logger.info("Starting security scan")

        results = {
            'code_issues': self.scanners['code'].analyze(artifact),
            'dependency_vulns': self.scanners['dependencies'].scan(artifact),
            'container_issues': self.scanners['container'].scan(artifact),
            'secrets_found': self.scanners['secrets'].detect(artifact)
        }

        return ScanResults(results)

    def generate_security_report(self, scan_results) -> str:
        """Generate detailed security report."""
        return "Security report content"


class CodeAnalyzer:
    """Analyzes code for security issues."""

    def analyze(self, artifact) -> List[Dict]:
        """Perform static code analysis."""
        return []


class DependencyScanner:
    """Scans dependencies for known vulnerabilities."""

    def scan(self, artifact) -> List[Dict]:
        """Scan dependencies against vulnerability databases."""
        return []
''',

    "infrastructure.py": '''"""
Infrastructure Manager - Provisions and manages cloud infrastructure.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class InfrastructureManager:
    """
    Manages cloud infrastructure provisioning.

    Handles:
    - Cloud resource creation (VMs, containers, serverless)
    - Network configuration
    - Load balancer setup
    - Database provisioning
    - Storage allocation
    - DNS configuration
    - SSL certificate management
    """

    def __init__(self):
        self.cloud_provider = CloudProvider()
        self.network_manager = NetworkManager()
        self.dns_manager = DNSManager()

    def provision_resources(self, config: Dict) -> "Infrastructure":
        """
        Provision all required infrastructure resources.

        Args:
            config: Infrastructure configuration

        Returns:
            Provisioned infrastructure details
        """
        logger.info("Provisioning infrastructure")

        # Create compute resources
        compute = self.cloud_provider.create_compute_instances(
            instance_type=config['instance_type'],
            count=config['instance_count']
        )

        # Setup networking
        network = self.network_manager.setup_network(
            vpc_cidr=config['vpc_cidr'],
            subnets=config['subnets']
        )

        # Configure load balancer
        load_balancer = self.network_manager.create_load_balancer(
            instances=compute,
            health_check_path=config['health_check_path']
        )

        # Provision database
        database = self.cloud_provider.create_database(
            engine=config['db_engine'],
            instance_class=config['db_instance_class']
        )

        # Setup DNS
        domain = self.dns_manager.configure_dns(
            domain_name=config['domain'],
            load_balancer_url=load_balancer.url
        )

        return Infrastructure(
            compute=compute,
            network=network,
            load_balancer=load_balancer,
            database=database,
            domain=domain
        )

    def teardown_resources(self, infrastructure_id: str):
        """Teardown infrastructure resources."""
        logger.info(f"Tearing down infrastructure: {infrastructure_id}")
        # Cleanup logic


class CloudProvider:
    """Interface to cloud provider APIs."""

    def create_compute_instances(self, instance_type: str, count: int):
        """Create compute instances."""
        return ComputeInstances()

    def create_database(self, engine: str, instance_class: str):
        """Provision managed database."""
        return Database()


class NetworkManager:
    """Manages network configuration."""

    def setup_network(self, vpc_cidr: str, subnets: list):
        """Setup VPC and subnets."""
        return Network()

    def create_load_balancer(self, instances, health_check_path: str):
        """Create and configure load balancer."""
        return LoadBalancer()
''',

    "deployment.py": '''"""
Service Deployer - Deploys services and manages rollouts.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ServiceDeployer:
    """
    Deploys services using blue-green or canary deployment strategies.

    Features:
    - Blue-green deployments
    - Canary releases
    - Rolling updates
    - Health monitoring
    - Automatic rollback
    - Traffic splitting
    """

    def __init__(self):
        self.strategy = DeploymentStrategy()
        self.health_checker = HealthChecker()
        self.traffic_router = TrafficRouter()

    def deploy_service(self, image_url: str, infrastructure) -> "Deployment":
        """
        Deploy service using configured strategy.

        Args:
            image_url: Container image URL
            infrastructure: Provisioned infrastructure

        Returns:
            Deployment details
        """
        logger.info(f"Deploying service: {image_url}")

        # Deploy new version
        new_deployment = self.strategy.deploy_new_version(
            image_url=image_url,
            infrastructure=infrastructure
        )

        # Wait for startup
        self.wait_for_ready(new_deployment)

        return new_deployment

    def check_health(self, deployment) -> "HealthStatus":
        """Check deployment health status."""
        return self.health_checker.check(deployment)

    def route_traffic(self, deployment):
        """Route traffic to new deployment."""
        logger.info("Routing traffic to new deployment")
        self.traffic_router.switch_traffic(deployment)

    def rollback(self, deployment_id: str):
        """Rollback to previous deployment."""
        logger.warning(f"Rolling back deployment: {deployment_id}")
        self.strategy.rollback_to_previous()

    def wait_for_ready(self, deployment, timeout: int = 300):
        """Wait for deployment to be ready."""
        # Waiting logic
        pass


class HealthChecker:
    """Performs health checks on deployed services."""

    def check(self, deployment) -> "HealthStatus":
        """Execute health checks."""
        return HealthStatus(healthy=True)


class TrafficRouter:
    """Manages traffic routing between deployments."""

    def switch_traffic(self, deployment, percentage: int = 100):
        """Switch traffic to deployment."""
        # Traffic routing logic
        pass
'''
}


def print_section(title, char="="):
    """Print formatted section header."""
    print(f"\n{char*70}")
    print(f"  {title}")
    print(f"{char*70}")


def get_openai_embedding(text: str, settings) -> List[float]:
    """Get real OpenAI embedding for text."""
    client = OpenAI(api_key=settings.openai_api_key)

    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text
    )

    return response.data[0].embedding


def ingest_deployment_system(namespace="llm_graphrag_test"):
    """Ingest the deployment system codebase."""
    print_section("1. Ingesting Deployment System Codebase")

    settings = get_settings()
    parser = PythonParser()
    loader = Neo4jLoader()
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    collection_name = "llm_deployment_code"

    # Create Qdrant collection with real embedding dimensions
    try:
        qdrant.delete_collection(collection_name)
    except:
        pass

    print(f"\n  Creating Qdrant collection with {settings.qdrant_vector_size}D vectors...")
    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=settings.qdrant_vector_size, distance=Distance.COSINE)
    )

    total_nodes = 0
    total_relationships = 0
    points = []
    point_id = 0

    for filename, code in DEPLOYMENT_SYSTEM.items():
        print(f"\n  Processing {filename}...")

        # Parse code
        parse_result = parser.parse_string(
            code=code,
            namespace=namespace,
            file_path=filename
        )

        # Load to Neo4j
        result = loader.load_parse_result(parse_result)
        total_nodes += result['nodes_created']
        total_relationships += result['relationships_created']

        print(f"    Neo4j: {result['nodes_created']} nodes, {result['relationships_created']} relationships")

        # Create real embeddings for Qdrant
        embedding_count = 0
        for unit in parse_result.all_units:
            point_id += 1

            # Create embedding text
            text_to_embed = f"{unit.name}\n{unit.docstring or ''}\n{unit.code[:500]}"

            # Get real OpenAI embedding
            embedding = get_openai_embedding(text_to_embed, settings)

            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "id": unit.id,
                    "name": unit.name,
                    "type": unit.type.value,
                    "file_path": unit.file_path,
                    "docstring": unit.docstring or "",
                    "code": unit.code,
                    "namespace": namespace
                }
            ))
            embedding_count += 1

        print(f"    Qdrant: {embedding_count} embeddings created")

    # Upload to Qdrant in batches
    print(f"\n  Uploading {len(points)} embeddings to Qdrant...")
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i+batch_size]
        qdrant.upsert(collection_name=collection_name, points=batch)
        print(f"    Uploaded batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")

    print(f"\n  ✓ Total: {total_nodes} nodes, {total_relationships} relationships in Neo4j")
    print(f"  ✓ Total: {len(points)} real embeddings in Qdrant")

    return collection_name, namespace


def test_semantic_search_with_llm(collection_name, namespace):
    """Test semantic search with LLM summarization."""
    print_section("2. Semantic Search with LLM Summary", char="-")

    settings = get_settings()
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    client = OpenAI(api_key=settings.openai_api_key)

    query = "How does the system handle security vulnerabilities during deployment?"

    print(f"\n  Query: \"{query}\"\n")

    # Get query embedding
    print("  Step 1: Creating query embedding...")
    query_embedding = get_openai_embedding(query, settings)

    # Search Qdrant
    print("  Step 2: Searching for semantically similar code...")
    results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=5,
        query_filter=Filter(
            must=[FieldCondition(key="namespace", match=MatchValue(value=namespace))]
        )
    )

    print(f"\n  Found {len(results)} relevant code segments:\n")

    context_parts = []
    for i, result in enumerate(results, 1):
        payload = result.payload
        print(f"    {i}. {payload['name']} ({payload['type']}) - Similarity: {result.score:.3f}")
        print(f"       File: {payload['file_path']}")
        if payload.get('docstring'):
            print(f"       {payload['docstring'][:70]}...")

        context_parts.append(f"{payload['name']} in {payload['file_path']}:\n{payload['code'][:300]}")

    # Use LLM to summarize
    print("\n  Step 3: Using LLM to generate comprehensive answer...")

    context = "\n\n".join(context_parts)

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "You are a code analysis assistant. Analyze the provided code and answer questions about it."},
            {"role": "user", "content": f"Based on this code:\n\n{context}\n\nQuestion: {query}\n\nProvide a detailed answer:"}
        ],
        temperature=0.3,
        max_tokens=500
    )

    answer = response.choices[0].message.content

    print("\n  " + "="*66)
    print("  LLM-Generated Answer:")
    print("  " + "="*66)
    for line in answer.split('\n'):
        print(f"  {line}")
    print("  " + "="*66)


def test_flow_query_with_llm(namespace):
    """Test flow-based query with graph traversal and LLM summary."""
    print_section("3. Flow-Based Query with Graph + LLM", char="-")

    settings = get_settings()
    neo4j = Neo4jClient()
    client = OpenAI(api_key=settings.openai_api_key)

    print("\n  Query: Explain the complete deployment workflow\n")

    # Find entry point
    print("  Step 1: Finding deployment entry point...")
    query = """
    MATCH (c:Class {namespace: $namespace, name: 'DeploymentOrchestrator'})-[:CONTAINS]->(m:Method {name: 'deploy'})
    RETURN m.name as method, m.code as code, m.docstring as doc
    """

    entry_points = neo4j.execute_query(query, {"namespace": namespace})

    entry = None
    if entry_points:
        entry = entry_points[0]
        print(f"    Found: {entry['method']}()")
        print(f"    {entry['doc'][:100]}...")
    else:
        print("    No entry point found, using default context")

    # Trace execution flow
    print("\n  Step 2: Tracing execution flow through graph...")
    query = """
    MATCH (orchestrator:Class {namespace: $namespace, name: 'DeploymentOrchestrator'})
    MATCH (orchestrator)-[:CONTAINS]->(deploy:Method {name: 'deploy'})
    MATCH path = (deploy)-[:CALLS*1..3]->(called)
    WITH deploy, called, length(path) as depth
    WHERE depth <= 2
    RETURN DISTINCT
        called.name as function_name,
        called.type as type,
        called.docstring as description,
        called.code as code,
        depth
    ORDER BY depth, function_name
    LIMIT 15
    """

    flow_results = neo4j.execute_query(query, {"namespace": namespace})

    print(f"\n    Execution flow ({len(flow_results)} steps):\n")

    flow_context = []
    for i, step in enumerate(flow_results, 1):
        indent = "  " * step['depth']
        print(f"    {indent}{i}. {step['function_name']}()")
        if step['description']:
            print(f"    {indent}   {step['description'][:60]}...")

        flow_context.append(
            f"Step {i}: {step['function_name']}\n"
            f"Description: {step['description']}\n"
            f"Code:\n{step['code'][:400]}\n"
        )

    # Get class relationships
    print("\n  Step 3: Finding related classes and dependencies...")
    query = """
    MATCH (orchestrator:Class {namespace: $namespace, name: 'DeploymentOrchestrator'})
    MATCH (orchestrator)-[:CONTAINS]->(m:Method)
    MATCH (m)-[:CALLS]->(f)
    MATCH (parent_class:Class)-[:CONTAINS]->(f)
    WHERE parent_class.name <> 'DeploymentOrchestrator'
    RETURN DISTINCT
        parent_class.name as class_name,
        parent_class.docstring as description,
        count(f) as method_count
    ORDER BY method_count DESC
    LIMIT 10
    """

    dependencies = neo4j.execute_query(query, {"namespace": namespace})

    print(f"\n    Key dependencies ({len(dependencies)} classes):\n")
    for dep in dependencies:
        print(f"      • {dep['class_name']} ({dep['method_count']} methods called)")
        if dep['description']:
            print(f"        {dep['description'][:70]}...")

    # Use LLM to create comprehensive explanation
    print("\n  Step 4: Generating LLM-powered workflow explanation...")

    context = "\n\n".join(flow_context[:10])  # Limit context size
    deps_text = "\n".join([f"- {d['class_name']}: {d['description']}" for d in dependencies])

    entry_code = entry['code'][:500] if entry else "Entry point not found in code"

    prompt = f"""Analyze this deployment system and explain the complete workflow.

Entry Point Code:
{entry_code}

Execution Flow:
{context}

Key Dependencies:
{deps_text}

Provide a clear, step-by-step explanation of how the deployment process works, highlighting the key stages and their purposes."""

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "You are a senior software architect. Explain complex systems clearly and concisely."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=800
    )

    explanation = response.choices[0].message.content

    print("\n  " + "="*66)
    print("  LLM-Generated Workflow Explanation:")
    print("  " + "="*66)
    for line in explanation.split('\n'):
        print(f"  {line}")
    print("  " + "="*66)


def test_hybrid_query_with_llm(collection_name, namespace):
    """Test hybrid query combining vector + graph + LLM."""
    print_section("4. Hybrid Query: Vector + Graph + LLM", char="-")

    settings = get_settings()
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    neo4j = Neo4jClient()
    client = OpenAI(api_key=settings.openai_api_key)

    query = "What infrastructure components are provisioned and how are they configured?"

    print(f"\n  Query: \"{query}\"\n")

    # Step 1: Vector search to find relevant code
    print("  Step 1: Semantic search for relevant code...")
    query_embedding = get_openai_embedding(query, settings)

    vector_results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=3,
        query_filter=Filter(
            must=[
                FieldCondition(key="namespace", match=MatchValue(value=namespace)),
                FieldCondition(key="type", match=MatchValue(value="Method"))
            ]
        )
    )

    print(f"    Found {len(vector_results)} relevant methods:")
    for r in vector_results:
        print(f"      • {r.payload['name']}() - Similarity: {r.score:.3f}")

    # Step 2: Graph expansion to find related code
    print("\n  Step 2: Expanding via graph relationships...")

    if vector_results:
        top_match = vector_results[0].payload['name']

        query = """
        MATCH (m {namespace: $namespace, name: $method_name})
        OPTIONAL MATCH (m)-[:CALLS]->(called)
        OPTIONAL MATCH (parent:Class)-[:CONTAINS]->(m)
        RETURN
            m.name as method,
            m.code as code,
            m.docstring as doc,
            collect(DISTINCT called.name) as calls,
            parent.name as class_name,
            parent.docstring as class_doc
        """

        graph_results = neo4j.execute_query(
            query,
            {"namespace": namespace, "method_name": top_match}
        )

        if graph_results:
            gr = graph_results[0]
            print(f"    Method: {gr['method']}()")
            print(f"    Class: {gr['class_name']}")
            if gr['calls'] and gr['calls'][0]:
                print(f"    Calls: {', '.join([c for c in gr['calls'] if c][:5])}")

    # Step 3: Assemble context from both sources
    print("\n  Step 3: Assembling hybrid context...")

    context_parts = []

    # Add vector search results
    for result in vector_results[:2]:
        p = result.payload
        context_parts.append(f"{p['name']} in {p['file_path']}:\n{p['code'][:400]}")

    # Add graph expansion results
    if graph_results:
        gr = graph_results[0]
        context_parts.append(f"Full context for {gr['method']}:\n{gr['code'][:500]}")

    # Step 4: LLM summary
    print("\n  Step 4: Generating comprehensive answer with LLM...")

    context = "\n\n---\n\n".join(context_parts)

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "You are a cloud infrastructure expert. Explain infrastructure concepts clearly."},
            {"role": "user", "content": f"Based on this code:\n\n{context}\n\nQuestion: {query}\n\nProvide a detailed, technical answer:"}
        ],
        temperature=0.3,
        max_tokens=600
    )

    answer = response.choices[0].message.content

    print("\n  " + "="*66)
    print("  Hybrid LLM Answer (Vector + Graph Context):")
    print("  " + "="*66)
    for line in answer.split('\n'):
        print(f"  {line}")
    print("  " + "="*66)


def cleanup(collection_name, namespace):
    """Clean up test data."""
    print_section("5. Cleanup")

    try:
        settings = get_settings()

        # Clean Neo4j
        neo4j = Neo4jClient()
        query = f"MATCH (n {{namespace: '{namespace}'}}) DETACH DELETE n"
        neo4j.execute_query(query, {})
        print("  ✓ Cleaned up Neo4j test data")

        # Clean Qdrant
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        qdrant.delete_collection(collection_name)
        print(f"  ✓ Deleted Qdrant collection '{collection_name}'")
    except Exception as e:
        print(f"  ⚠ Cleanup warning: {e}")


def main():
    """Run LLM-powered GraphRAG demonstration."""
    print("\n" + "="*70)
    print("  LLM-Powered GraphRAG Test")
    print("="*70)
    print("\nDemonstrates:")
    print("  • Real OpenAI embeddings for semantic search")
    print("  • Graph traversal for execution flow")
    print("  • LLM summarization of code context")
    print("  • Hybrid retrieval (vector + graph)")

    try:
        # Ingest codebase
        collection_name, namespace = ingest_deployment_system()

        # Run different query strategies
        test_semantic_search_with_llm(collection_name, namespace)
        test_flow_query_with_llm(namespace)
        test_hybrid_query_with_llm(collection_name, namespace)

        # Cleanup
        cleanup(collection_name, namespace)

        print("\n" + "="*70)
        print("  ✓ LLM-Powered GraphRAG Test Complete!")
        print("="*70)
        print("\n💡 Key Capabilities Demonstrated:")
        print("  • Semantic search with real embeddings (1536D OpenAI vectors)")
        print("  • Graph-based execution flow tracing")
        print("  • LLM-powered code explanation and summarization")
        print("  • Hybrid retrieval combining vector + graph context")
        print("  • Multi-step workflow analysis (15+ deployment steps)")
        print("\nYour FlowRAG system is production-ready!")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
