#!/bin/bash
# Clean up local SSH tunnel only.
# The VM handles its own shutdown via idle-timeout-seconds metadata (60 min).
# This runs as a Claude Code Stop hook — must be fast and non-blocking.

LOCAL_PORT=8888

if lsof -ti :$LOCAL_PORT > /dev/null 2>&1; then
    lsof -ti :$LOCAL_PORT | xargs kill 2>/dev/null || true
fi
