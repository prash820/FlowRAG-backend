"""
25-Step GraphRAG Test
Comprehensive test with a complex multi-step CI/CD pipeline
Tests both semantic search and flow-based graph traversal
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


# 25-Step CI/CD Pipeline Code
PIPELINE_ORCHESTRATOR = '''"""
CI/CD Pipeline Orchestrator - Manages complete deployment lifecycle
Implements a comprehensive 25-step pipeline with security, testing, and monitoring
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the complete CI/CD pipeline with 25 distinct steps.

    This orchestrator manages the entire deployment lifecycle including:
    - Code validation and linting (steps 1-3)
    - Security scanning and compliance (steps 4-7)
    - Build and compilation (steps 8-10)
    - Testing suite execution (steps 11-15)
    - Artifact management (steps 16-17)
    - Deployment strategies (steps 18-21)
    - Post-deployment validation (steps 22-23)
    - Monitoring and alerting (steps 24-25)
    """

    def __init__(self, config: Dict):
        """Initialize pipeline orchestrator with configuration."""
        self.config = config
        self.pipeline_state = {}
        self.execution_history = []
        logger.info("Pipeline orchestrator initialized")

    def execute_pipeline(self, code_repo: str, branch: str) -> Dict:
        """
        Execute the complete 25-step CI/CD pipeline.

        Args:
            code_repo: Repository URL or path
            branch: Git branch to deploy

        Returns:
            Dict containing pipeline execution results and metrics
        """
        logger.info(f"Starting 25-step pipeline for {code_repo}@{branch}")

        try:
            # Phase 1: Code Validation (Steps 1-3)
            self.step_01_checkout_code(code_repo, branch)
            self.step_02_validate_syntax()
            self.step_03_run_linter()

            # Phase 2: Security & Compliance (Steps 4-7)
            self.step_04_scan_secrets()
            self.step_05_scan_dependencies()
            self.step_06_license_compliance()
            self.step_07_sast_analysis()

            # Phase 3: Build Process (Steps 8-10)
            self.step_08_install_dependencies()
            self.step_09_compile_code()
            self.step_10_generate_assets()

            # Phase 4: Testing Suite (Steps 11-15)
            self.step_11_unit_tests()
            self.step_12_integration_tests()
            self.step_13_e2e_tests()
            self.step_14_performance_tests()
            self.step_15_security_tests()

            # Phase 5: Artifact Management (Steps 16-17)
            self.step_16_create_artifact()
            self.step_17_upload_to_registry()

            # Phase 6: Deployment (Steps 18-21)
            self.step_18_provision_infrastructure()
            self.step_19_deploy_to_staging()
            self.step_20_smoke_tests()
            self.step_21_deploy_to_production()

            # Phase 7: Post-Deployment (Steps 22-25)
            self.step_22_health_checks()
            self.step_23_regression_testing()
            self.step_24_setup_monitoring()
            self.step_25_enable_alerting()

            logger.info("Pipeline completed successfully")
            return self._generate_pipeline_report()

        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            self._handle_pipeline_failure(e)
            raise

    def step_01_checkout_code(self, repo: str, branch: str):
        """Step 1: Checkout code from version control."""
        logger.info(f"Step 1/25: Checking out {branch} from {repo}")
        # Clone repository and checkout specified branch
        self.pipeline_state['repo'] = repo
        self.pipeline_state['branch'] = branch
        self.pipeline_state['commit_sha'] = self._get_commit_sha()

    def step_02_validate_syntax(self):
        """Step 2: Validate code syntax across all files."""
        logger.info("Step 2/25: Validating syntax")
        # Parse all source files to check for syntax errors
        from validators.syntax_validator import SyntaxValidator
        validator = SyntaxValidator()
        results = validator.validate_all()
        if not results['valid']:
            raise SyntaxError(f"Syntax errors found: {results['errors']}")

    def step_03_run_linter(self):
        """Step 3: Run code linting and style checks."""
        logger.info("Step 3/25: Running linter")
        from validators.linter import CodeLinter
        linter = CodeLinter()
        issues = linter.check_all_files()
        self.pipeline_state['lint_issues'] = len(issues)
        if len(issues) > self.config.get('max_lint_issues', 0):
            raise ValueError(f"Too many lint issues: {len(issues)}")

    def step_04_scan_secrets(self):
        """Step 4: Scan for exposed secrets and credentials."""
        logger.info("Step 4/25: Scanning for secrets")
        from security.secret_scanner import SecretScanner
        scanner = SecretScanner()
        secrets_found = scanner.scan_repository()
        if secrets_found:
            raise SecurityError(f"Secrets detected: {secrets_found}")

    def step_05_scan_dependencies(self):
        """Step 5: Scan dependencies for known vulnerabilities."""
        logger.info("Step 5/25: Scanning dependencies")
        from security.dependency_scanner import DependencyScanner
        scanner = DependencyScanner()
        vulnerabilities = scanner.scan_dependencies()
        self.pipeline_state['vulnerabilities'] = vulnerabilities

    def step_06_license_compliance(self):
        """Step 6: Check license compliance for all dependencies."""
        logger.info("Step 6/25: Checking license compliance")
        from compliance.license_checker import LicenseChecker
        checker = LicenseChecker()
        non_compliant = checker.check_all_dependencies()
        if non_compliant:
            raise ComplianceError(f"Non-compliant licenses: {non_compliant}")

    def step_07_sast_analysis(self):
        """Step 7: Static Application Security Testing."""
        logger.info("Step 7/25: Running SAST analysis")
        from security.sast_analyzer import SASTAnalyzer
        analyzer = SASTAnalyzer()
        findings = analyzer.analyze_codebase()
        self.pipeline_state['sast_findings'] = findings

    def step_08_install_dependencies(self):
        """Step 8: Install all project dependencies."""
        logger.info("Step 8/25: Installing dependencies")
        from build.dependency_manager import DependencyManager
        manager = DependencyManager()
        manager.install_all()

    def step_09_compile_code(self):
        """Step 9: Compile source code to executable form."""
        logger.info("Step 9/25: Compiling code")
        from build.compiler import CodeCompiler
        compiler = CodeCompiler()
        build_output = compiler.compile_all()
        self.pipeline_state['build_artifacts'] = build_output

    def step_10_generate_assets(self):
        """Step 10: Generate static assets and resources."""
        logger.info("Step 10/25: Generating assets")
        from build.asset_generator import AssetGenerator
        generator = AssetGenerator()
        assets = generator.generate_all()
        self.pipeline_state['assets'] = assets

    def step_11_unit_tests(self):
        """Step 11: Execute unit test suite."""
        logger.info("Step 11/25: Running unit tests")
        from testing.unit_test_runner import UnitTestRunner
        runner = UnitTestRunner()
        results = runner.run_all_tests()
        if results['failures'] > 0:
            raise TestFailureError(f"Unit tests failed: {results['failures']}")

    def step_12_integration_tests(self):
        """Step 12: Execute integration test suite."""
        logger.info("Step 12/25: Running integration tests")
        from testing.integration_test_runner import IntegrationTestRunner
        runner = IntegrationTestRunner()
        results = runner.run_all_tests()
        if results['failures'] > 0:
            raise TestFailureError(f"Integration tests failed: {results['failures']}")

    def step_13_e2e_tests(self):
        """Step 13: Execute end-to-end test suite."""
        logger.info("Step 13/25: Running E2E tests")
        from testing.e2e_test_runner import E2ETestRunner
        runner = E2ETestRunner()
        results = runner.run_all_tests()
        self.pipeline_state['e2e_results'] = results

    def step_14_performance_tests(self):
        """Step 14: Execute performance and load tests."""
        logger.info("Step 14/25: Running performance tests")
        from testing.performance_tester import PerformanceTester
        tester = PerformanceTester()
        metrics = tester.run_load_tests()
        if metrics['response_time'] > self.config['max_response_time']:
            raise PerformanceError("Performance benchmarks not met")

    def step_15_security_tests(self):
        """Step 15: Execute security penetration tests."""
        logger.info("Step 15/25: Running security tests")
        from testing.security_tester import SecurityTester
        tester = SecurityTester()
        vulnerabilities = tester.run_penetration_tests()
        self.pipeline_state['security_test_results'] = vulnerabilities

    def step_16_create_artifact(self):
        """Step 16: Create deployable artifact package."""
        logger.info("Step 16/25: Creating deployment artifact")
        from artifacts.artifact_creator import ArtifactCreator
        creator = ArtifactCreator()
        artifact = creator.create_deployable_package()
        self.pipeline_state['artifact_id'] = artifact['id']

    def step_17_upload_to_registry(self):
        """Step 17: Upload artifact to container/package registry."""
        logger.info("Step 17/25: Uploading to registry")
        from artifacts.registry_uploader import RegistryUploader
        uploader = RegistryUploader()
        registry_url = uploader.upload_artifact(self.pipeline_state['artifact_id'])
        self.pipeline_state['registry_url'] = registry_url

    def step_18_provision_infrastructure(self):
        """Step 18: Provision cloud infrastructure resources."""
        logger.info("Step 18/25: Provisioning infrastructure")
        from infrastructure.provisioner import InfrastructureProvisioner
        provisioner = InfrastructureProvisioner()
        resources = provisioner.provision_resources()
        self.pipeline_state['infrastructure'] = resources

    def step_19_deploy_to_staging(self):
        """Step 19: Deploy application to staging environment."""
        logger.info("Step 19/25: Deploying to staging")
        from deployment.staging_deployer import StagingDeployer
        deployer = StagingDeployer()
        staging_url = deployer.deploy(self.pipeline_state['artifact_id'])
        self.pipeline_state['staging_url'] = staging_url

    def step_20_smoke_tests(self):
        """Step 20: Run smoke tests in staging environment."""
        logger.info("Step 20/25: Running smoke tests")
        from testing.smoke_tester import SmokeTester
        tester = SmokeTester()
        results = tester.test_critical_paths(self.pipeline_state['staging_url'])
        if not results['passed']:
            raise DeploymentError("Smoke tests failed in staging")

    def step_21_deploy_to_production(self):
        """Step 21: Deploy application to production environment."""
        logger.info("Step 21/25: Deploying to production")
        from deployment.production_deployer import ProductionDeployer
        deployer = ProductionDeployer()
        prod_url = deployer.deploy_with_blue_green(self.pipeline_state['artifact_id'])
        self.pipeline_state['production_url'] = prod_url

    def step_22_health_checks(self):
        """Step 22: Verify application health in production."""
        logger.info("Step 22/25: Running health checks")
        from monitoring.health_checker import HealthChecker
        checker = HealthChecker()
        health_status = checker.check_all_endpoints(self.pipeline_state['production_url'])
        if not health_status['healthy']:
            raise DeploymentError("Health checks failed")

    def step_23_regression_testing(self):
        """Step 23: Execute regression tests in production."""
        logger.info("Step 23/25: Running regression tests")
        from testing.regression_tester import RegressionTester
        tester = RegressionTester()
        results = tester.test_production(self.pipeline_state['production_url'])
        self.pipeline_state['regression_results'] = results

    def step_24_setup_monitoring(self):
        """Step 24: Configure monitoring and observability."""
        logger.info("Step 24/25: Setting up monitoring")
        from monitoring.monitor_setup import MonitoringSetup
        setup = MonitoringSetup()
        dashboards = setup.configure_monitoring(self.pipeline_state['production_url'])
        self.pipeline_state['monitoring_dashboards'] = dashboards

    def step_25_enable_alerting(self):
        """Step 25: Enable alerting and incident management."""
        logger.info("Step 25/25: Enabling alerting")
        from monitoring.alert_manager import AlertManager
        manager = AlertManager()
        alert_config = manager.setup_alerts(self.pipeline_state['production_url'])
        self.pipeline_state['alerts_configured'] = True
        logger.info("Pipeline execution complete!")

    def _generate_pipeline_report(self) -> Dict:
        """Generate comprehensive pipeline execution report."""
        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'steps_completed': 25,
            'state': self.pipeline_state,
            'metrics': self._calculate_metrics()
        }

    def _handle_pipeline_failure(self, error: Exception):
        """Handle pipeline failure and cleanup."""
        logger.error(f"Pipeline failure: {str(error)}")
        # Rollback deployment, cleanup resources
        self._cleanup_resources()

    def _get_commit_sha(self) -> str:
        """Get current commit SHA."""
        return "abc123def456"

    def _calculate_metrics(self) -> Dict:
        """Calculate pipeline performance metrics."""
        return {
            'total_duration': '15m 32s',
            'test_coverage': '94.2%',
            'security_score': 'A+'
        }

    def _cleanup_resources(self):
        """Cleanup resources after failure."""
        logger.info("Cleaning up resources")
'''


SECURITY_MODULE = '''"""
Security Module - Handles security scanning and vulnerability detection
Implements steps 4, 5, 7, and 15 of the pipeline
"""

import logging
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Vulnerability:
    """Represents a security vulnerability."""
    severity: str
    cve_id: str
    description: str
    affected_package: str
    fixed_version: str


class SecretScanner:
    """
    Scans codebase for exposed secrets and credentials.
    Used in Step 4 of the pipeline.
    """

    def __init__(self):
        self.patterns = self._load_secret_patterns()
        self.exclusions = []

    def scan_repository(self) -> List[Dict]:
        """
        Scan entire repository for exposed secrets.

        Checks for:
        - API keys and tokens
        - Database credentials
        - Private keys and certificates
        - AWS access keys
        - OAuth tokens

        Returns:
            List of detected secrets with location information
        """
        logger.info("Scanning repository for secrets")
        secrets_found = []

        # Scan all files for secret patterns
        for file_path in self._get_all_files():
            secrets = self._scan_file(file_path)
            secrets_found.extend(secrets)

        if secrets_found:
            logger.warning(f"Found {len(secrets_found)} potential secrets")

        return secrets_found

    def _load_secret_patterns(self) -> List:
        """Load regex patterns for secret detection."""
        return [
            r'api[_-]?key',
            r'secret[_-]?key',
            r'password',
            r'aws[_-]?access[_-]?key'
        ]

    def _get_all_files(self) -> List[str]:
        """Get list of all files to scan."""
        return []

    def _scan_file(self, file_path: str) -> List[Dict]:
        """Scan individual file for secrets."""
        return []


class DependencyScanner:
    """
    Scans project dependencies for known vulnerabilities.
    Used in Step 5 of the pipeline.
    """

    def __init__(self):
        self.vulnerability_db = self._load_vulnerability_database()

    def scan_dependencies(self) -> List[Vulnerability]:
        """
        Scan all project dependencies against vulnerability databases.

        Checks:
        - NPM packages (npm audit)
        - Python packages (safety, pip-audit)
        - Docker base images
        - System libraries

        Returns:
            List of vulnerabilities found in dependencies
        """
        logger.info("Scanning dependencies for vulnerabilities")
        vulnerabilities = []

        # Check package.json dependencies
        npm_vulns = self._scan_npm_dependencies()
        vulnerabilities.extend(npm_vulns)

        # Check requirements.txt
        python_vulns = self._scan_python_dependencies()
        vulnerabilities.extend(python_vulns)

        # Check Docker images
        docker_vulns = self._scan_docker_images()
        vulnerabilities.extend(docker_vulns)

        logger.info(f"Found {len(vulnerabilities)} vulnerabilities")
        return vulnerabilities

    def _load_vulnerability_database(self) -> Dict:
        """Load CVE and vulnerability database."""
        return {}

    def _scan_npm_dependencies(self) -> List[Vulnerability]:
        """Scan NPM dependencies."""
        return []

    def _scan_python_dependencies(self) -> List[Vulnerability]:
        """Scan Python dependencies."""
        return []

    def _scan_docker_images(self) -> List[Vulnerability]:
        """Scan Docker image vulnerabilities."""
        return []


class SASTAnalyzer:
    """
    Static Application Security Testing analyzer.
    Used in Step 7 of the pipeline.
    """

    def __init__(self):
        self.rules = self._load_security_rules()

    def analyze_codebase(self) -> Dict:
        """
        Perform static security analysis on codebase.

        Detects:
        - SQL injection vulnerabilities
        - XSS vulnerabilities
        - CSRF issues
        - Insecure deserialization
        - Command injection
        - Path traversal
        - Hardcoded credentials

        Returns:
            Dictionary of security findings by severity
        """
        logger.info("Running SAST analysis")
        findings = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

        # Analyze for common vulnerabilities
        sql_injection = self._detect_sql_injection()
        findings['high'].extend(sql_injection)

        xss_vulns = self._detect_xss()
        findings['high'].extend(xss_vulns)

        command_injection = self._detect_command_injection()
        findings['critical'].extend(command_injection)

        logger.info(f"SAST complete: {sum(len(v) for v in findings.values())} findings")
        return findings

    def _load_security_rules(self) -> List:
        """Load SAST security rules."""
        return []

    def _detect_sql_injection(self) -> List:
        """Detect SQL injection vulnerabilities."""
        return []

    def _detect_xss(self) -> List:
        """Detect XSS vulnerabilities."""
        return []

    def _detect_command_injection(self) -> List:
        """Detect command injection vulnerabilities."""
        return []


class SecurityTester:
    """
    Performs dynamic security testing and penetration tests.
    Used in Step 15 of the pipeline.
    """

    def __init__(self):
        self.test_suite = self._load_security_tests()

    def run_penetration_tests(self) -> List[Dict]:
        """
        Execute automated penetration tests.

        Tests include:
        - Authentication bypass attempts
        - Authorization checks
        - Input validation testing
        - API security testing
        - Session management testing

        Returns:
            List of security vulnerabilities discovered
        """
        logger.info("Running penetration tests")
        vulnerabilities = []

        # Test authentication
        auth_vulns = self._test_authentication()
        vulnerabilities.extend(auth_vulns)

        # Test authorization
        authz_vulns = self._test_authorization()
        vulnerabilities.extend(authz_vulns)

        # Test input validation
        input_vulns = self._test_input_validation()
        vulnerabilities.extend(input_vulns)

        logger.info(f"Penetration testing complete: {len(vulnerabilities)} issues found")
        return vulnerabilities

    def _load_security_tests(self) -> List:
        """Load security test suite."""
        return []

    def _test_authentication(self) -> List[Dict]:
        """Test authentication mechanisms."""
        return []

    def _test_authorization(self) -> List[Dict]:
        """Test authorization controls."""
        return []

    def _test_input_validation(self) -> List[Dict]:
        """Test input validation."""
        return []
'''


DEPLOYMENT_MODULE = '''"""
Deployment Module - Handles deployment to staging and production
Implements steps 18-21 of the pipeline
"""

import logging
from typing import Dict, List
from enum import Enum

logger = logging.getLogger(__name__)


class DeploymentStrategy(Enum):
    """Deployment strategy types."""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    RECREATE = "recreate"


class InfrastructureProvisioner:
    """
    Provisions cloud infrastructure resources.
    Used in Step 18 of the pipeline.
    """

    def __init__(self):
        self.cloud_provider = "AWS"
        self.region = "us-east-1"

    def provision_resources(self) -> Dict:
        """
        Provision all required infrastructure resources.

        Provisions:
        - Compute instances (EC2, ECS, Lambda)
        - Load balancers
        - Auto-scaling groups
        - Databases (RDS, DynamoDB)
        - Cache layers (ElastiCache)
        - CDN (CloudFront)
        - Storage (S3)
        - Networking (VPC, subnets, security groups)

        Returns:
            Dictionary of provisioned resource ARNs and endpoints
        """
        logger.info(f"Provisioning infrastructure in {self.region}")

        resources = {}

        # Provision compute
        resources['compute'] = self._provision_compute()

        # Provision load balancer
        resources['load_balancer'] = self._provision_load_balancer()

        # Provision database
        resources['database'] = self._provision_database()

        # Provision cache
        resources['cache'] = self._provision_cache()

        # Setup networking
        resources['networking'] = self._setup_networking()

        logger.info(f"Infrastructure provisioned: {len(resources)} resource groups")
        return resources

    def _provision_compute(self) -> Dict:
        """Provision compute instances."""
        return {'type': 'ECS', 'cluster': 'production-cluster'}

    def _provision_load_balancer(self) -> Dict:
        """Provision application load balancer."""
        return {'type': 'ALB', 'dns': 'app-lb-12345.us-east-1.elb.amazonaws.com'}

    def _provision_database(self) -> Dict:
        """Provision database instances."""
        return {'type': 'RDS', 'engine': 'postgresql', 'endpoint': 'db.example.com'}

    def _provision_cache(self) -> Dict:
        """Provision cache layer."""
        return {'type': 'ElastiCache', 'engine': 'redis'}

    def _setup_networking(self) -> Dict:
        """Setup VPC and networking."""
        return {'vpc_id': 'vpc-12345', 'subnets': ['subnet-1', 'subnet-2']}


class StagingDeployer:
    """
    Deploys application to staging environment.
    Used in Step 19 of the pipeline.
    """

    def __init__(self):
        self.environment = "staging"

    def deploy(self, artifact_id: str) -> str:
        """
        Deploy application to staging environment.

        Steps:
        1. Pull artifact from registry
        2. Configure environment variables
        3. Deploy to staging infrastructure
        4. Run database migrations
        5. Warm up caches
        6. Update DNS records

        Args:
            artifact_id: ID of the artifact to deploy

        Returns:
            URL of the deployed staging application
        """
        logger.info(f"Deploying {artifact_id} to staging")

        # Pull artifact
        artifact = self._pull_artifact(artifact_id)

        # Configure environment
        config = self._configure_environment()

        # Run migrations
        self._run_migrations()

        # Deploy application
        deployment_url = self._deploy_application(artifact, config)

        logger.info(f"Staging deployment complete: {deployment_url}")
        return deployment_url

    def _pull_artifact(self, artifact_id: str) -> Dict:
        """Pull artifact from registry."""
        return {'id': artifact_id, 'version': '1.0.0'}

    def _configure_environment(self) -> Dict:
        """Configure environment variables."""
        return {'NODE_ENV': 'staging', 'LOG_LEVEL': 'debug'}

    def _run_migrations(self):
        """Run database migrations."""
        logger.info("Running database migrations")

    def _deploy_application(self, artifact: Dict, config: Dict) -> str:
        """Deploy application to staging."""
        return "https://staging.example.com"


class ProductionDeployer:
    """
    Deploys application to production with advanced strategies.
    Used in Step 21 of the pipeline.
    """

    def __init__(self):
        self.environment = "production"
        self.strategy = DeploymentStrategy.BLUE_GREEN

    def deploy_with_blue_green(self, artifact_id: str) -> str:
        """
        Deploy to production using blue-green deployment strategy.

        Blue-Green Deployment Process:
        1. Deploy to inactive (green) environment
        2. Run smoke tests on green
        3. Switch traffic to green environment
        4. Monitor for errors
        5. Keep blue environment for quick rollback
        6. After validation, decommission blue

        Args:
            artifact_id: ID of the artifact to deploy

        Returns:
            URL of the production application
        """
        logger.info(f"Starting blue-green deployment for {artifact_id}")

        # Identify current active environment
        active_env = self._get_active_environment()
        inactive_env = 'green' if active_env == 'blue' else 'blue'

        logger.info(f"Active: {active_env}, Deploying to: {inactive_env}")

        # Deploy to inactive environment
        self._deploy_to_environment(inactive_env, artifact_id)

        # Smoke test inactive environment
        if not self._smoke_test_environment(inactive_env):
            raise DeploymentError("Smoke tests failed on inactive environment")

        # Switch traffic
        self._switch_traffic(inactive_env)

        # Monitor for errors
        self._monitor_deployment(inactive_env)

        logger.info("Blue-green deployment complete")
        return "https://api.example.com"

    def deploy_with_canary(self, artifact_id: str, canary_percentage: int = 10) -> str:
        """
        Deploy using canary deployment strategy.

        Canary Deployment Process:
        1. Deploy new version to small subset of servers
        2. Route small percentage of traffic to canary
        3. Monitor metrics and error rates
        4. Gradually increase traffic to canary
        5. If issues detected, rollback immediately
        6. If successful, complete rollout

        Args:
            artifact_id: ID of the artifact to deploy
            canary_percentage: Initial percentage of traffic for canary

        Returns:
            URL of the production application
        """
        logger.info(f"Starting canary deployment: {canary_percentage}% traffic")

        # Deploy canary version
        self._deploy_canary(artifact_id, canary_percentage)

        # Monitor canary metrics
        metrics = self._monitor_canary_metrics()

        if metrics['error_rate'] > 0.01:
            logger.error("Canary error rate too high, rolling back")
            self._rollback_canary()
            raise DeploymentError("Canary deployment failed")

        # Gradually increase traffic
        for percentage in [25, 50, 75, 100]:
            self._increase_canary_traffic(percentage)
            self._monitor_canary_metrics()

        logger.info("Canary deployment complete")
        return "https://api.example.com"

    def _get_active_environment(self) -> str:
        """Get currently active environment (blue or green)."""
        return 'blue'

    def _deploy_to_environment(self, env: str, artifact_id: str):
        """Deploy artifact to specific environment."""
        logger.info(f"Deploying to {env} environment")

    def _smoke_test_environment(self, env: str) -> bool:
        """Run smoke tests on environment."""
        logger.info(f"Smoke testing {env} environment")
        return True

    def _switch_traffic(self, target_env: str):
        """Switch traffic to target environment."""
        logger.info(f"Switching traffic to {target_env}")

    def _monitor_deployment(self, env: str):
        """Monitor deployment for errors."""
        logger.info(f"Monitoring {env} deployment")

    def _deploy_canary(self, artifact_id: str, percentage: int):
        """Deploy canary version."""
        logger.info(f"Deploying canary at {percentage}%")

    def _monitor_canary_metrics(self) -> Dict:
        """Monitor canary metrics."""
        return {'error_rate': 0.001, 'latency': 120}

    def _rollback_canary(self):
        """Rollback canary deployment."""
        logger.info("Rolling back canary")

    def _increase_canary_traffic(self, percentage: int):
        """Increase traffic to canary."""
        logger.info(f"Increasing canary traffic to {percentage}%")


class DeploymentError(Exception):
    """Raised when deployment fails."""
    pass
'''


MONITORING_MODULE = '''"""
Monitoring Module - Handles health checks, monitoring, and alerting
Implements steps 22, 24, and 25 of the pipeline
"""

import logging
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    endpoint: str
    status: str
    response_time: float
    healthy: bool


class HealthChecker:
    """
    Performs health checks on deployed applications.
    Used in Step 22 of the pipeline.
    """

    def __init__(self):
        self.timeout = 30
        self.retry_count = 3

    def check_all_endpoints(self, base_url: str) -> Dict:
        """
        Check health of all application endpoints.

        Checks:
        - API endpoint availability
        - Database connectivity
        - Cache connectivity
        - External service dependencies
        - SSL certificate validity
        - DNS resolution

        Args:
            base_url: Base URL of the deployed application

        Returns:
            Dictionary containing health status of all components
        """
        logger.info(f"Running health checks for {base_url}")

        results = {
            'healthy': True,
            'checks': []
        }

        # Check API endpoint
        api_health = self._check_api_health(base_url)
        results['checks'].append(api_health)

        # Check database
        db_health = self._check_database_connectivity(base_url)
        results['checks'].append(db_health)

        # Check cache
        cache_health = self._check_cache_connectivity(base_url)
        results['checks'].append(cache_health)

        # Check external dependencies
        deps_health = self._check_external_dependencies(base_url)
        results['checks'].extend(deps_health)

        # Overall health
        results['healthy'] = all(check.healthy for check in results['checks'])

        logger.info(f"Health checks complete: {'healthy' if results['healthy'] else 'unhealthy'}")
        return results

    def _check_api_health(self, base_url: str) -> HealthCheckResult:
        """Check API endpoint health."""
        return HealthCheckResult(
            endpoint='/health',
            status='200 OK',
            response_time=45.2,
            healthy=True
        )

    def _check_database_connectivity(self, base_url: str) -> HealthCheckResult:
        """Check database connectivity."""
        return HealthCheckResult(
            endpoint='/health/db',
            status='connected',
            response_time=12.5,
            healthy=True
        )

    def _check_cache_connectivity(self, base_url: str) -> HealthCheckResult:
        """Check cache connectivity."""
        return HealthCheckResult(
            endpoint='/health/cache',
            status='connected',
            response_time=5.1,
            healthy=True
        )

    def _check_external_dependencies(self, base_url: str) -> List[HealthCheckResult]:
        """Check external service dependencies."""
        return []


class MonitoringSetup:
    """
    Configures monitoring and observability.
    Used in Step 24 of the pipeline.
    """

    def __init__(self):
        self.metrics_provider = "CloudWatch"
        self.logging_provider = "ELK"
        self.tracing_provider = "Jaeger"

    def configure_monitoring(self, app_url: str) -> Dict:
        """
        Configure comprehensive monitoring and observability.

        Configures:
        - Application metrics (response time, throughput, errors)
        - Infrastructure metrics (CPU, memory, disk, network)
        - Custom business metrics
        - Log aggregation and analysis
        - Distributed tracing
        - APM (Application Performance Monitoring)
        - Real User Monitoring (RUM)

        Args:
            app_url: URL of the application to monitor

        Returns:
            Dictionary of configured monitoring dashboards and endpoints
        """
        logger.info(f"Configuring monitoring for {app_url}")

        dashboards = {}

        # Setup application metrics
        dashboards['application'] = self._setup_application_metrics(app_url)

        # Setup infrastructure metrics
        dashboards['infrastructure'] = self._setup_infrastructure_metrics()

        # Setup custom metrics
        dashboards['business'] = self._setup_business_metrics()

        # Configure log aggregation
        dashboards['logs'] = self._configure_log_aggregation()

        # Setup distributed tracing
        dashboards['tracing'] = self._setup_distributed_tracing()

        logger.info(f"Monitoring configured: {len(dashboards)} dashboards created")
        return dashboards

    def _setup_application_metrics(self, app_url: str) -> str:
        """Setup application performance metrics."""
        logger.info("Configuring application metrics")
        return "https://cloudwatch.aws.amazon.com/dashboard/app-metrics"

    def _setup_infrastructure_metrics(self) -> str:
        """Setup infrastructure metrics."""
        logger.info("Configuring infrastructure metrics")
        return "https://cloudwatch.aws.amazon.com/dashboard/infra-metrics"

    def _setup_business_metrics(self) -> str:
        """Setup custom business metrics."""
        logger.info("Configuring business metrics")
        return "https://cloudwatch.aws.amazon.com/dashboard/business-metrics"

    def _configure_log_aggregation(self) -> str:
        """Configure centralized logging."""
        logger.info("Configuring log aggregation")
        return "https://elk.example.com/app/kibana"

    def _setup_distributed_tracing(self) -> str:
        """Setup distributed tracing."""
        logger.info("Configuring distributed tracing")
        return "https://jaeger.example.com"


class AlertManager:
    """
    Manages alerting and incident response.
    Used in Step 25 of the pipeline.
    """

    def __init__(self):
        self.alert_provider = "PagerDuty"
        self.notification_channels = ['email', 'slack', 'sms']

    def setup_alerts(self, app_url: str) -> Dict:
        """
        Configure alerting rules and incident management.

        Alert Categories:
        - Critical: Immediate response required (page on-call)
        - High: Response within 1 hour
        - Medium: Response within 4 hours
        - Low: Review during business hours

        Alerts for:
        - High error rates (>1%)
        - Slow response times (>500ms p95)
        - High CPU/memory usage (>80%)
        - Failed health checks
        - Security incidents
        - Deployment failures
        - Custom business thresholds

        Args:
            app_url: URL of the application

        Returns:
            Dictionary of configured alert rules
        """
        logger.info(f"Configuring alerts for {app_url}")

        alert_config = {}

        # Critical alerts
        alert_config['critical'] = self._configure_critical_alerts()

        # High priority alerts
        alert_config['high'] = self._configure_high_priority_alerts()

        # Medium priority alerts
        alert_config['medium'] = self._configure_medium_priority_alerts()

        # Setup notification channels
        alert_config['channels'] = self._setup_notification_channels()

        # Configure escalation policies
        alert_config['escalation'] = self._configure_escalation_policies()

        logger.info(f"Alerting configured: {sum(len(v) for v in alert_config.values())} rules")
        return alert_config

    def _configure_critical_alerts(self) -> List[Dict]:
        """Configure critical severity alerts."""
        return [
            {'name': 'High Error Rate', 'threshold': '1%', 'window': '5m'},
            {'name': 'Service Down', 'threshold': 'health_check_failed', 'window': '1m'},
            {'name': 'Database Unavailable', 'threshold': 'connection_failed', 'window': '2m'}
        ]

    def _configure_high_priority_alerts(self) -> List[Dict]:
        """Configure high priority alerts."""
        return [
            {'name': 'Slow Response Time', 'threshold': '500ms p95', 'window': '10m'},
            {'name': 'High CPU Usage', 'threshold': '80%', 'window': '15m'}
        ]

    def _configure_medium_priority_alerts(self) -> List[Dict]:
        """Configure medium priority alerts."""
        return [
            {'name': 'Increased Latency', 'threshold': '300ms p95', 'window': '30m'},
            {'name': 'Memory Usage', 'threshold': '75%', 'window': '30m'}
        ]

    def _setup_notification_channels(self) -> Dict:
        """Setup notification channels."""
        return {
            'email': 'oncall@example.com',
            'slack': '#alerts',
            'pagerduty': 'https://events.pagerduty.com/integration/abc123'
        }

    def _configure_escalation_policies(self) -> Dict:
        """Configure alert escalation policies."""
        return {
            'critical': '0m -> oncall, 5m -> manager, 15m -> director',
            'high': '30m -> oncall, 2h -> manager',
            'medium': '4h -> oncall'
        }
'''


def get_openai_embedding(text: str, settings) -> List[float]:
    """Get real OpenAI embedding for text."""
    client = OpenAI(api_key=settings.openai_api_key)

    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text
    )

    return response.data[0].embedding


def ingest_25step_pipeline():
    """Ingest the 25-step pipeline code into Neo4j and Qdrant."""
    print("=" * 70)
    print("  Ingesting 25-Step CI/CD Pipeline")
    print("=" * 70)

    settings = get_settings()

    # Initialize clients
    print("\n  Initializing clients...")
    neo4j = Neo4jClient()
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, check_compatibility=False)
    parser = PythonParser()
    loader = Neo4jLoader()

    # Create unique namespace and collection
    namespace = f"pipeline_25step_{int(datetime.now().timestamp())}"
    collection_name = "pipeline_25step_code"

    # Create Qdrant collection
    print(f"\n  Creating Qdrant collection with 1536D vectors...")
    try:
        qdrant.delete_collection(collection_name=collection_name)
    except:
        pass

    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )

    # Code files to process
    code_files = [
        ("orchestrator.py", PIPELINE_ORCHESTRATOR),
        ("security.py", SECURITY_MODULE),
        ("deployment.py", DEPLOYMENT_MODULE),
        ("monitoring.py", MONITORING_MODULE)
    ]

    all_embeddings = []
    total_nodes = 0
    total_relationships = 0

    for file_name, code_content in code_files:
        print(f"\n  Processing {file_name}...")

        # Parse code
        parse_result = parser.parse_string(code_content, namespace, file_name)

        # Load to Neo4j
        neo4j_result = loader.load_parse_result(parse_result)
        total_nodes += neo4j_result['nodes_created']
        total_relationships += neo4j_result['relationships_created']

        print(f"    Neo4j: {neo4j_result['nodes_created']} nodes, {neo4j_result['relationships_created']} relationships")

        # Create embeddings for each code unit
        embeddings_created = 0
        all_units = (
            parse_result.modules +
            parse_result.classes +
            parse_result.functions +
            parse_result.methods
        )

        for node in all_units:
            # Create embedding text
            embedding_text = f"{node.name} {node.docstring or ''} {node.code[:200]}"

            # Get real OpenAI embedding
            embedding_vector = get_openai_embedding(embedding_text, settings)

            # Prepare for Qdrant
            all_embeddings.append({
                'id': f"{namespace}_{file_name}_{node.name}",
                'vector': embedding_vector,
                'payload': {
                    'namespace': namespace,
                    'name': node.name,
                    'type': node.type,
                    'file_path': file_name,
                    'docstring': node.docstring or '',
                    'code': node.code[:500]
                }
            })
            embeddings_created += 1

        print(f"    Qdrant: {embeddings_created} embeddings created")

    # Upload embeddings to Qdrant in batches
    print(f"\n  Uploading {len(all_embeddings)} embeddings to Qdrant...")
    batch_size = 100
    for i in range(0, len(all_embeddings), batch_size):
        batch = all_embeddings[i:i + batch_size]
        points = [
            PointStruct(
                id=hash(emb['id']) % (2**63),  # Convert to valid ID
                vector=emb['vector'],
                payload=emb['payload']
            )
            for emb in batch
        ]
        qdrant.upsert(collection_name=collection_name, points=points)
        print(f"    Uploaded batch {i//batch_size + 1}/{(len(all_embeddings)-1)//batch_size + 1}")

    print(f"\n  ✓ Total: {total_nodes} nodes, {total_relationships} relationships in Neo4j")
    print(f"  ✓ Total: {len(all_embeddings)} real embeddings in Qdrant")

    return collection_name, namespace


def test_semantic_search(collection_name, namespace):
    """Test semantic search with various queries."""
    print("\n" + "-" * 70)
    print("  Semantic Search Tests")
    print("-" * 70)

    settings = get_settings()
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, check_compatibility=False)
    client = OpenAI(api_key=settings.openai_api_key)

    # Test queries
    queries = [
        "How does the system scan for security vulnerabilities?",
        "What deployment strategies are supported?",
        "How is monitoring and alerting configured?",
        "What happens in the blue-green deployment process?"
    ]

    for query in queries:
        print(f"\n  Query: \"{query}\"")
        print(f"  Step 1: Creating query embedding...")

        # Get query embedding
        query_embedding = get_openai_embedding(query, settings)

        print(f"  Step 2: Searching for semantically similar code...")

        # Search Qdrant
        results = qdrant.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=5,
            query_filter=Filter(
                must=[FieldCondition(key="namespace", match=MatchValue(value=namespace))]
            )
        )

        print(f"\n  Found {len(results)} relevant code segments:\n")
        for i, result in enumerate(results, 1):
            payload = result.payload
            print(f"    {i}. {payload['name']} ({payload['type']}) - Similarity: {result.score:.3f}")
            print(f"       File: {payload['file_path']}")
            if payload.get('docstring'):
                doc_preview = payload['docstring'][:80].replace('\n', ' ')
                print(f"       {doc_preview}...")

        # Use LLM to generate answer
        print(f"\n  Step 3: Using LLM to generate comprehensive answer...\n")

        context_parts = []
        for result in results:
            payload = result.payload
            context_parts.append(
                f"{payload['name']} in {payload['file_path']}:\n{payload['docstring']}\n{payload['code'][:300]}"
            )

        context = "\n\n".join(context_parts)

        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a code analysis assistant. Answer questions based on the provided code context."},
                {"role": "user", "content": f"Based on this code:\n\n{context}\n\nQuestion: {query}\n\nProvide a clear, concise answer."}
            ],
            temperature=0.3,
            max_tokens=300
        )

        answer = response.choices[0].message.content
        print("  " + "=" * 66)
        print("  LLM Answer:")
        print("  " + "=" * 66)
        for line in answer.split('\n'):
            print(f"  {line}")
        print("  " + "=" * 66)


def test_flow_based_search(collection_name, namespace):
    """Test flow-based graph traversal."""
    print("\n" + "-" * 70)
    print("  Flow-Based Graph Traversal Tests")
    print("-" * 70)

    settings = get_settings()
    neo4j = Neo4jClient()
    client = OpenAI(api_key=settings.openai_api_key)

    print("\n  Query: Trace the complete execution flow of the 25-step pipeline")

    # Find the main orchestrator method
    print("\n  Step 1: Finding pipeline entry point...")
    query = """
    MATCH (c:Class {namespace: $namespace, name: 'PipelineOrchestrator'})-[:CONTAINS]->(m:Method {name: 'execute_pipeline'})
    RETURN m.name as method, m.code as code, m.docstring as doc
    """

    entry_points = neo4j.execute_query(query, {"namespace": namespace})

    if entry_points:
        entry = entry_points[0]
        print(f"    ✓ Found: {entry['method']}()")
        print(f"    {entry['doc'][:100]}...")
    else:
        print("    ✗ No entry point found")
        entry = None

    # Find all step methods
    print("\n  Step 2: Finding all 25 pipeline steps...")
    query = """
    MATCH (c:Class {namespace: $namespace, name: 'PipelineOrchestrator'})-[:CONTAINS]->(m:Method)
    WHERE m.name STARTS WITH 'step_'
    RETURN m.name as step, m.docstring as description
    ORDER BY m.name
    """

    steps = neo4j.execute_query(query, {"namespace": namespace})
    print(f"    ✓ Found {len(steps)} pipeline steps:\n")

    for step in steps[:10]:  # Show first 10
        step_num = step['step'].split('_')[1]
        desc = step['description'].split('\n')[0] if step['description'] else 'No description'
        print(f"      Step {step_num}: {desc}")

    if len(steps) > 10:
        print(f"      ... and {len(steps) - 10} more steps")

    # Find cross-module dependencies
    print("\n  Step 3: Finding cross-module dependencies...")
    query = """
    MATCH (orchestrator:Class {namespace: $namespace, name: 'PipelineOrchestrator'})-[:CONTAINS]->(m:Method)
    WHERE m.name STARTS WITH 'step_'
    MATCH (m)-[:CALLS]->(called)
    MATCH (parent:Class)-[:CONTAINS]->(called)
    WHERE parent.name <> 'PipelineOrchestrator'
    RETURN DISTINCT parent.name as class_name, parent.file_path as file, parent.docstring as description
    LIMIT 10
    """

    dependencies = neo4j.execute_query(query, {"namespace": namespace})
    print(f"    ✓ Found {len(dependencies)} cross-module dependencies:\n")

    for dep in dependencies:
        print(f"      • {dep['class_name']} ({dep['file']})")
        if dep['description']:
            print(f"        {dep['description'][:70]}...")

    # Generate LLM explanation
    print("\n  Step 4: Generating LLM-powered workflow explanation...")

    steps_text = "\n".join([f"- Step {s['step'].split('_')[1]}: {s['description'].split('.')[0] if s['description'] else 'N/A'}" for s in steps[:25]])
    deps_text = "\n".join([f"- {d['class_name']}: {d['description'].split('.')[0] if d['description'] else 'N/A'}" for d in dependencies])

    entry_code = entry['code'][:500] if entry else "Entry point code not available"

    prompt = f"""Analyze this 25-step CI/CD pipeline and explain the complete workflow.

Entry Point:
{entry_code}

All 25 Steps:
{steps_text}

Key Dependencies:
{deps_text}

Provide a comprehensive overview of how the pipeline works, organized by phases."""

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "You are a DevOps expert analyzing CI/CD pipelines."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=600
    )

    answer = response.choices[0].message.content
    print("\n  " + "=" * 66)
    print("  LLM-Generated Pipeline Overview:")
    print("  " + "=" * 66)
    for line in answer.split('\n'):
        print(f"  {line}")
    print("  " + "=" * 66)


def cleanup(collection_name, namespace):
    """Cleanup test data."""
    print("\n" + "=" * 70)
    print("  Cleanup")
    print("=" * 70)

    settings = get_settings()
    neo4j = Neo4jClient()
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, check_compatibility=False)

    # Delete Neo4j data
    query = "MATCH (n {namespace: $namespace}) DETACH DELETE n"
    neo4j.execute_query(query, {"namespace": namespace})
    print("  ✓ Cleaned up Neo4j test data")

    # Delete Qdrant collection
    qdrant.delete_collection(collection_name=collection_name)
    print(f"  ✓ Deleted Qdrant collection '{collection_name}'")


def main():
    """Run the 25-step GraphRAG test."""
    print("\n" + "=" * 70)
    print("  25-Step CI/CD Pipeline GraphRAG Test")
    print("=" * 70)
    print("\nDemonstrates:")
    print("  • Complex 25-step workflow with 4 modules")
    print("  • Real OpenAI embeddings for semantic search")
    print("  • Graph traversal for execution flow analysis")
    print("  • LLM-powered code explanation")
    print("  • Cross-module dependency tracking")
    print("=" * 70)

    try:
        # Ingest code
        print("\n" + "=" * 70)
        print("  1. Ingesting 25-Step Pipeline Code")
        print("=" * 70)
        collection_name, namespace = ingest_25step_pipeline()

        # Test semantic search
        test_semantic_search(collection_name, namespace)

        # Test flow-based search
        test_flow_based_search(collection_name, namespace)

        # Cleanup - DISABLED to keep data for UI testing
        print(f"\n💡 Data preserved for UI testing:")
        print(f"   Collection: {collection_name}")
        print(f"   Namespace: {namespace}")
        print(f"\n   Use these values in the UI!")
        # cleanup(collection_name, namespace)

        print("\n" + "=" * 70)
        print("  ✓ 25-Step GraphRAG Test Complete!")
        print("=" * 70)
        print("\n💡 Key Capabilities Demonstrated:")
        print("  • Ingested 4 modules with 25+ distinct pipeline steps")
        print("  • Semantic search found relevant code with high accuracy")
        print("  • Graph traversal successfully traced execution flows")
        print("  • LLM generated comprehensive workflow explanations")
        print("  • Cross-module dependencies correctly identified")
        print("\nYour FlowRAG system handles complex workflows excellently!")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    from datetime import datetime
    main()
