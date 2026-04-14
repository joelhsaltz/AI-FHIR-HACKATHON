#!/bin/bash
# PreToolUse hook: block notebook uploads to Drive unless verified.
# Checks for .last_verified_<notebook_stem> timestamp file.
# Called before mcp__google-personal__create_drive_file.

set -euo pipefail

PROJECT_ROOT="/Users/joelsaltz/fhir-hackathon"

# Read the tool input from stdin (JSON)
INPUT=$(cat)

# Check if this is a notebook upload (filename ends in .ipynb)
FILENAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_name',''))" 2>/dev/null || echo "")

if [[ "$FILENAME" != *.ipynb ]]; then
    exit 0  # Not a notebook upload, allow
fi

# Extract notebook stem (e.g., "you_are_the_agent_demo" from "you_are_the_agent_demo.ipynb")
STEM="${FILENAME%.ipynb}"
VERIFY_FILE="$PROJECT_ROOT/.last_verified_$STEM"
NOTEBOOK_FILE="$PROJECT_ROOT/notebooks/$FILENAME"

if [[ ! -f "$VERIFY_FILE" ]]; then
    echo "BLOCKED: Notebook '$FILENAME' has not been verified in this session."
    echo "Run the smoke test and Vertex AI verification before distributing."
    echo "  python test_demo_notebook.py"
    echo "After verification passes, run: touch $VERIFY_FILE"
    exit 2
fi

# Check if notebook is newer than verification timestamp
if [[ -f "$NOTEBOOK_FILE" && "$NOTEBOOK_FILE" -nt "$VERIFY_FILE" ]]; then
    echo "BLOCKED: Notebook '$FILENAME' was modified after last verification."
    echo "The generator was changed — re-run verification before distributing."
    echo "  python create_prototype_demo.py && python test_demo_notebook.py"
    echo "After verification passes, run: touch $VERIFY_FILE"
    exit 2
fi

exit 0
