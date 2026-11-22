#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

TOKEN=$(grep ADMIN_TOKEN target_app/.env | cut -d= -f2)
curl -sf -X DELETE -H "x-admin-token: $TOKEN" http://localhost:8001/admin/chaos > /dev/null
: > logs/shoplite.jsonl

echo "Lab reset: chaos off, logs cleared."