"""
FlowRAG Natural Language Query Interface

Ask questions about your codebase in plain English and get AI-powered answers.
Uses OpenAI GPT to translate questions to Cypher and summarize results.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases.neo4j.client import Neo4jClient
import openai
import os
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    print("Please set it with: export OPENAI_API_KEY='your-key-here'")
    print("Or add it to .env file: OPENAI_API_KEY=your-key-here")
    sys.exit(1)

openai.api_key = OPENAI_API_KEY


SCHEMA_CONTEXT = """
# FlowRAG Neo4j Schema

## Node Structure
Nodes represent code units (functions, methods, classes, structs).

Properties:
- namespace: "sock_shop:<service-name>" (e.g., "sock_shop:payment")
- name: Function/class name
- type: "Function" | "Method" | "Class"
- language: "go" | "javascript" | "java" | "python"
- file_path: Absolute path to source file
- line_start, line_end: Line numbers
- code: Full source code
- signature: Function signature
- parameters: List of parameter names
- calls: List of functions called within this function

## Services Available
- sock_shop:front-end (JavaScript)
- sock_shop:payment (Go)
- sock_shop:user (Go)
- sock_shop:catalogue (Go)

## Relationships
- [:CALLS] - Function/method calls another
- [:CONTAINS] - File/class contains method/function

## Common Query Patterns

Find all services:
```cypher
MATCH (n)
WHERE n.namespace STARTS WITH "sock_shop:"
WITH DISTINCT split(n.namespace, ":")[1] as service
RETURN service
```

Find functions in a service:
```cypher
MATCH (n)
WHERE n.namespace = "sock_shop:payment"
AND n.type IN ["Function", "Method"]
RETURN n.name, n.signature, n.line_start
```

Find call relationships:
```cypher
MATCH (a)-[:CALLS]->(b)
WHERE a.namespace = "sock_shop:payment"
RETURN a.name, b.name
```
"""


def generate_cypher_query(question: str, schema_context: str) -> str:
    """Use GPT to generate a Cypher query from a natural language question."""

    system_prompt = f"""You are a Cypher query expert for Neo4j databases.
Given a natural language question about a codebase, generate a Cypher query to answer it.

{schema_context}

Important:
- Return ONLY the Cypher query, no explanations
- Use LIMIT to prevent large result sets
- Format results with meaningful column names
- Handle case-insensitive searches where appropriate
"""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a Cypher query to answer: {question}"}
        ],
        temperature=0.3,
        max_tokens=500
    )

    cypher_query = response.choices[0].message.content.strip()

    # Remove markdown code blocks if present
    if cypher_query.startswith("```"):
        lines = cypher_query.split("\n")
        cypher_query = "\n".join(lines[1:-1])

    return cypher_query


def summarize_results(question: str, cypher_query: str, results: List[Dict]) -> str:
    """Use GPT to summarize query results into a natural language answer."""

    system_prompt = """You are a helpful assistant that explains code analysis results.
Given a question, the Cypher query used, and the results, provide a clear, concise answer.

Format your answer:
1. Direct answer to the question
2. Key findings (bullet points if multiple items)
3. Relevant details (file paths, line numbers if available)

Be concise but informative. If results are empty, say so clearly."""

    # Limit results to prevent token overflow
    results_sample = results[:20] if len(results) > 20 else results
    results_summary = f"{len(results)} results" if len(results) > 20 else f"{len(results)} results"

    user_prompt = f"""Question: {question}

Cypher Query Used:
{cypher_query}

Results ({results_summary}):
{json.dumps(results_sample, indent=2)}

Please provide a natural language answer to the question based on these results."""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )

    return response.choices[0].message.content.strip()


def query_flowrag(question: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Ask a natural language question and get an AI-powered answer.

    Args:
        question: Natural language question about the codebase
        verbose: If True, show Cypher query and raw results

    Returns:
        Dict with answer, cypher_query, raw_results
    """
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print(f"{'='*80}")

    # Step 1: Generate Cypher query
    print("\n🤖 Generating Cypher query...")
    try:
        cypher_query = generate_cypher_query(question, SCHEMA_CONTEXT)
        if verbose:
            print(f"\nCypher Query:\n{cypher_query}\n")
    except Exception as e:
        return {
            "error": f"Failed to generate query: {e}",
            "question": question
        }

    # Step 2: Execute query
    print("🔍 Querying Neo4j...")
    try:
        client = Neo4jClient()
        client.connect()
        results = client.execute_query(cypher_query, {})
        client.close()

        if verbose:
            print(f"\nRaw Results ({len(results)} rows):")
            for row in results[:5]:
                print(f"  {row}")
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more rows")
    except Exception as e:
        return {
            "error": f"Query execution failed: {e}",
            "question": question,
            "cypher_query": cypher_query
        }

    # Step 3: Summarize results
    print("✨ Generating answer...")
    try:
        answer = summarize_results(question, cypher_query, results)
    except Exception as e:
        return {
            "error": f"Failed to summarize results: {e}",
            "question": question,
            "cypher_query": cypher_query,
            "raw_results": results
        }

    return {
        "question": question,
        "answer": answer,
        "cypher_query": cypher_query,
        "raw_results": results,
        "result_count": len(results)
    }


def interactive_mode():
    """Run in interactive mode - ask questions continuously."""
    print("="*80)
    print("FlowRAG Interactive Query Interface")
    print("="*80)
    print("\nAsk questions about your Sock Shop codebase in natural language.")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            question = input("\n💭 Your question: ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break

            if not question:
                continue

            result = query_flowrag(question, verbose=False)

            if "error" in result:
                print(f"\n❌ Error: {result['error']}")
            else:
                print(f"\n📖 Answer:\n{result['answer']}")
                print(f"\n📊 Based on {result['result_count']} results from Neo4j")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")


def batch_mode(questions: List[str]):
    """Run batch questions and save results."""
    results = []

    for i, question in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"Question {i}/{len(questions)}")
        print(f"{'='*80}")

        result = query_flowrag(question, verbose=True)
        results.append(result)

        if "error" not in result:
            print(f"\n📖 Answer:\n{result['answer']}")
        else:
            print(f"\n❌ Error: {result['error']}")

    # Save results
    output_file = "flowrag_query_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n\n✅ Results saved to {output_file}")
    return results


# Example questions
EXAMPLE_QUESTIONS = [
    "What services are in the Sock Shop architecture?",
    "What language is the payment service written in?",
    "How many functions are in the payment service?",
    "What are the main files in the payment service?",
    "Show me functions that handle authorization in the payment service",
    "What functions does the catalogue service have?",
    "Which services use Go?",
    "What is the total number of code units ingested?",
]


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="FlowRAG Natural Language Query Interface")
    parser.add_argument("question", nargs="*", help="Question to ask (if not provided, enters interactive mode)")
    parser.add_argument("--batch", action="store_true", help="Run example questions in batch mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show Cypher queries and raw results")

    args = parser.parse_args()

    if args.batch:
        print("Running batch mode with example questions...")
        batch_mode(EXAMPLE_QUESTIONS)
    elif args.question:
        # Single question mode
        question = " ".join(args.question)
        result = query_flowrag(question, verbose=args.verbose)

        if "error" in result:
            print(f"\n❌ Error: {result['error']}")
            sys.exit(1)
        else:
            print(f"\n📖 Answer:\n{result['answer']}")
            if args.verbose:
                print(f"\n📊 Result count: {result['result_count']}")
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
