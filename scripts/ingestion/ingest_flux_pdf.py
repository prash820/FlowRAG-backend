"""
Ingest Flux Light Node Setup PDF - Extract Workflow Steps
This script demonstrates FlowRAG's document processing capabilities
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from databases.neo4j.client import Neo4jClient
from config import get_settings
import hashlib
import uuid
from datetime import datetime

# Initialize clients
settings = get_settings()
openai_client = OpenAI(api_key=settings.openai_api_key)
qdrant_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
neo4j_client = Neo4jClient()
neo4j_client.connect()

NAMESPACE = "flux_setup_guide"
COLLECTION = "flux_documents"

# Extracted workflow steps from the PDF
FLUX_WORKFLOW = {
    "title": "Flux Light Node Setup Guide",
    "author": "Ali Malik",
    "document_type": "Technical Setup Guide",
    "main_phases": [
        {
            "phase": "Prerequisites",
            "step_number": 1,
            "steps": [
                {
                    "id": "prereq_1",
                    "name": "Download ZelCore Wallet",
                    "description": "Download the latest ZelCore Wallet from zelcore.io and choose your platform",
                    "dependencies": [],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "prereq_2",
                    "name": "Login or Register",
                    "description": "Existing users can login OR if brand new user, register new account with recovery password mechanism",
                    "dependencies": ["prereq_1"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "prereq_3",
                    "name": "Enable d2FA (Optional)",
                    "description": "Enable Decentralized Two-factor authentication for extra security. Requires 0.0002 Flux",
                    "dependencies": ["prereq_2"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "prereq_4",
                    "name": "Add Flux Asset",
                    "description": "Click on + sign to add FLUX and other assets to your wallet",
                    "dependencies": ["prereq_2"],
                    "estimated_time": "2 minutes"
                },
                {
                    "id": "prereq_5",
                    "name": "Purchase Flux Tokens",
                    "description": "Buy FLUX from exchanges: CoinMetro, Kucoin, or Gate Exchange",
                    "dependencies": ["prereq_4"],
                    "estimated_time": "15 minutes"
                }
            ]
        },
        {
            "phase": "Wallet Configuration",
            "step_number": 2,
            "steps": [
                {
                    "id": "wallet_1",
                    "name": "Transfer Collateral",
                    "description": "Send exactly 1,000 FLUX (Cumulus), 12,500 FLUX (Nimbus), or 40,000 FLUX (Stratus) to your ZelCore wallet",
                    "dependencies": ["prereq_5"],
                    "estimated_time": "10 minutes"
                },
                {
                    "id": "wallet_2",
                    "name": "Wait for Confirmations",
                    "description": "Wait for minimum 100 confirmations (~3.5 hours) before starting the node",
                    "dependencies": ["wallet_1"],
                    "estimated_time": "210 minutes"
                },
                {
                    "id": "wallet_3",
                    "name": "Configure FluxNode Details",
                    "description": "Click on FluxNode > Edit. Provide NodeName and IP address from VPS provider",
                    "dependencies": ["wallet_2"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "wallet_4",
                    "name": "Copy ZelId",
                    "description": "Apps > ZelTools > Zel Id > Copy the ZelId for later use",
                    "dependencies": ["wallet_3"],
                    "estimated_time": "2 minutes"
                }
            ]
        },
        {
            "phase": "VPS Setup",
            "step_number": 3,
            "steps": [
                {
                    "id": "vps_1",
                    "name": "Choose VPS Provider",
                    "description": "Select VPS provider that meets minimum requirements (Ubuntu 20.04 recommended)",
                    "dependencies": [],
                    "estimated_time": "15 minutes",
                    "parallel_with": ["wallet_1"]
                },
                {
                    "id": "vps_2",
                    "name": "Install SSH Client (Windows)",
                    "description": "Download and install PuTTY from chiark.greenend.org.uk for SSH access on Windows",
                    "dependencies": ["vps_1"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "vps_3",
                    "name": "Connect via SSH",
                    "description": "Use root credentials provided by VPS to connect via SSH",
                    "dependencies": ["vps_2"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "vps_4",
                    "name": "Install Prerequisites",
                    "description": "Run: sudo apt-get install curl && sudo apt-get install npm -y",
                    "dependencies": ["vps_3"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "vps_5",
                    "name": "Benchmark VPS (Optional)",
                    "description": "Install sysbench and run CPU/disk benchmarks to verify VPS meets requirements",
                    "dependencies": ["vps_4"],
                    "estimated_time": "10 minutes"
                }
            ]
        },
        {
            "phase": "Docker Installation",
            "step_number": 4,
            "steps": [
                {
                    "id": "docker_1",
                    "name": "Run Multitoolbox Script",
                    "description": "Execute: bash -i <(curl -s https://raw.githubusercontent.com/RunOnFlux/fluxnode-multitool/master/multitoolbox.sh)",
                    "dependencies": ["vps_5", "wallet_2"],
                    "estimated_time": "2 minutes"
                },
                {
                    "id": "docker_2",
                    "name": "Select Docker Install",
                    "description": "Choose Option 1: Install Docker from the multitoolbox menu",
                    "dependencies": ["docker_1"],
                    "estimated_time": "1 minute"
                },
                {
                    "id": "docker_3",
                    "name": "Create User Account",
                    "description": "Enter username (same as FluxNode name in ZelCore) and set password",
                    "dependencies": ["docker_2"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "docker_4",
                    "name": "Complete Docker Installation",
                    "description": "Wait for Docker installation to complete. Press Y when prompted to switch to user account",
                    "dependencies": ["docker_3"],
                    "estimated_time": "10 minutes"
                }
            ]
        },
        {
            "phase": "FluxNode Installation",
            "step_number": 5,
            "steps": [
                {
                    "id": "flux_1",
                    "name": "Run Multitoolbox Again",
                    "description": "Execute multitoolbox script again after Docker installation",
                    "dependencies": ["docker_4"],
                    "estimated_time": "1 minute"
                },
                {
                    "id": "flux_2",
                    "name": "Select FluxNode Install",
                    "description": "Choose Option 2: Install FluxNode from menu",
                    "dependencies": ["flux_1"],
                    "estimated_time": "1 minute"
                },
                {
                    "id": "flux_3",
                    "name": "Enter FluxNode Private Key",
                    "description": "Paste the Node Private Key from ZelCore wallet (from Edit FluxNode page)",
                    "dependencies": ["flux_2", "wallet_3"],
                    "estimated_time": "2 minutes"
                },
                {
                    "id": "flux_4",
                    "name": "Enter Collateral TX ID",
                    "description": "Paste the Collateral TX ID from ZelCore wallet",
                    "dependencies": ["flux_3"],
                    "estimated_time": "1 minute"
                },
                {
                    "id": "flux_5",
                    "name": "Enter Output Index",
                    "description": "Enter the Output Index (usually 0 or 1) from ZelCore wallet",
                    "dependencies": ["flux_4"],
                    "estimated_time": "1 minute"
                },
                {
                    "id": "flux_6",
                    "name": "Download Bootstrap",
                    "description": "Select Option 1 to download bootstrap file from source (recommended). Takes 10-15 minutes",
                    "dependencies": ["flux_5"],
                    "estimated_time": "15 minutes"
                },
                {
                    "id": "flux_7",
                    "name": "Enter ZelId",
                    "description": "Paste the ZelId copied earlier from ZelCore wallet",
                    "dependencies": ["flux_6"],
                    "estimated_time": "2 minutes"
                },
                {
                    "id": "flux_8",
                    "name": "Blockchain Sync",
                    "description": "Wait for Flux blockchain to sync. Monitor connection status. Takes 45-60 minutes",
                    "dependencies": ["flux_7"],
                    "estimated_time": "60 minutes"
                },
                {
                    "id": "flux_9",
                    "name": "Setup Alert Notifications (Optional)",
                    "description": "Configure Discord webhook for node status alerts",
                    "dependencies": ["flux_8"],
                    "estimated_time": "10 minutes"
                }
            ]
        },
        {
            "phase": "Verification and Start",
            "step_number": 6,
            "steps": [
                {
                    "id": "verify_1",
                    "name": "Check Benchmarks",
                    "description": "Run: fluxbench-cli getbenchmarks to verify node meets tier requirements (CUMULUS/NIMBUS/STRATUS)",
                    "dependencies": ["flux_9"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "verify_2",
                    "name": "Restart Benchmarks if Failed",
                    "description": "If benchmark status shows Failed, run: fluxbench-cli restartnodebenchmarks",
                    "dependencies": ["verify_1"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "verify_3",
                    "name": "Final Checklist",
                    "description": "Verify IP address, private key, TX ID, output index, 100 confirmations, and benchmark pass",
                    "dependencies": ["verify_2"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "verify_4",
                    "name": "Start FluxNode from Wallet",
                    "description": "In ZelCore wallet, click Start button on FluxNode. Confirm benchmarks passed, then click Start FluxNode",
                    "dependencies": ["verify_3"],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "verify_5",
                    "name": "Wait for Confirmation",
                    "description": "Status will change from OFFLINE > STARTING > CONFIRMED (takes 1-10 blocks, 2-20 minutes)",
                    "dependencies": ["verify_4"],
                    "estimated_time": "20 minutes"
                },
                {
                    "id": "verify_6",
                    "name": "Monitor Node Status",
                    "description": "Expect first rewards in 48 hours. Monitor via ZelCore FluxNodes dashboard",
                    "dependencies": ["verify_5"],
                    "estimated_time": "ongoing"
                }
            ]
        }
    ]
}


def create_embedding(text):
    """Create OpenAI embedding for text"""
    response = openai_client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text
    )
    return response.data[0].embedding


def init_qdrant_collection():
    """Initialize Qdrant collection"""
    try:
        qdrant_client.get_collection(COLLECTION)
        print(f"✅ Collection '{COLLECTION}' already exists")
    except:
        qdrant_client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=1536,  # OpenAI embedding size
                distance=Distance.COSINE
            )
        )
        print(f"✅ Created collection '{COLLECTION}'")


def init_neo4j_schema():
    """Initialize Neo4j constraints and indexes"""
    try:
        # Create constraints
        neo4j_client.execute_write("""
            CREATE CONSTRAINT step_id IF NOT EXISTS
            FOR (s:Step) REQUIRE s.id IS UNIQUE
        """)

        neo4j_client.execute_write("""
            CREATE CONSTRAINT phase_id IF NOT EXISTS
            FOR (p:Phase) REQUIRE p.id IS UNIQUE
        """)

        # Create indexes
        neo4j_client.execute_write("""
            CREATE INDEX step_namespace IF NOT EXISTS
            FOR (s:Step) ON (s.namespace)
        """)

        print("✅ Neo4j schema initialized")
    except Exception as e:
        print(f"⚠️  Schema initialization: {e}")


def ingest_workflow():
    """Ingest Flux workflow into Neo4j and Qdrant"""

    print("\n🚀 Starting Flux Light Node Setup ingestion...\n")

    # Initialize
    init_qdrant_collection()
    init_neo4j_schema()

    # Create document node
    doc_id = str(uuid.uuid4())
    neo4j_client.execute_write("""
        MERGE (d:Document {id: $doc_id})
        SET d.title = $title,
            d.author = $author,
            d.doc_type = $doc_type,
            d.namespace = $namespace,
            d.created_at = datetime()
    """, {
        "doc_id": doc_id,
        "title": FLUX_WORKFLOW["title"],
        "author": FLUX_WORKFLOW["author"],
        "doc_type": FLUX_WORKFLOW["document_type"],
        "namespace": NAMESPACE
    })

    print(f"✅ Created document node: {FLUX_WORKFLOW['title']}")

    # Process each phase
    total_steps = 0
    vectors_to_upsert = []

    for phase_data in FLUX_WORKFLOW["main_phases"]:
        phase_id = f"phase_{phase_data['step_number']}"
        phase_name = phase_data["phase"]

        # Create phase node
        neo4j_client.execute_write("""
            MERGE (p:Phase {id: $phase_id})
            SET p.name = $name,
                p.step_number = $step_number,
                p.namespace = $namespace

            WITH p
            MATCH (d:Document {id: $doc_id})
            MERGE (d)-[:HAS_PHASE]->(p)
        """, {
            "phase_id": phase_id,
            "name": phase_name,
            "step_number": phase_data["step_number"],
            "namespace": NAMESPACE,
            "doc_id": doc_id
        })

        print(f"\n📋 Phase {phase_data['step_number']}: {phase_name}")

        # Process steps in this phase
        prev_step_id = None

        for step in phase_data["steps"]:
            step_id = f"{NAMESPACE}:{step['id']}"
            total_steps += 1

            # Create step node in Neo4j
            neo4j_client.execute_write("""
                MERGE (s:Step {id: $step_id})
                SET s.name = $name,
                    s.description = $description,
                    s.estimated_time = $estimated_time,
                    s.namespace = $namespace,
                    s.step_type = $step_type

                WITH s
                MATCH (p:Phase {id: $phase_id})
                MERGE (p)-[:CONTAINS]->(s)
            """, {
                "step_id": step_id,
                "name": step["name"],
                "description": step["description"],
                "estimated_time": step.get("estimated_time", "unknown"),
                "namespace": NAMESPACE,
                "phase_id": phase_id,
                "step_type": "parallel" if "parallel_with" in step else "sequential"
            })

            # Create dependencies
            for dep_id in step.get("dependencies", []):
                dep_full_id = f"{NAMESPACE}:{dep_id}"
                neo4j_client.execute_write("""
                    MATCH (s:Step {id: $step_id})
                    MATCH (d:Step {id: $dep_id})
                    MERGE (s)-[:DEPENDS_ON]->(d)
                """, {
                    "step_id": step_id,
                    "dep_id": dep_full_id
                })

            # Create parallel relationships
            if "parallel_with" in step:
                for parallel_id in step["parallel_with"]:
                    parallel_full_id = f"{NAMESPACE}:{parallel_id}"
                    neo4j_client.execute_write("""
                        MATCH (s:Step {id: $step_id})
                        MATCH (p:Step {id: $parallel_id})
                        MERGE (s)-[:PARALLEL_WITH]->(p)
                        MERGE (p)-[:PARALLEL_WITH]->(s)
                    """, {
                        "step_id": step_id,
                        "parallel_id": parallel_full_id
                    })

            # Create sequential relationship with previous step
            if prev_step_id and not step.get("dependencies"):
                neo4j_client.execute_write("""
                    MATCH (s:Step {id: $step_id})
                    MATCH (p:Step {id: $prev_id})
                    MERGE (s)-[:FOLLOWS]->(p)
                """, {
                    "step_id": step_id,
                    "prev_id": prev_step_id
                })

            # Create embedding for Qdrant
            step_text = f"{step['name']}: {step['description']}"
            embedding = create_embedding(step_text)

            # Generate deterministic UUID from step_id
            point_id = str(uuid.UUID(hashlib.md5(step_id.encode()).hexdigest()))

            vectors_to_upsert.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "step_id": step_id,
                    "name": step["name"],
                    "description": step["description"],
                    "phase": phase_name,
                    "phase_number": phase_data["step_number"],
                    "estimated_time": step.get("estimated_time", "unknown"),
                    "namespace": NAMESPACE,
                    "doc_title": FLUX_WORKFLOW["title"],
                    "step_type": "parallel" if "parallel_with" in step else "sequential"
                }
            ))

            print(f"  ✓ Step: {step['name']}")
            prev_step_id = step_id

    # Upsert vectors to Qdrant in batches
    batch_size = 100
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i+batch_size]
        qdrant_client.upsert(
            collection_name=COLLECTION,
            points=batch
        )

    print(f"\n✅ Ingested {total_steps} steps into Qdrant")
    print(f"✅ Created {len(FLUX_WORKFLOW['main_phases'])} phases in Neo4j")

    # Calculate total estimated time
    total_time = calculate_total_time()
    print(f"\n⏱️  Total estimated time: {total_time} minutes (~{total_time//60} hours {total_time%60} minutes)")


def calculate_total_time():
    """Calculate critical path time through the workflow"""
    result = neo4j_client.execute_query("""
        MATCH path = (s:Step {namespace: $namespace})
        WHERE NOT (s)-[:DEPENDS_ON]->()
        WITH s
        CALL {
            WITH s
            MATCH (s)-[:DEPENDS_ON*0..]->(dep:Step)
            RETURN sum(toInteger(split(dep.estimated_time, ' ')[0])) as total_time
        }
        RETURN max(total_time) as critical_path_time
    """, {"namespace": NAMESPACE})

    if result and len(result) > 0:
        return result[0].get("critical_path_time", 0)
    return 0


def demo_query(query_text):
    """Demo semantic search on ingested workflow"""
    print(f"\n🔍 Query: '{query_text}'")

    # Create query embedding
    query_embedding = create_embedding(query_text)

    # Search Qdrant
    results = qdrant_client.search(
        collection_name=COLLECTION,
        query_vector=query_embedding,
        limit=5,
        score_threshold=0.7,
        query_filter={
            "must": [
                {"key": "namespace", "match": {"value": NAMESPACE}}
            ]
        }
    )

    print(f"\n📊 Found {len(results)} relevant steps:\n")

    for i, hit in enumerate(results, 1):
        print(f"{i}. {hit.payload['name']} (Score: {hit.score:.3f})")
        print(f"   Phase: {hit.payload['phase']}")
        print(f"   Description: {hit.payload['description']}")
        print(f"   Estimated Time: {hit.payload['estimated_time']}\n")

    return results


if __name__ == "__main__":
    # Ingest the workflow
    ingest_workflow()

    # Demo queries
    print("\n" + "="*80)
    print("🎯 DEMO QUERIES")
    print("="*80)

    demo_query("How do I set up a Flux light node?")
    demo_query("What steps can I do in parallel?")
    demo_query("What do I need to complete before running the Multitoolbox script?")

    print("\n✨ Demo complete! Check Neo4j browser at http://localhost:7474")
    print("   Username: neo4j")
    print("   Password: your-password-here")
    print("\n📝 Try this Cypher query:")
    print("   MATCH (d:Document)-[:HAS_PHASE]->(p:Phase)-[:CONTAINS]->(s:Step)")
    print("   WHERE d.namespace = 'flux_setup_guide'")
    print("   RETURN d, p, s")
