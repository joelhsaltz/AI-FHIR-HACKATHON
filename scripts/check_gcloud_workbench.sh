#!/bin/bash
# PreToolUse hook: block gcloud compute instances start/stop on Workbench instances.
# Workbench instances are managed resources — must use gcloud workbench instances.

set -euo pipefail

INPUT=$(cat)

# Extract the command from the tool input
CMD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Check for gcloud compute instances start/stop targeting our instance
if echo "$CMD" | grep -qE 'gcloud compute instances (start|stop).*fhir-hackathon-instance'; then
    echo "BLOCKED: Cannot use 'gcloud compute instances start/stop' on Workbench instances."
    echo "Workbench instances are managed resources — the Compute Engine API returns 403."
    echo ""
    echo "Use instead:"
    echo "  bash setup_vertex.sh                    # Recommended: handles everything"
    echo "  gcloud workbench instances start/stop    # Direct Workbench API"
    echo ""
    echo "See: /colab-mcp skill or ~/.claude/skills/colab-mcp/SKILL.md"
    exit 2
fi

exit 0
