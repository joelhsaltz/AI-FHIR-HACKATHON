#!/bin/bash
# Vertex AI Workbench setup — ensures instance is running and tunnel is open.
# Designed to run as a Claude Code PreToolUse hook (fast, quiet on happy path).
#
# Architecture:
#   - Discovery: gcloud compute instances list (single API call, all zones)
#   - XSRF fix: baked into VM via startup-script metadata (no manual config)
#   - Idle shutdown: 60-min via idle-timeout-seconds metadata (no stop hook needed)
#   - SSH tunnel: gcloud compute ssh (Workbench VMs are Compute Engine instances)

set -euo pipefail

INSTANCE_NAME="fhir-hackathon-instance"
PROJECT_ID="joel-vertex-project"
STATE_DIR="$HOME/.vertex-ai"
ZONE_FILE="$STATE_DIR/active-zone"
LOCAL_PORT=8888
REMOTE_PORT=8080

QUIET=false
if [[ "${1:-}" == "--quiet" ]] || [[ -n "${CLAUDE_HOOK:-}" ]]; then
    QUIET=true
fi

log() {
    if [[ "$QUIET" == false ]]; then
        echo "$@"
    fi
}

# --- Fast path: tunnel up and Jupyter responding → exit immediately ---
if lsof -i :$LOCAL_PORT > /dev/null 2>&1; then
    if curl -s --max-time 3 http://localhost:$LOCAL_PORT/api > /dev/null 2>&1; then
        log "Vertex AI Workbench already connected on port $LOCAL_PORT."
        exit 0
    else
        # Tunnel process exists but Jupyter not responding — kill stale tunnel
        log "Stale tunnel detected, killing..."
        lsof -ti :$LOCAL_PORT | xargs kill 2>/dev/null || true
        sleep 1
    fi
fi

# --- Discover instance (single API call across all zones) ---
log "Finding $INSTANCE_NAME..."
DISCOVERY=$(gcloud compute instances list \
    --filter="name=$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --format="value(zone,status)" 2>/dev/null || true)

if [[ -z "$DISCOVERY" ]]; then
    echo "ERROR: Instance $INSTANCE_NAME not found in project $PROJECT_ID." >&2
    echo "Create it first via: gcloud workbench instances create $INSTANCE_NAME --location=<zone> --project=$PROJECT_ID --machine-type=e2-standard-4" >&2
    exit 1
fi

ZONE=$(echo "$DISCOVERY" | awk '{print $1}')
STATUS=$(echo "$DISCOVERY" | awk '{print $2}')
log "Found in $ZONE (status: $STATUS)"

# Save zone for other scripts
mkdir -p "$STATE_DIR"
echo "$ZONE" > "$ZONE_FILE"

# --- Start instance if not running ---
if [[ "$STATUS" == "TERMINATED" || "$STATUS" == "STOPPED" || "$STATUS" == "SUSPENDED" ]]; then
    log "Starting instance..."
    gcloud workbench instances start "$INSTANCE_NAME" \
        --location="$ZONE" \
        --project="$PROJECT_ID" \
        --quiet 2>&1 | grep -v "^$" || true

    # Wait for RUNNING
    for i in $(seq 1 36); do
        STATUS=$(gcloud compute instances list \
            --filter="name=$INSTANCE_NAME" \
            --project="$PROJECT_ID" \
            --format="value(status)" 2>/dev/null || echo "UNKNOWN")
        if [[ "$STATUS" == "RUNNING" ]]; then
            break
        fi
        log "  Waiting for RUNNING... ($STATUS)"
        sleep 5
    done

    if [[ "$STATUS" != "RUNNING" ]]; then
        echo "ERROR: Instance did not reach RUNNING (status: $STATUS)." >&2
        exit 1
    fi
    log "Instance is RUNNING."
fi

# --- Open SSH tunnel ---
log "Opening SSH tunnel ($LOCAL_PORT -> $REMOTE_PORT)..."
gcloud compute ssh "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    -- -L "$LOCAL_PORT:localhost:$REMOTE_PORT" -N -f 2>&1 | grep -v "^$" || true
sleep 2

# --- Health check (up to ~2 minutes for cold starts with startup-script) ---
for i in $(seq 1 24); do
    if curl -s --max-time 3 http://localhost:$LOCAL_PORT/api > /dev/null 2>&1; then
        log "Vertex AI Workbench is live at http://localhost:$LOCAL_PORT"
        exit 0
    fi
    sleep 5
done

echo "ERROR: Tunnel open but Jupyter not responding on port $LOCAL_PORT." >&2
exit 2
