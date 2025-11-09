"""
Cypher Query Templates for FlowRAG.

Pre-defined queries for common graph operations.
Database Agent is responsible for this module.
"""

from typing import Dict, Any


# ============================================================================
# Code Graph Queries
# ============================================================================

FIND_FUNCTION_CALLS = """
MATCH (caller:Function)-[r:CALLS]->(callee:Function)
WHERE caller.namespace = $namespace
RETURN caller.name as caller,
       callee.name as callee,
       r.call_count as count,
       r.is_recursive as recursive
"""

FIND_CLASS_HIERARCHY = """
MATCH path = (child:Class)-[:INHERITS_FROM*]->(parent:Class)
WHERE child.namespace = $namespace
RETURN [node IN nodes(path) | node.name] as hierarchy
"""

FIND_MODULE_DEPENDENCIES = """
MATCH (m:Module)-[r:IMPORTS]->(dep:Module)
WHERE m.namespace = $namespace
RETURN m.file_path as module,
       collect(dep.file_path) as dependencies,
       collect(r.import_type) as import_types
"""

GET_FUNCTION_CONTEXT = """
MATCH (f:Function {id: $function_id})
OPTIONAL MATCH (f)-[:CALLS]->(called:Function)
OPTIONAL MATCH (caller:Function)-[:CALLS]->(f)
OPTIONAL MATCH (c:Class)-[:CONTAINS]->(f)
RETURN f as function,
       collect(DISTINCT called.name) as calls,
       collect(DISTINCT caller.name) as called_by,
       c.name as parent_class
"""

# ============================================================================
# Flow Detection Queries
# ============================================================================

FIND_PARALLEL_STEPS = """
MATCH (flow:ExecutionFlow {id: $flow_id})-[:CONTAINS]->(step:Step)
MATCH (step)-[:PARALLEL_WITH]->(parallel:Step)
WHERE step.namespace = $namespace
RETURN step.step_number as step,
       step.description as description,
       collect(parallel.step_number) as parallel_steps
ORDER BY step.step_number
"""

FIND_CRITICAL_PATH = """
MATCH (flow:ExecutionFlow {id: $flow_id})-[:CONTAINS]->(step:Step)
WHERE step.namespace = $namespace
  AND NOT EXISTS((step)-[:PARALLEL_WITH]->())
WITH step
ORDER BY step.step_number
RETURN collect(step.step_number) as critical_path,
       collect(step.description) as descriptions
"""

FIND_STEP_DEPENDENCIES = """
MATCH (step:Step {id: $step_id})
OPTIONAL MATCH (step)-[:DEPENDS_ON]->(dep:Step)
OPTIONAL MATCH (blocker:Step)-[:DEPENDS_ON]->(step)
RETURN step.step_number as step,
       collect(DISTINCT dep.step_number) as dependencies,
       collect(DISTINCT blocker.step_number) as blocks
"""

GET_FLOW_OPTIMIZATION = """
MATCH (flow:ExecutionFlow {id: $flow_id})
RETURN flow.total_steps as total_steps,
       flow.sequential_time as sequential_time,
       flow.parallel_time as parallel_time,
       flow.optimization_pct as optimization_pct
"""

# ============================================================================
# Document Queries
# ============================================================================

FIND_RELATED_DOCS = """
MATCH (doc:Document)-[:DOCUMENTS]->(entity)
WHERE doc.namespace = $namespace
  AND entity.id IN $entity_ids
RETURN doc.file_path as document,
       doc.title as title,
       collect(entity.name) as documented_entities
"""

GET_DOC_SECTIONS = """
MATCH (doc:Document {id: $doc_id})-[:HAS_SECTION]->(section:Section)
RETURN section.name as section,
       section.content as content
ORDER BY section.order
"""

# ============================================================================
# Search and Discovery Queries
# ============================================================================

SEARCH_BY_NAME = """
MATCH (n)
WHERE n.namespace = $namespace
  AND toLower(n.name) CONTAINS toLower($search_term)
RETURN labels(n)[0] as type,
       n.name as name,
       n.id as id,
       n.file_path as file_path
LIMIT $limit
"""

FIND_BY_FILE_PATH = """
MATCH (n)
WHERE n.namespace = $namespace
  AND n.file_path = $file_path
RETURN labels(n)[0] as type,
       properties(n) as properties
"""

GET_NAMESPACE_STATS = """
MATCH (n)
WHERE n.namespace = $namespace
WITH labels(n)[0] as label, count(*) as count
RETURN label, count
ORDER BY count DESC
"""

# ============================================================================
# Graph Traversal Queries
# ============================================================================

FIND_CALL_CHAIN = """
MATCH path = (start:Function {id: $start_id})-[:CALLS*1..$max_depth]->(end:Function)
WHERE start.namespace = $namespace
RETURN [node IN nodes(path) | node.name] as call_chain,
       length(path) as depth
ORDER BY depth
LIMIT $limit
"""

FIND_IMPACT_ANALYSIS = """
// Find all nodes that depend on the target node
MATCH (target {id: $target_id})
OPTIONAL MATCH path = (dependent)-[*1..5]->(target)
WHERE dependent.namespace = $namespace
RETURN DISTINCT labels(dependent)[0] as type,
       dependent.name as name,
       dependent.id as id,
       length(path) as distance
ORDER BY distance
"""

GET_SUBGRAPH = """
MATCH (center {id: $center_id})
OPTIONAL MATCH path = (center)-[*1..$depth]-(neighbor)
WHERE neighbor.namespace = $namespace
WITH center, collect(DISTINCT neighbor) as neighbors, collect(DISTINCT path) as paths
RETURN center,
       neighbors,
       [rel IN relationships(paths[0]) | type(rel)] as relationship_types
"""

# ============================================================================
# Aggregation Queries
# ============================================================================

GET_MOST_CALLED_FUNCTIONS = """
MATCH (f:Function)<-[r:CALLS]-()
WHERE f.namespace = $namespace
WITH f, count(r) as call_count
ORDER BY call_count DESC
LIMIT $limit
RETURN f.name as function,
       f.file_path as file,
       call_count
"""

GET_MOST_COMPLEX_FUNCTIONS = """
MATCH (f:Function)
WHERE f.namespace = $namespace
  AND f.complexity IS NOT NULL
WITH f
ORDER BY f.complexity DESC
LIMIT $limit
RETURN f.name as function,
       f.file_path as file,
       f.complexity as complexity,
       f.line_start as line
"""

GET_MODULE_COUPLING = """
MATCH (m:Module)-[r:IMPORTS]->(dep:Module)
WHERE m.namespace = $namespace
WITH m, count(dep) as dependencies
ORDER BY dependencies DESC
LIMIT $limit
RETURN m.file_path as module,
       dependencies
"""

# ============================================================================
# Mutation Queries
# ============================================================================

MERGE_FUNCTION = """
MERGE (f:Function {id: $id})
ON CREATE SET f = $properties
ON MATCH SET f += $properties
RETURN f.id as id
"""

MERGE_RELATIONSHIP = """
MATCH (a {id: $from_id}), (b {id: $to_id})
MERGE (a)-[r:$rel_type]->(b)
ON CREATE SET r = $properties
ON MATCH SET r += $properties
RETURN id(r) as rel_id
"""

DELETE_BY_NAMESPACE = """
MATCH (n {namespace: $namespace})
DETACH DELETE n
"""


# ============================================================================
# Query Functions
# ============================================================================

def get_query(query_name: str) -> str:
    """
    Get a query template by name.

    Args:
        query_name: Name of the query constant

    Returns:
        Cypher query string

    Raises:
        KeyError: If query name not found
    """
    return globals()[query_name]


def format_query(query: str, **kwargs: Any) -> str:
    """
    Format a query template with parameters.

    Args:
        query: Query template
        **kwargs: Template parameters

    Returns:
        Formatted query string
    """
    return query.format(**kwargs)
