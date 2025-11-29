"""
Service Dependency Extractor - Extracts cross-service API calls.

Analyzes code to detect HTTP/REST API calls to other microservices
and creates CALLS_API relationships for cross-namespace queries.

Ingestion Agent is responsible for this module.
"""

import re
import hashlib
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class ServiceDependencyExtractor:
    """Extracts cross-service dependencies from code."""

    def __init__(self, service_mappings: Optional[Dict[str, str]] = None,
                 config_file: Optional[str] = None):
        """
        Initialize the extractor.

        Args:
            service_mappings: Optional dictionary mapping service identifiers to namespaces
                             Format: {'service_key': 'namespace', ...}
            config_file: Optional path to JSON config file with service mappings
        """
        self.api_calls = []
        self.service_url_mappings = {}

        # Load service mappings from config file if provided
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.service_url_mappings = config.get('service_mappings', {})
                    logger.info(f"Loaded {len(self.service_url_mappings)} service mappings from {config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")

        # Override with explicit mappings if provided
        if service_mappings:
            self.service_url_mappings.update(service_mappings)

        # If no mappings provided, log a warning
        if not self.service_url_mappings:
            logger.warning(
                "No service mappings configured. Cross-service API detection will be limited. "
                "Provide service_mappings dict or config_file to improve detection."
            )

    def extract_api_calls_from_code(
        self,
        code: str,
        file_path: str,
        namespace: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """
        Extract API calls from source code.

        Args:
            code: Source code content
            file_path: Path to source file
            namespace: Current namespace
            language: Programming language

        Returns:
            List of API call dictionaries
        """
        api_calls = []

        if language in ['dart', 'flutter']:
            api_calls.extend(self._extract_dart_api_calls(code, file_path, namespace))
        elif language in ['typescript', 'javascript', 'ts', 'js']:
            api_calls.extend(self._extract_typescript_api_calls(code, file_path, namespace))
        elif language == 'python':
            api_calls.extend(self._extract_python_api_calls(code, file_path, namespace))

        return api_calls

    def _extract_dart_api_calls(
        self, code: str, file_path: str, namespace: str
    ) -> List[Dict[str, Any]]:
        """Extract API calls from Dart/Flutter code."""
        api_calls = []

        # Pattern 1: http.get/post with Uri.parse (handles multi-line formatting)
        # Example: await http\n    .get(\n      Uri.parse('$_baseUrl/api/getAllPendingOrders'), ...)
        pattern1 = r'http\s*\.\s*(get|post|put|delete|patch)\s*\(\s*Uri\.parse\s*\(\s*["\']([^"\']+)["\']\s*\)'

        for match in re.finditer(pattern1, code, re.MULTILINE | re.DOTALL):
            http_method = match.group(1).upper()
            url_template = match.group(2)

            # Extract baseUrl if used
            base_url = self._extract_dart_base_url(code)
            target_service, clean_url = self._resolve_service_from_url(url_template, base_url)

            if target_service:
                # Find function containing this call
                line_num = code[:match.start()].count('\n') + 1
                function_name = self._find_containing_function(code, match.start())

                api_call = {
                    'source_namespace': namespace,
                    'source_file': file_path,
                    'source_function': function_name or 'unknown',
                    'target_service': target_service,
                    'target_url': clean_url,
                    'http_method': http_method,
                    'line_number': line_num,
                    'auth_type': self._detect_dart_auth_type(code),
                }
                api_calls.append(api_call)

        # Pattern 2: Environment variable based URLs
        # Example: dotenv.env['SHOP_DATA_PROVIDER_URL']
        env_url_pattern = r'dotenv\.env\[["\']([A-Z_]+_URL)["\']\]'
        for match in re.finditer(env_url_pattern, code):
            env_var = match.group(1)
            target_service = self._map_env_var_to_service(env_var)
            if target_service:
                line_num = code[:match.start()].count('\n') + 1
                function_name = self._find_containing_function(code, match.start())

                # Look for nearby HTTP call
                surrounding_code = code[match.start():min(len(code), match.start() + 500)]
                method_match = re.search(r'http\.(get|post|put|delete|patch)', surrounding_code)
                http_method = method_match.group(1).upper() if method_match else 'GET'

                api_call = {
                    'source_namespace': namespace,
                    'source_file': file_path,
                    'source_function': function_name or 'unknown',
                    'target_service': target_service,
                    'target_url': env_var,
                    'http_method': http_method,
                    'line_number': line_num,
                    'auth_type': self._detect_dart_auth_type(code),
                }
                api_calls.append(api_call)

        return api_calls

    def _extract_typescript_api_calls(
        self, code: str, file_path: str, namespace: str
    ) -> List[Dict[str, Any]]:
        """Extract API calls from TypeScript/JavaScript code."""
        api_calls = []

        # Pattern 1: fetch() calls
        fetch_pattern = r'fetch\s*\(\s*[`"\']([^`"\']+)[`"\']'
        for match in re.finditer(fetch_pattern, code):
            url = match.group(1)
            target_service, clean_url = self._resolve_service_from_url(url, None)

            if target_service:
                line_num = code[:match.start()].count('\n') + 1
                function_name = self._find_containing_function(code, match.start())

                # Try to detect HTTP method
                method_match = re.search(r'method:\s*["\'](\w+)["\']', code[match.end():match.end() + 200])
                http_method = method_match.group(1).upper() if method_match else 'GET'

                api_call = {
                    'source_namespace': namespace,
                    'source_file': file_path,
                    'source_function': function_name or 'unknown',
                    'target_service': target_service,
                    'target_url': clean_url,
                    'http_method': http_method,
                    'line_number': line_num,
                }
                api_calls.append(api_call)

        # Pattern 2: axios calls
        axios_pattern = r'axios\.(get|post|put|delete|patch)\s*\(\s*[`"\']([^`"\']+)[`"\']'
        for match in re.finditer(axios_pattern, code):
            http_method = match.group(1).upper()
            url = match.group(2)
            target_service, clean_url = self._resolve_service_from_url(url, None)

            if target_service:
                line_num = code[:match.start()].count('\n') + 1
                function_name = self._find_containing_function(code, match.start())

                api_call = {
                    'source_namespace': namespace,
                    'source_file': file_path,
                    'source_function': function_name or 'unknown',
                    'target_service': target_service,
                    'target_url': clean_url,
                    'http_method': http_method,
                    'line_number': line_num,
                }
                api_calls.append(api_call)

        return api_calls

    def _extract_python_api_calls(
        self, code: str, file_path: str, namespace: str
    ) -> List[Dict[str, Any]]:
        """Extract API calls from Python code."""
        api_calls = []

        # Pattern: requests.get/post/etc
        requests_pattern = r'requests\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(requests_pattern, code):
            http_method = match.group(1).upper()
            url = match.group(2)
            target_service, clean_url = self._resolve_service_from_url(url, None)

            if target_service:
                line_num = code[:match.start()].count('\n') + 1
                function_name = self._find_containing_function(code, match.start())

                api_call = {
                    'source_namespace': namespace,
                    'source_file': file_path,
                    'source_function': function_name or 'unknown',
                    'target_service': target_service,
                    'target_url': clean_url,
                    'http_method': http_method,
                    'line_number': line_num,
                }
                api_calls.append(api_call)

        return api_calls

    def _resolve_service_from_url(
        self, url: str, base_url: Optional[str] = None
    ) -> Tuple[Optional[str], str]:
        """
        Resolve service namespace from URL.

        Returns:
            Tuple of (service_namespace, cleaned_url)
        """
        original_url = url

        # Handle template variables like $_baseUrl, ${baseUrl}, etc.
        template_patterns = [
            r'\$\{?_?baseUrl\}?',
            r'\$\{?BASE_URL\}?',
            r'\$\{?base_url\}?',
        ]

        # Check if URL contains template variable
        has_template = any(re.search(pattern, url, re.IGNORECASE) for pattern in template_patterns)

        if has_template:
            # If we have the actual base_url, check if it's an env var or actual URL
            if base_url:
                # Check if base_url is actually an env var name (e.g., "SHOP_DATA_PROVIDER_URL")
                if '_URL' in base_url and base_url.isupper():
                    # It's an env var name - try to map it to a service
                    env_var = base_url.replace('_URL', '').replace('_', '').lower()
                    for service_key, namespace in self.service_url_mappings.items():
                        if service_key.lower() in env_var or env_var in service_key.lower():
                            return namespace, original_url
                    # Couldn't map env var to service
                    logger.debug(f"Cannot map env var {base_url} to known service")
                    return None, original_url
                elif base_url.startswith('http://') or base_url.startswith('https://'):
                    # It's an actual URL - substitute it and continue processing
                    for pattern in template_patterns:
                        url = re.sub(pattern, base_url, url, flags=re.IGNORECASE)
                else:
                    # Unknown format
                    logger.debug(f"Unknown base_url format: {base_url}")
                    return None, original_url
            else:
                # Can't resolve template without base URL
                # Return None to indicate we need more context
                logger.debug(f"Cannot resolve template URL without base_url: {url}")
                return None, original_url

        # Try to extract hostname/service name from full URLs
        try:
            if url.startswith('http://') or url.startswith('https://'):
                parsed = urlparse(url)
                hostname = parsed.hostname or ''

                # Match against configured service mappings
                for service_key, namespace in self.service_url_mappings.items():
                    # Case-insensitive matching for service identifiers in hostname
                    if service_key.lower() in hostname.lower():
                        return namespace, url

            # Check for environment variable references in URL
            # Pattern: ${SERVICE_NAME_URL}, $SERVICE_NAME_URL, etc.
            env_var_pattern = r'\$\{?([A-Z_]+)_URL\}?'
            env_match = re.search(env_var_pattern, url)
            if env_match:
                env_var = env_match.group(1)
                # Try to match env var name to service mappings
                for service_key, namespace in self.service_url_mappings.items():
                    if service_key.upper() in env_var.upper():
                        return namespace, url

        except Exception as e:
            logger.debug(f"Error parsing URL {url}: {e}")

        return None, url

    def _extract_dart_base_url(self, code: str) -> Optional[str]:
        """
        Extract base URL or environment variable name from Dart code.

        Returns either the actual URL or the env var name that can be mapped to a service.
        """
        # Pattern 1: dotenv.env['SERVICE_NAME_URL']
        env_pattern = r'dotenv\.env\[["\']([A-Z_]+_URL)["\']\]'
        env_match = re.search(env_pattern, code)
        if env_match:
            # Return the env var name - caller can map it to service
            return env_match.group(1)

        # Pattern 2: Actual URL string in _baseUrl getter
        # String get _baseUrl { return 'https://...' }
        url_pattern = r'_baseUrl.*?["\']([^"\']+)["\']'
        url_match = re.search(url_pattern, code)
        if url_match:
            return url_match.group(1)

        return None

    def _detect_dart_auth_type(self, code: str) -> Optional[str]:
        """Detect authentication type from Dart code."""
        if 'Authorization' in code and 'Bearer' in code:
            return 'jwt'
        elif 'x-api-key' in code:
            return 'api_key'
        return None

    def _map_env_var_to_service(self, env_var: str) -> Optional[str]:
        """Map environment variable to service namespace."""
        env_upper = env_var.upper()
        for service_key, namespace in self.service_url_mappings.items():
            if service_key.upper() in env_upper:
                return namespace
        return None

    def _find_containing_function(self, code: str, position: int) -> Optional[str]:
        """Find the function/method containing the given position."""
        # Look backwards for function declaration
        preceding_code = code[:position]

        # Dart/Flutter pattern
        dart_match = re.findall(r'\b(\w+)\s*\([^)]*\)\s*(?:async\s*)?{', preceding_code)
        if dart_match:
            return dart_match[-1]

        # TypeScript/JavaScript pattern
        js_match = re.findall(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=.*?function|(\w+)\s*:\s*(?:async\s*)?\([^)]*\)\s*=>)', preceding_code)
        if js_match:
            # Find the last non-None group
            for match_groups in reversed(js_match):
                for group in match_groups:
                    if group:
                        return group

        # Python pattern
        py_match = re.findall(r'def\s+(\w+)\s*\(', preceding_code)
        if py_match:
            return py_match[-1]

        return None

    def create_api_call_id(self, api_call: Dict[str, Any]) -> str:
        """Generate unique ID for an API call relationship."""
        unique_str = f"{api_call['source_file']}:{api_call['source_function']}:{api_call['target_service']}:{api_call['line_number']}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]


def get_service_dependency_extractor(
    service_mappings: Optional[Dict[str, str]] = None,
    config_file: Optional[str] = None
) -> ServiceDependencyExtractor:
    """
    Get service dependency extractor instance.

    Args:
        service_mappings: Optional dictionary mapping service identifiers to namespaces
        config_file: Optional path to JSON config file

    Returns:
        ServiceDependencyExtractor instance
    """
    return ServiceDependencyExtractor(
        service_mappings=service_mappings,
        config_file=config_file
    )
