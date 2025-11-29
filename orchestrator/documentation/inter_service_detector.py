"""
Inter-Service Call Detector.

Detects external service calls in code (HTTP, gRPC, message queues, etc.)
for comprehensive service documentation.

Documentation Agent is responsible for this module.
"""

from typing import List, Dict, Any, Optional
import re
import logging
from databases import get_neo4j_client

logger = logging.getLogger(__name__)


class ServiceCall:
    """Represents a detected inter-service call."""

    def __init__(
        self,
        call_type: str,  # http, grpc, kafka, rabbitmq, redis, etc.
        source_file: str,
        source_function: str,
        target_service: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,  # GET, POST, etc.
        line_number: Optional[int] = None,
        code_snippet: Optional[str] = None,
    ):
        self.call_type = call_type
        self.source_file = source_file
        self.source_function = source_function
        self.target_service = target_service
        self.endpoint = endpoint
        self.method = method
        self.line_number = line_number
        self.code_snippet = code_snippet

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "call_type": self.call_type,
            "source_file": self.source_file,
            "source_function": self.source_function,
            "target_service": self.target_service,
            "endpoint": self.endpoint,
            "method": self.method,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
        }


class InterServiceCallDetector:
    """Detector for inter-service calls in code."""

    # HTTP client patterns
    HTTP_PATTERNS = [
        # JavaScript/TypeScript
        r"(?:axios|fetch|http|request|superagent)\.(?:get|post|put|delete|patch)",
        r"fetch\s*\(['\"](?P<url>https?://[^'\"]+)",
        r"axios\s*\.\s*(?P<method>get|post|put|delete|patch)\s*\(['\"](?P<url>[^'\"]+)",

        # Python
        r"requests\.(?P<method>get|post|put|delete|patch)\s*\(['\"](?P<url>[^'\"]+)",
        r"urllib\.request\.urlopen\s*\(['\"](?P<url>[^'\"]+)",
        r"http\.client\.HTTP(?:S)?Connection\s*\(['\"](?P<host>[^'\"]+)",

        # Java
        r"HttpClient\.(?:newBuilder|newHttpClient)",
        r"RestTemplate\.(?P<method>getForEntity|postForEntity|exchange)",
        r"WebClient\.(?:create|builder)",

        # Go
        r"http\.(?:Get|Post|Head|Put|Patch|Delete)\s*\(['\"](?P<url>[^'\"]+)",
        r"client\.Do\s*\(",
    ]

    # gRPC patterns
    GRPC_PATTERNS = [
        r"grpc\.(?:dial|Dial|NewClient)",
        r"@grpc\.unary_unary",
        r"stub\s*=\s*\w+Stub\(",
        r"grpc\.Channel\(",
    ]

    # Message queue patterns
    KAFKA_PATTERNS = [
        r"KafkaProducer\(",
        r"KafkaConsumer\(",
        r"producer\.send\s*\(['\"](?P<topic>[^'\"]+)",
        r"@kafka\.(?:producer|consumer)",
    ]

    RABBITMQ_PATTERNS = [
        r"pika\.BlockingConnection",
        r"channel\.basic_publish\s*\(.*?routing_key\s*=\s*['\"](?P<queue>[^'\"]+)",
        r"channel\.queue_declare\s*\(['\"](?P<queue>[^'\"]+)",
    ]

    # Redis patterns
    REDIS_PATTERNS = [
        r"redis\.Redis\(",
        r"Redis\.from_url\(",
        r"redis\.createClient\(",
    ]

    # Database patterns (external DBs)
    DB_PATTERNS = [
        r"psycopg2\.connect\(",
        r"mysql\.connector\.connect\(",
        r"MongoClient\(",
        r"sqlite3\.connect\(",
    ]

    def __init__(self):
        """Initialize detector."""
        self.neo4j_client = get_neo4j_client()

    def detect_service_calls(self, namespace: str) -> List[ServiceCall]:
        """
        Detect all inter-service calls in a namespace.

        Args:
            namespace: Namespace to analyze

        Returns:
            List of detected service calls
        """
        logger.info(f"Detecting inter-service calls in namespace: {namespace}")

        service_calls = []

        # Get all code from Neo4j
        query = """
        MATCH (n)
        WHERE n.namespace = $namespace
          AND n.code IS NOT NULL
          AND (n.type = 'function' OR n.type = 'method' OR n.type = 'class')
        RETURN n.file_path as file_path,
               n.name as name,
               n.code as code,
               n.line_start as line_start,
               n.type as type
        LIMIT 1000
        """

        try:
            results = self.neo4j_client.execute_query(query, {"namespace": namespace})
            logger.info(f"Analyzing {len(results)} code units for service calls")

            for result in results:
                file_path = result.get("file_path", "")
                name = result.get("name", "")
                code = result.get("code", "")
                line_start = result.get("line_start", 0)

                if not code:
                    continue

                # Detect HTTP calls
                service_calls.extend(
                    self._detect_http_calls(file_path, name, code, line_start)
                )

                # Detect gRPC calls
                service_calls.extend(
                    self._detect_grpc_calls(file_path, name, code, line_start)
                )

                # Detect Kafka calls
                service_calls.extend(
                    self._detect_kafka_calls(file_path, name, code, line_start)
                )

                # Detect RabbitMQ calls
                service_calls.extend(
                    self._detect_rabbitmq_calls(file_path, name, code, line_start)
                )

                # Detect Redis calls
                service_calls.extend(
                    self._detect_redis_calls(file_path, name, code, line_start)
                )

                # Detect database calls
                service_calls.extend(
                    self._detect_database_calls(file_path, name, code, line_start)
                )

        except Exception as e:
            logger.error(f"Failed to detect service calls: {e}", exc_info=True)

        logger.info(f"Detected {len(service_calls)} inter-service calls")
        return service_calls

    def _detect_http_calls(
        self, file_path: str, function_name: str, code: str, line_start: int
    ) -> List[ServiceCall]:
        """Detect HTTP client calls."""
        calls = []

        for pattern in self.HTTP_PATTERNS:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                # Extract URL and method if available
                url = None
                method = None

                if "url" in match.groupdict():
                    url = match.group("url")

                if "method" in match.groupdict():
                    method = match.group("method").upper()

                # Extract line number
                line_num = code[:match.start()].count("\n") + line_start

                # Extract code snippet
                snippet = self._extract_snippet(code, match.start(), match.end())

                # Try to infer target service from URL
                target_service = self._infer_service_from_url(url) if url else None

                calls.append(
                    ServiceCall(
                        call_type="http",
                        source_file=file_path,
                        source_function=function_name,
                        target_service=target_service,
                        endpoint=url,
                        method=method,
                        line_number=line_num,
                        code_snippet=snippet,
                    )
                )

        return calls

    def _detect_grpc_calls(
        self, file_path: str, function_name: str, code: str, line_start: int
    ) -> List[ServiceCall]:
        """Detect gRPC calls."""
        calls = []

        for pattern in self.GRPC_PATTERNS:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count("\n") + line_start
                snippet = self._extract_snippet(code, match.start(), match.end())

                calls.append(
                    ServiceCall(
                        call_type="grpc",
                        source_file=file_path,
                        source_function=function_name,
                        line_number=line_num,
                        code_snippet=snippet,
                    )
                )

        return calls

    def _detect_kafka_calls(
        self, file_path: str, function_name: str, code: str, line_start: int
    ) -> List[ServiceCall]:
        """Detect Kafka calls."""
        calls = []

        for pattern in self.KAFKA_PATTERNS:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count("\n") + line_start
                snippet = self._extract_snippet(code, match.start(), match.end())

                # Extract topic name if available
                topic = None
                if "topic" in match.groupdict():
                    topic = match.group("topic")

                calls.append(
                    ServiceCall(
                        call_type="kafka",
                        source_file=file_path,
                        source_function=function_name,
                        endpoint=topic,
                        line_number=line_num,
                        code_snippet=snippet,
                    )
                )

        return calls

    def _detect_rabbitmq_calls(
        self, file_path: str, function_name: str, code: str, line_start: int
    ) -> List[ServiceCall]:
        """Detect RabbitMQ calls."""
        calls = []

        for pattern in self.RABBITMQ_PATTERNS:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count("\n") + line_start
                snippet = self._extract_snippet(code, match.start(), match.end())

                # Extract queue name if available
                queue = None
                if "queue" in match.groupdict():
                    queue = match.group("queue")

                calls.append(
                    ServiceCall(
                        call_type="rabbitmq",
                        source_file=file_path,
                        source_function=function_name,
                        endpoint=queue,
                        line_number=line_num,
                        code_snippet=snippet,
                    )
                )

        return calls

    def _detect_redis_calls(
        self, file_path: str, function_name: str, code: str, line_start: int
    ) -> List[ServiceCall]:
        """Detect Redis calls."""
        calls = []

        for pattern in self.REDIS_PATTERNS:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count("\n") + line_start
                snippet = self._extract_snippet(code, match.start(), match.end())

                calls.append(
                    ServiceCall(
                        call_type="redis",
                        source_file=file_path,
                        source_function=function_name,
                        line_number=line_num,
                        code_snippet=snippet,
                    )
                )

        return calls

    def _detect_database_calls(
        self, file_path: str, function_name: str, code: str, line_start: int
    ) -> List[ServiceCall]:
        """Detect external database calls."""
        calls = []

        for pattern in self.DB_PATTERNS:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count("\n") + line_start
                snippet = self._extract_snippet(code, match.start(), match.end())

                # Infer database type from pattern
                db_type = "database"
                if "psycopg2" in match.group():
                    db_type = "postgresql"
                elif "mysql" in match.group():
                    db_type = "mysql"
                elif "MongoClient" in match.group():
                    db_type = "mongodb"
                elif "sqlite3" in match.group():
                    db_type = "sqlite"

                calls.append(
                    ServiceCall(
                        call_type=db_type,
                        source_file=file_path,
                        source_function=function_name,
                        line_number=line_num,
                        code_snippet=snippet,
                    )
                )

        return calls

    def _extract_snippet(self, code: str, start: int, end: int, context: int = 100) -> str:
        """Extract code snippet with context."""
        snippet_start = max(0, start - context)
        snippet_end = min(len(code), end + context)
        return code[snippet_start:snippet_end].strip()

    def _infer_service_from_url(self, url: str) -> Optional[str]:
        """Try to infer service name from URL."""
        if not url:
            return None

        # Extract domain/service name from URL
        # Examples:
        # - https://api.payment.com/... -> payment
        # - http://user-service:8080/... -> user-service
        # - https://backend.example.com/api/... -> backend

        # Remove protocol
        url_without_protocol = re.sub(r"^https?://", "", url)

        # Extract domain
        domain = url_without_protocol.split("/")[0]

        # Remove port
        domain = domain.split(":")[0]

        # Extract service name (first part of domain)
        parts = domain.split(".")
        if len(parts) > 0:
            return parts[0]

        return None


def get_inter_service_detector() -> InterServiceCallDetector:
    """Get inter-service call detector instance."""
    return InterServiceCallDetector()
