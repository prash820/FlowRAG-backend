"""
Feature flags for FlowRAG experimental features.

This module provides a centralized way to enable/disable experimental features
without affecting existing functionality. All new features should be disabled
by default and only enabled when explicitly configured.

Usage:
    from config.feature_flags import get_feature_flags

    flags = get_feature_flags()
    if flags.enable_data_flow_analysis:
        # Use new data flow analysis
        pass
    else:
        # Use existing behavior
        pass
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class FeatureFlags(BaseModel):
    """Feature flags for experimental features."""

    # =========================================================================
    # Graph Model Enhancement (Phase 1)
    # =========================================================================
    enable_data_flow_relationships: bool = Field(
        default=True,
        description="Enable DATA_FLOWS_TO relationships in the graph model. "
                    "Tracks variable passing between function calls."
    )

    enable_parallelization_waves: bool = Field(
        default=True,
        description="Enable automatic parallelization wave detection. "
                    "Groups independent operations that can run concurrently."
    )

    # =========================================================================
    # AST-Based Parsing (Phase 2)
    # =========================================================================
    enable_typescript_ast: bool = Field(
        default=False,
        description="Use tree-sitter for TypeScript parsing instead of regex. "
                    "Provides more accurate code analysis."
    )

    enable_javascript_ast: bool = Field(
        default=False,
        description="Use tree-sitter for JavaScript parsing instead of regex."
    )

    # =========================================================================
    # Data Flow Analysis (Phase 3)
    # =========================================================================
    enable_data_flow_analysis: bool = Field(
        default=False,
        description="Enable full data flow analysis during ingestion. "
                    "Requires enable_typescript_ast or similar AST parser."
    )

    enable_variable_tracking: bool = Field(
        default=False,
        description="Track variable assignments and usage across scopes. "
                    "Part of data flow analysis."
    )

    # =========================================================================
    # Query Enhancement
    # =========================================================================
    enable_flow_aware_queries: bool = Field(
        default=False,
        description="Use data flow information in query responses. "
                    "Requires enable_data_flow_relationships."
    )

    enable_auto_parallelization_hints: bool = Field(
        default=False,
        description="Automatically suggest parallelization opportunities in responses. "
                    "Requires enable_parallelization_waves."
    )

    # =========================================================================
    # Logging and Debugging
    # =========================================================================
    log_feature_usage: bool = Field(
        default=True,
        description="Log when experimental features are used."
    )

    def is_data_flow_ready(self) -> bool:
        """Check if data flow analysis is fully enabled and ready."""
        return (
            self.enable_data_flow_analysis and
            self.enable_data_flow_relationships and
            (self.enable_typescript_ast or self.enable_javascript_ast)
        )

    def is_parallelization_ready(self) -> bool:
        """Check if parallelization detection is fully enabled."""
        return (
            self.enable_parallelization_waves and
            self.enable_data_flow_relationships
        )


# Singleton instance
_feature_flags: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """
    Get feature flags instance (singleton pattern).

    Loads flags from environment variables with FLOWRAG_FEATURE_ prefix.
    Example: FLOWRAG_FEATURE_ENABLE_DATA_FLOW_RELATIONSHIPS=true
    """
    global _feature_flags

    if _feature_flags is None:
        # Load from environment variables
        flags_dict = {}

        for field_name in FeatureFlags.model_fields:
            env_key = f"FLOWRAG_FEATURE_{field_name.upper()}"
            env_value = os.environ.get(env_key)

            if env_value is not None:
                # Convert string to boolean
                if env_value.lower() in ('true', '1', 'yes', 'on'):
                    flags_dict[field_name] = True
                elif env_value.lower() in ('false', '0', 'no', 'off'):
                    flags_dict[field_name] = False
                else:
                    logger.warning(f"Invalid value for {env_key}: {env_value}")

        _feature_flags = FeatureFlags(**flags_dict)

        # Log enabled features
        enabled = [k for k, v in _feature_flags.model_dump().items()
                   if v is True and k != 'log_feature_usage']
        if enabled:
            logger.info(f"Experimental features enabled: {', '.join(enabled)}")
        else:
            logger.debug("No experimental features enabled")

    return _feature_flags


def reset_feature_flags() -> None:
    """Reset feature flags (useful for testing)."""
    global _feature_flags
    _feature_flags = None


def enable_feature(feature_name: str) -> None:
    """
    Programmatically enable a feature (useful for testing).

    Args:
        feature_name: Name of the feature to enable
    """
    flags = get_feature_flags()
    if hasattr(flags, feature_name):
        setattr(flags, feature_name, True)
        if flags.log_feature_usage:
            logger.info(f"Feature enabled: {feature_name}")
    else:
        raise ValueError(f"Unknown feature: {feature_name}")


def disable_feature(feature_name: str) -> None:
    """
    Programmatically disable a feature.

    Args:
        feature_name: Name of the feature to disable
    """
    flags = get_feature_flags()
    if hasattr(flags, feature_name):
        setattr(flags, feature_name, False)
        if flags.log_feature_usage:
            logger.info(f"Feature disabled: {feature_name}")
    else:
        raise ValueError(f"Unknown feature: {feature_name}")
