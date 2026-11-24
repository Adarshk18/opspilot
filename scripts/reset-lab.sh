#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! curl -sf http://localhost:8001/health/live > /dev/null; then
  echo "ERROR: ShopLite is not reachable on port 8001. Start it in T1 first." >&2
  exit 1
fi

TOKEN=$(grep ADMIN_TOKEN target_app/.env | cut -d= -f2)
if ! curl -sf -X DELETE -H "x-admin-token: $TOKEN" http://localhost:8001/admin/chaos > /dev/null; then
  echo "ERROR: Could not reset chaos. Check ADMIN_TOKEN in target_app/.env." >&2
  exit 1
fi

: > logs/shoplite.jsonl
echo "Lab reset: chaos off, logs cleared, stock restored."

docker compose exec -T shop-postgres psql -U shop -d shop -q -c \
  "UPDATE products SET stock = 50 WHERE id = 1; UPDATE products SET stock = 100 WHERE id = 2; UPDATE products SET stock = 5 WHERE id = 3;"