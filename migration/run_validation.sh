#!/bin/bash
# Run validation for disney_knowledge migration

set -e

# Change to project root (relative to script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Running disney_knowledge validation..."
echo "========================================"

# Run the validation script
uv run python migration/validate_disney_knowledge.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Validation PASSED"
elif [ $exit_code -eq 1 ]; then
    echo "Validation FAILED"
else
    echo "Validation ERROR"
fi

exit $exit_code
