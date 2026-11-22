# Local Runbook: OpsPilot Development Environment
 
Daily routine for starting, using, and stopping the OpsPilot lab on a local machine (Windows + WSL2 Ubuntu).
 
## Terminal layout
 
| Terminal | Folder | Job | Stays running? |
|---|---|---|---|
| **T1** | `target_app/` | ShopLite server | Yes, don't type here |
| **T2** | project root and `target_app/` | Infrastructure, chaos, load | No, command terminal |
| **T3** | `backend/` | OpsPilot agent | No |
 
Open terminals in VS Code with **Terminal → New Terminal**, then rename each one (right-click → Rename) to T1, T2, T3.
 
---
 
## Daily startup
 
### Step 0: Before any terminal
 
1. Start **Docker Desktop** on Windows and wait until it says it's running.
2. Open Ubuntu and run:
```bash
cd ~/code/opspilot && code .
```
 
   Confirm VS Code shows **WSL: Ubuntu** in the bottom-left corner.
 
### Step 1: Infrastructure (T2)
 
```bash
cd ~/code/opspilot
docker compose up -d
docker compose ps
```
 
Expected: `opspilot-postgres` and `shoplite-postgres` show **(healthy)**, and `opspilot-litellm` is **running**. The gateway starts slowly; wait about 30 seconds on first start.
 
```bash
curl -s http://localhost:4000/health/liveliness
```
 
Expected: a response like `"I'm alive!"`.
 
### Step 2: ShopLite (T1)
 
```bash
cd ~/code/opspilot/target_app
uv run alembic upgrade head
uv run uvicorn app.main:app --port 8001 2>&1 | tee -a ../logs/shoplite.jsonl | jq -R 'fromjson? // .'
```
 
- `alembic upgrade head` is safe to run every day. If the database is up to date, it does nothing.
- Wait for `"Application startup complete."`
### Step 3: Verify and reset (T2)
 
```bash
cd ~/code/opspilot
curl -s http://localhost:8001/health/ready
./scripts/reset-lab.sh
export TOKEN=$(grep ADMIN_TOKEN ~/code/opspilot/target_app/.env | cut -d= -f2)
cd target_app
```
 
Expected: `{"status":"ready","database":"ok"}`, then `Lab reset: chaos off, logs cleared.`
 
`export TOKEN` only applies to the terminal where it was run. Run it again in any new terminal used for chaos commands.
 
### Step 4: Agent (T3)
 
```bash
cd ~/code/opspilot/backend
```
 
The agent is ready. Run it after creating an incident.
 
---
 
## Running one experiment
 
Always the same four steps.
 
**1. Reset (T2):**
 
```bash
~/code/opspilot/scripts/reset-lab.sh
```
 
**2. Turn on one chaos setting (T2, in `target_app/`):**
 
```bash
curl -i -X PUT http://localhost:8001/admin/chaos \
  -H "x-admin-token: $TOKEN" -H "Content-Type: application/json" \
  -d 'CHAOS_JSON'
```
 
**3. Send traffic (T2, in `target_app/`):** use the load command from the table below.
 
**4. Ask the agent (T3, in `backend/`):**
 
```bash
uv run python -m app.cli "QUESTION"
```
 
| Incident | `CHAOS_JSON` | Load command | Question |
|---|---|---|---|
| INC-01 slow DB | `{"db_latency_seconds": 2}` | none needed | "The product page feels very slow." |
| INC-02 pool exhaustion | `{"hold_connection_seconds": 3}` | `uv run python scripts/load.py --method POST --path /orders --requests 15 --concurrency 10` | "Checkout is timing out for many customers." |
| INC-03 payment failure | `{"error_rate": 0.4}` | `uv run python scripts/load.py --method POST --path /orders --requests 30 --concurrency 5` | "Customers say checkout is failing." |
| INC-04 memory leak | `{"leak_mb_per_request": 5}` | `uv run python scripts/load.py --requests 40 --concurrency 5` | "Memory alerts are firing on ShopLite." |
 
After each run, add a row to `docs/agent-runs.md`.
 
### Refill stock
 
If orders start returning 409 (T2, project root):
 
```bash
docker compose exec shop-postgres psql -U shop -d shop -c "UPDATE products SET stock = 100 WHERE id = 2;"
```
 
### Measure the latency baseline
 
With chaos off (T2, in `target_app/`), run three times:
 
```bash
uv run python scripts/load.py --requests 20 --concurrency 20
```
 
Keep the baseline in the agent's system prompt up to date with these numbers.
 
---
 
## Shutting down
 
1. **T1:** press Ctrl + C to stop ShopLite.
2. **T2:**
```bash
cd ~/code/opspilot
docker compose stop
```
 
3. Commit anything that changed:
```bash
git status
git add -A
git commit -m "type(scope): what changed"
git push
```
 
Use **`docker compose stop`**, never `docker compose down -v`. `stop` keeps containers and data. `down -v` deletes the databases, including the LiteLLM virtual key and its spending history.
 
| Command | Containers | Volumes (data) |
|---|---|---|
| `docker compose stop` | Stopped, still exist | Kept |
| `docker compose down` | Stopped and deleted | Kept |
| `docker compose down -v` | Stopped and deleted | **Deleted** |
 
---
 
## Quick troubleshooting
 
| Symptom | Likely cause | Fix |
|---|---|---|
| `ConnectError` from load script, or curl "Failed to connect" to 8001 | ShopLite isn't running | Check T1 and restart it |
| `docker: command not found` | Docker Desktop not started, or WSL integration off | Start Docker Desktop. If running, check Settings → Resources → WSL integration → Ubuntu |
| Admin endpoint returns **404** | `$TOKEN` not set in this terminal, or `.env` changed after ShopLite started | Re-run the `export TOKEN` line, or restart ShopLite |
| Agent fails with **401/403** from the gateway | Wrong or missing `LLM_API_KEY` in `backend/.env` | Check the key; run `docker compose logs litellm` |
| Agent fails with a connection error to port 4000 | Gateway container not running | `docker compose ps`, then `docker compose up -d litellm` |
| `Address already in use` | An old ShopLite process is still running | `lsof -i :8001` shows the PID; `kill <PID>` stops it |
| Code changes have no effect | ShopLite runs without `--reload` | Restart T1 after every code change |
| Diagnosis mentions old errors | Logs weren't reset | Run `./scripts/reset-lab.sh` before every experiment |
| Agent says "fallback skipped: not authorized" | Virtual key doesn't include `agent-fallback` | Update the key's `models` via `/key/update` |
 
---
 
## Ports
 
| Port | Service |
|---|---|
| 8000 | OpsPilot backend (FastAPI) |
| 8001 | ShopLite (target app) |
| 4000 | LiteLLM gateway (localhost only) |
| 5432 | OpsPilot Postgres (pgvector) |
| 5433 | ShopLite Postgres |
 