#!/bin/bash
# Convenient wrapper for querying Flux documentation
# Usage: ./ask_flux.sh "Your question here"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect if we're in flowrag-master or parent directory
if [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
    # We're inside flowrag-master
    VENV_PYTHON="${SCRIPT_DIR}/venv/bin/python3"
    # Check if query script is in current dir first, then parent
    if [ -f "${SCRIPT_DIR}/query_flux_workflow.py" ]; then
        QUERY_SCRIPT="${SCRIPT_DIR}/query_flux_workflow.py"
    else
        QUERY_SCRIPT="${SCRIPT_DIR}/../query_flux_workflow.py"
    fi
else
    # We're in parent directory
    VENV_PYTHON="${SCRIPT_DIR}/flowrag-master/venv/bin/python3"
    QUERY_SCRIPT="${SCRIPT_DIR}/query_flux_workflow.py"
fi

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment not found at: $VENV_PYTHON"
    echo "   Please run: cd flowrag-master && python3 -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# Check if query script exists
if [ ! -f "$QUERY_SCRIPT" ]; then
    echo "❌ Query script not found at: $QUERY_SCRIPT"
    exit 1
fi

# Check if .env file exists
ENV_FILE="${SCRIPT_DIR}/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  Warning: .env file not found at: $ENV_FILE"
    echo "   The script will continue but may fail if OPENAI_API_KEY is not set"
    echo "   Create a .env file with: OPENAI_API_KEY='your-key-here'"
fi

# If no arguments, show usage
if [ $# -eq 0 ]; then
    cat << EOF
Usage: $0 <question> [options]

Examples:
  $0 "How do I set up a Flux node?"
  $0 "What are the prerequisites?" --steps 10
  $0 --demo                          # Show demo queries
  $0 --interactive                   # Interactive mode

Options:
  --steps N      Number of steps to retrieve (default: 10)
  --demo         Run demo queries
  --interactive  Interactive chat mode

EOF
    exit 0
fi

# Run the query
unset DEBUG
exec "$VENV_PYTHON" "$QUERY_SCRIPT" "$@"
