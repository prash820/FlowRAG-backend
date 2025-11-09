"""
FlowRAG UI - Web Interface for GraphRAG
Simple FastAPI app with built-in HTML UI for testing semantic and flow searches
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from databases.neo4j.client import Neo4jClient
from config import get_settings

app = FastAPI(title="FlowRAG UI", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
settings = get_settings()
neo4j_client = Neo4jClient()
qdrant_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, check_compatibility=False)
openai_client = OpenAI(api_key=settings.openai_api_key)


# Request/Response models
class SemanticSearchRequest(BaseModel):
    query: str
    collection: str = "pipeline_25step_code"
    namespace: Optional[str] = None
    limit: int = 5


class FlowSearchRequest(BaseModel):
    query: str
    namespace: str
    entry_class: str = "PipelineOrchestrator"
    entry_method: str = "execute_pipeline"


class CodeResult(BaseModel):
    name: str
    type: str
    file_path: str
    similarity: float
    docstring: str
    code_preview: str


class SemanticSearchResponse(BaseModel):
    query: str
    results: List[CodeResult]
    llm_answer: str
    total_results: int


class FlowSearchResponse(BaseModel):
    query: str
    entry_point: Optional[Dict]
    steps: List[Dict]
    dependencies: List[Dict]
    llm_explanation: str


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the UI."""
    with open(Path(__file__).parent / "index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "neo4j": neo4j_client is not None,
        "qdrant": qdrant_client is not None,
        "openai": openai_client is not None
    }


@app.post("/api/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(request: SemanticSearchRequest):
    """Perform semantic search on code."""
    try:
        # Get latest namespace if not provided
        if not request.namespace:
            collections = qdrant_client.get_collections()
            if request.collection not in [c.name for c in collections.collections]:
                raise HTTPException(status_code=404, detail=f"Collection '{request.collection}' not found")

            # Try to get any namespace from the collection
            scroll_result = qdrant_client.scroll(
                collection_name=request.collection,
                limit=1
            )
            if scroll_result[0]:
                request.namespace = scroll_result[0][0].payload.get('namespace')
            else:
                raise HTTPException(status_code=404, detail="No data found in collection")

        # Create query embedding
        embedding_response = openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=request.query
        )
        query_embedding = embedding_response.data[0].embedding

        # Search Qdrant
        search_results = qdrant_client.search(
            collection_name=request.collection,
            query_vector=query_embedding,
            limit=request.limit,
            query_filter=Filter(
                must=[FieldCondition(key="namespace", match=MatchValue(value=request.namespace))]
            ) if request.namespace else None
        )

        # Format results
        results = []
        context_parts = []

        for result in search_results:
            payload = result.payload
            code_result = CodeResult(
                name=payload['name'],
                type=payload['type'],
                file_path=payload['file_path'],
                similarity=result.score,
                docstring=payload.get('docstring', ''),
                code_preview=payload.get('code', '')[:300]
            )
            results.append(code_result)

            # Build context for LLM
            context_parts.append(
                f"{payload['name']} in {payload['file_path']}:\n{payload.get('docstring', '')}\n{payload.get('code', '')[:300]}"
            )

        # Generate LLM answer
        context = "\n\n".join(context_parts)
        llm_response = openai_client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a code analysis assistant. Answer questions based on the provided code context."},
                {"role": "user", "content": f"Based on this code:\n\n{context}\n\nQuestion: {request.query}\n\nProvide a clear, concise answer."}
            ],
            temperature=0.3,
            max_tokens=300
        )

        llm_answer = llm_response.choices[0].message.content

        return SemanticSearchResponse(
            query=request.query,
            results=results,
            llm_answer=llm_answer,
            total_results=len(results)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search/flow", response_model=FlowSearchResponse)
async def flow_search(request: FlowSearchRequest):
    """Perform flow-based graph traversal."""
    try:
        # Find entry point
        entry_query = f"""
        MATCH (c:Class {{namespace: $namespace, name: $class_name}})-[:CONTAINS]->(m:Method {{name: $method_name}})
        RETURN m.name as method, m.code as code, m.docstring as doc
        """

        entry_points = neo4j_client.execute_query(
            entry_query,
            {
                "namespace": request.namespace,
                "class_name": request.entry_class,
                "method_name": request.entry_method
            }
        )

        entry_point = entry_points[0] if entry_points else None

        # Find all steps
        steps_query = f"""
        MATCH (c:Class {{namespace: $namespace, name: $class_name}})-[:CONTAINS]->(m:Method)
        WHERE m.name STARTS WITH 'step_'
        RETURN m.name as step, m.docstring as description
        ORDER BY m.name
        """

        steps = neo4j_client.execute_query(
            steps_query,
            {"namespace": request.namespace, "class_name": request.entry_class}
        )

        # Find dependencies
        deps_query = f"""
        MATCH (orchestrator:Class {{namespace: $namespace, name: $class_name}})-[:CONTAINS]->(m:Method)
        WHERE m.name STARTS WITH 'step_'
        MATCH (m)-[:CALLS]->(called)
        MATCH (parent:Class)-[:CONTAINS]->(called)
        WHERE parent.name <> $class_name
        RETURN DISTINCT parent.name as class_name, parent.file_path as file, parent.docstring as description
        LIMIT 10
        """

        dependencies = neo4j_client.execute_query(
            deps_query,
            {"namespace": request.namespace, "class_name": request.entry_class}
        )

        # Generate LLM explanation
        steps_text = "\n".join([
            f"- Step {s['step'].split('_')[1]}: {s['description'].split('.')[0] if s.get('description') else 'N/A'}"
            for s in steps[:25]
        ])

        deps_text = "\n".join([
            f"- {d['class_name']}: {d['description'].split('.')[0] if d.get('description') else 'N/A'}"
            for d in dependencies
        ])

        entry_code = entry_point['code'][:500] if entry_point else "Entry point not found"

        prompt = f"""Analyze this pipeline and explain the complete workflow.

Entry Point:
{entry_code}

All Steps:
{steps_text}

Key Dependencies:
{deps_text}

Provide a comprehensive overview organized by phases."""

        llm_response = openai_client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a DevOps expert analyzing CI/CD pipelines."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=600
        )

        llm_explanation = llm_response.choices[0].message.content

        return FlowSearchResponse(
            query=request.query,
            entry_point=entry_point,
            steps=steps,
            dependencies=dependencies,
            llm_explanation=llm_explanation
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting FlowRAG UI...")
    print("📍 Open http://localhost:8000 in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
