#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ $# -ne 1 ]; then
  echo "Usage: scripts/chaos.sh '<json>'   e.g. scripts/chaos.sh '{\"error_rate\": 0.4}'" >&2
  exit 1
fi

TOKEN=$(grep ADMIN_TOKEN target_app/.env | cut -d= -f2)
if ! curl -sf -X PUT http://localhost:8001/admin/chaos \
    -H "x-admin-token: $TOKEN" -H "Content-Type: application/json" -d "$1"; then
  echo "ERROR: could not set chaos. Is ShopLite running? Is the JSON valid?" >&2
  exit 1
fi
echo