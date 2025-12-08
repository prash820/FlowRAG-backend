"""
Namespace Groups API endpoints.

Provides functionality for:
- Creating and managing namespace groups
- Querying across multiple namespaces in a group
- Auto-grouping based on namespace naming conventions
"""

import logging
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from api.schemas.namespace_groups import (
    NamespaceGroupCreate,
    NamespaceGroupUpdate,
    NamespaceGroupResponse,
    NamespaceGroupListResponse,
    NamespaceInGroup,
    AddNamespacesToGroupRequest,
    RemoveNamespacesFromGroupRequest,
    GroupQueryRequest,
    GroupQueryResponse,
)
from databases.neo4j.client import Neo4jClient
from databases.qdrant.client import QdrantClient
from config import get_settings
from agents.llm import get_llm_client, LLMRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/namespace-groups", tags=["namespace_groups"])


def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client instance."""
    settings = get_settings()
    return Neo4jClient(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance."""
    settings = get_settings()
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )


@router.post("", response_model=NamespaceGroupResponse)
async def create_namespace_group(request: NamespaceGroupCreate):
    """
    Create a new namespace group.

    Groups allow you to query multiple related namespaces together.
    """
    neo4j = get_neo4j_client()

    try:
        # Check if group already exists
        check_query = """
        MATCH (ng:NamespaceGroup {name: $name})
        RETURN ng
        """
        existing = neo4j.execute_query(check_query, {"name": request.name})
        if existing:
            raise HTTPException(status_code=409, detail=f"Group '{request.name}' already exists")

        # Create the group
        create_query = """
        CREATE (ng:NamespaceGroup {
            name: $name,
            description: $description,
            created_at: datetime(),
            metadata: $metadata
        })
        RETURN ng.name as name, ng.description as description,
               toString(ng.created_at) as created_at
        """
        result = neo4j.execute_query(create_query, {
            "name": request.name,
            "description": request.description,
            "metadata": request.metadata or {},
        })

        # Add initial namespaces if provided
        if request.namespaces:
            add_ns_query = """
            MATCH (ng:NamespaceGroup {name: $group_name})
            UNWIND $namespaces as ns_name
            MERGE (ns:Namespace {name: ns_name})
            MERGE (ng)-[:CONTAINS_NAMESPACE]->(ns)
            """
            neo4j.execute_query(add_ns_query, {
                "group_name": request.name,
                "namespaces": request.namespaces,
            })

        # Return the created group with namespace details
        return await get_namespace_group(request.name)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create namespace group: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j.close()


@router.get("", response_model=NamespaceGroupListResponse)
async def list_namespace_groups(include_auto: bool = True):
    """
    List all namespace groups.

    Args:
        include_auto: If True, also include auto-detected groups based on namespace prefixes
    """
    neo4j = get_neo4j_client()

    try:
        # Get explicit groups
        groups_query = """
        MATCH (ng:NamespaceGroup)
        OPTIONAL MATCH (ng)-[:CONTAINS_NAMESPACE]->(ns:Namespace)
        WITH ng, collect(DISTINCT ns.name) as namespaces
        RETURN ng.name as name,
               ng.description as description,
               toString(ng.created_at) as created_at,
               ng.metadata as metadata,
               namespaces,
               size(namespaces) as namespace_count
        ORDER BY ng.name
        """
        explicit_groups = neo4j.execute_query(groups_query, {})

        groups = []

        # Process explicit groups
        for g in explicit_groups:
            group_response = await _build_group_response(neo4j, g["name"], g)
            groups.append(group_response)

        # Auto-detect groups from namespace prefixes if requested
        if include_auto:
            auto_groups = await _get_auto_detected_groups(neo4j)
            # Only add auto groups that don't already exist as explicit groups
            explicit_names = {g.name for g in groups}
            for auto_group in auto_groups:
                if auto_group.name not in explicit_names:
                    groups.append(auto_group)

        return NamespaceGroupListResponse(
            groups=sorted(groups, key=lambda g: g.name),
            total=len(groups),
        )

    except Exception as e:
        logger.error(f"Failed to list namespace groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j.close()


async def _get_auto_detected_groups(neo4j: Neo4jClient) -> List[NamespaceGroupResponse]:
    """Auto-detect groups from namespace naming conventions (prefix before first hyphen)."""

    # Get all namespaces
    query = """
    MATCH (n)
    WHERE n.namespace IS NOT NULL
    WITH DISTINCT n.namespace as namespace
    RETURN namespace
    ORDER BY namespace
    """
    result = neo4j.execute_query(query, {})

    # Group by prefix
    prefix_groups: dict = {}
    for r in result:
        ns = r["namespace"]
        parts = ns.split("-")
        prefix = parts[0] if len(parts) > 1 else None

        if prefix:
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(ns)

    # Only return groups with more than one namespace
    auto_groups = []
    for prefix, namespaces in prefix_groups.items():
        if len(namespaces) > 1:
            # Get stats for each namespace
            ns_list = []
            total_nodes = 0
            total_rels = 0

            for ns in namespaces:
                stats_query = """
                MATCH (n {namespace: $namespace})
                WITH count(n) as node_count
                OPTIONAL MATCH (n1 {namespace: $namespace})-[r]->(n2 {namespace: $namespace})
                RETURN node_count, count(r) as rel_count
                """
                stats = neo4j.execute_query(stats_query, {"namespace": ns})
                node_count = stats[0]["node_count"] if stats else 0
                rel_count = stats[0]["rel_count"] if stats else 0

                ns_list.append(NamespaceInGroup(
                    name=ns,
                    source_type="code",
                    stats={
                        "total_nodes": node_count,
                        "total_relationships": rel_count,
                        "total_files": 0,
                    }
                ))
                total_nodes += node_count
                total_rels += rel_count

            auto_groups.append(NamespaceGroupResponse(
                name=f"{prefix} (auto)",
                description=f"Auto-detected group from '{prefix}-*' namespaces",
                namespaces=ns_list,
                namespace_count=len(namespaces),
                total_nodes=total_nodes,
                total_relationships=total_rels,
                metadata={"auto_detected": True, "prefix": prefix},
            ))

    return auto_groups


async def _build_group_response(
    neo4j: Neo4jClient,
    group_name: str,
    group_data: dict = None
) -> NamespaceGroupResponse:
    """Build a complete group response with namespace details."""

    if not group_data:
        # Fetch group data
        query = """
        MATCH (ng:NamespaceGroup {name: $name})
        OPTIONAL MATCH (ng)-[:CONTAINS_NAMESPACE]->(ns:Namespace)
        WITH ng, collect(DISTINCT ns.name) as namespaces
        RETURN ng.name as name,
               ng.description as description,
               toString(ng.created_at) as created_at,
               ng.metadata as metadata,
               namespaces
        """
        result = neo4j.execute_query(query, {"name": group_name})
        if not result:
            raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")
        group_data = result[0]

    # Get detailed stats for each namespace
    namespaces = group_data.get("namespaces", [])
    ns_list = []
    total_nodes = 0
    total_rels = 0

    for ns in namespaces:
        if ns:  # Skip None values
            stats_query = """
            MATCH (n {namespace: $namespace})
            WITH count(n) as node_count
            OPTIONAL MATCH (n1 {namespace: $namespace})-[r]->(n2 {namespace: $namespace})
            RETURN node_count, count(r) as rel_count
            """
            stats = neo4j.execute_query(stats_query, {"namespace": ns})
            node_count = stats[0]["node_count"] if stats else 0
            rel_count = stats[0]["rel_count"] if stats else 0

            ns_list.append(NamespaceInGroup(
                name=ns,
                source_type="code",
                stats={
                    "total_nodes": node_count,
                    "total_relationships": rel_count,
                    "total_files": 0,
                }
            ))
            total_nodes += node_count
            total_rels += rel_count

    return NamespaceGroupResponse(
        name=group_data["name"],
        description=group_data.get("description"),
        namespaces=ns_list,
        namespace_count=len(ns_list),
        total_nodes=total_nodes,
        total_relationships=total_rels,
        created_at=group_data.get("created_at"),
        metadata=group_data.get("metadata"),
    )


@router.get("/{group_name}", response_model=NamespaceGroupResponse)
async def get_namespace_group(group_name: str):
    """Get details of a specific namespace group."""
    neo4j = get_neo4j_client()

    try:
        # Check if it's an auto-detected group
        if group_name.endswith(" (auto)"):
            prefix = group_name.replace(" (auto)", "")
            auto_groups = await _get_auto_detected_groups(neo4j)
            for g in auto_groups:
                if g.name == group_name:
                    return g
            raise HTTPException(status_code=404, detail=f"Auto group '{group_name}' not found")

        return await _build_group_response(neo4j, group_name)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get namespace group: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j.close()


@router.put("/{group_name}", response_model=NamespaceGroupResponse)
async def update_namespace_group(group_name: str, request: NamespaceGroupUpdate):
    """Update a namespace group's metadata."""
    neo4j = get_neo4j_client()

    try:
        update_query = """
        MATCH (ng:NamespaceGroup {name: $name})
        SET ng.description = COALESCE($description, ng.description),
            ng.metadata = COALESCE($metadata, ng.metadata)
        RETURN ng.name as name
        """
        result = neo4j.execute_query(update_query, {
            "name": group_name,
            "description": request.description,
            "metadata": request.metadata,
        })

        if not result:
            raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")

        return await get_namespace_group(group_name)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update namespace group: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j.close()


@router.delete("/{group_name}")
async def delete_namespace_group(group_name: str):
    """Delete a namespace group (does not delete the namespaces themselves)."""
    neo4j = get_neo4j_client()

    try:
        delete_query = """
        MATCH (ng:NamespaceGroup {name: $name})
        DETACH DELETE ng
        RETURN count(*) as deleted
        """
        result = neo4j.execute_query(delete_query, {"name": group_name})

        if not result or result[0]["deleted"] == 0:
            raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")

        return {"message": f"Group '{group_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete namespace group: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j.close()


@router.post("/{group_name}/namespaces", response_model=NamespaceGroupResponse)
async def add_namespaces_to_group(group_name: str, request: AddNamespacesToGroupRequest):
    """Add namespaces to an existing group."""
    neo4j = get_neo4j_client()

    try:
        # Check group exists
        check_query = """
        MATCH (ng:NamespaceGroup {name: $name})
        RETURN ng
        """
        if not neo4j.execute_query(check_query, {"name": group_name}):
            raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")

        # Add namespaces
        add_query = """
        MATCH (ng:NamespaceGroup {name: $group_name})
        UNWIND $namespaces as ns_name
        MERGE (ns:Namespace {name: ns_name})
        MERGE (ng)-[:CONTAINS_NAMESPACE]->(ns)
        """
        neo4j.execute_query(add_query, {
            "group_name": group_name,
            "namespaces": request.namespaces,
        })

        return await get_namespace_group(group_name)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add namespaces to group: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j.close()


@router.delete("/{group_name}/namespaces")
async def remove_namespaces_from_group(
    group_name: str,
    request: RemoveNamespacesFromGroupRequest
):
    """Remove namespaces from a group (does not delete the namespaces themselves)."""
    neo4j = get_neo4j_client()

    try:
        remove_query = """
        MATCH (ng:NamespaceGroup {name: $group_name})-[r:CONTAINS_NAMESPACE]->(ns:Namespace)
        WHERE ns.name IN $namespaces
        DELETE r
        RETURN count(r) as removed
        """
        result = neo4j.execute_query(remove_query, {
            "group_name": group_name,
            "namespaces": request.namespaces,
        })

        removed = result[0]["removed"] if result else 0
        return {
            "message": f"Removed {removed} namespace(s) from group '{group_name}'",
            "removed_count": removed,
        }

    except Exception as e:
        logger.error(f"Failed to remove namespaces from group: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j.close()


@router.post("/{group_name}/query", response_model=GroupQueryResponse)
async def query_namespace_group(group_name: str, request: GroupQueryRequest):
    """
    Query across all namespaces in a group.

    This performs a unified search across all namespaces in the group,
    combining results and providing cross-service relationship analysis.
    """
    start_time = time.time()
    neo4j = get_neo4j_client()

    try:
        # Get namespaces in the group
        if group_name.endswith(" (auto)"):
            prefix = group_name.replace(" (auto)", "")
            # Get namespaces with this prefix
            ns_query = """
            MATCH (n)
            WHERE n.namespace IS NOT NULL AND n.namespace STARTS WITH $prefix
            RETURN DISTINCT n.namespace as namespace
            """
            result = neo4j.execute_query(ns_query, {"prefix": prefix + "-"})
            namespaces = [r["namespace"] for r in result]
        else:
            ns_query = """
            MATCH (ng:NamespaceGroup {name: $group_name})-[:CONTAINS_NAMESPACE]->(ns:Namespace)
            RETURN ns.name as namespace
            """
            result = neo4j.execute_query(ns_query, {"group_name": group_name})
            namespaces = [r["namespace"] for r in result]

        if not namespaces:
            raise HTTPException(
                status_code=404,
                detail=f"No namespaces found in group '{group_name}'"
            )

        retrieval_start = time.time()

        # Search across all namespaces
        all_context_items = []

        for ns in namespaces:
            # Vector search in this namespace
            # Note: nodes have 'code' property, not 'content'
            vector_query = """
            MATCH (n {namespace: $namespace})
            WHERE n.code IS NOT NULL
            RETURN n.name as name,
                   n.code as code,
                   n.file_path as file_path,
                   n.namespace as namespace,
                   labels(n)[0] as type
            LIMIT $limit
            """
            results = neo4j.execute_query(vector_query, {
                "namespace": ns,
                "limit": request.max_results,
            })

            for r in results:
                all_context_items.append({
                    "name": r["name"],
                    "content": r.get("code", "")[:500],  # Truncate code as content
                    "file_path": r.get("file_path", ""),
                    "namespace": r["namespace"],
                    "type": r["type"],
                    "relevance_score": 0.8,  # Placeholder
                })

        retrieval_time = time.time() - retrieval_start

        # Build context string for LLM
        context_parts = []
        for item in all_context_items[:20]:  # Limit context to top 20 items
            context_parts.append(
                f"[{item['namespace']}] {item['type']}: {item['name']}\n"
                f"File: {item['file_path']}\n"
                f"```\n{item['content']}\n```\n"
            )
        context_str = "\n---\n".join(context_parts)

        # Call LLM to generate answer
        llm_client = get_llm_client()

        system_prompt = """You are a helpful code assistant analyzing a multi-service codebase.
You have access to code from multiple services/namespaces in a software system.
Answer questions based on the provided code context.
Be specific and reference the actual code when possible.
If the answer spans multiple services, explain how they interact."""

        user_prompt = f"""Question: {request.query}

The following code context comes from these services: {', '.join(namespaces)}

Code Context:
{context_str}

Please answer the question based on the code context above."""

        try:
            llm_request = LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=request.temperature,
                max_tokens=2000,
                stream=False,
            )
            llm_response = await llm_client.generate_async(llm_request)
            answer = llm_response.content
        except Exception as e:
            logger.warning(f"LLM call failed, falling back to summary: {e}")
            # Fallback to basic summary if LLM fails
            ns_counts = {}
            for item in all_context_items:
                ns = item["namespace"]
                ns_counts[ns] = ns_counts.get(ns, 0) + 1
            answer = f"Found {len(all_context_items)} relevant items across {len(namespaces)} namespaces:\n\n"
            for ns, count in ns_counts.items():
                answer += f"- **{ns}**: {count} items\n"

        # Include cross-service relationships if requested
        flow_analysis = None
        if request.include_cross_service:
            cross_query = """
            MATCH (n1)-[r:CALLS_API]->(n2)
            WHERE n1.namespace IN $namespaces AND n2.namespace IN $namespaces
            RETURN n1.namespace as source_ns, n2.namespace as target_ns,
                   r.target_url as api_endpoint, count(*) as call_count
            ORDER BY call_count DESC
            LIMIT 10
            """
            cross_results = neo4j.execute_query(cross_query, {"namespaces": namespaces})

            if cross_results:
                flow_analysis = {
                    "cross_service_calls": [
                        {
                            "from": r["source_ns"],
                            "to": r["target_ns"],
                            "endpoint": r["api_endpoint"],
                            "count": r["call_count"],
                        }
                        for r in cross_results
                    ]
                }

        total_time = time.time() - start_time

        return GroupQueryResponse(
            answer=answer,
            query=request.query,
            group_name=group_name,
            namespaces_searched=namespaces,
            context_items=all_context_items[:50],  # Limit response size
            sources_count=len(all_context_items),
            flow_analysis=flow_analysis,
            retrieval_time=retrieval_time,
            total_time=total_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query namespace group: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        neo4j.close()
