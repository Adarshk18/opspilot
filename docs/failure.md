# Failure Log

## 2026-11-19: Logging setup bugs in ShopLite

**Symptoms:** `/products` returned 500. Each startup log line appeared 3 times. "--- Logging error ---" messages.

**Root causes:**
1. Typo in the middleware left `token` undefined; the `finally` block crashed.
2. `formatexception` instead of `formatException` crashed the formatter.
3. uvicorn loggers had their own handlers *and* propagated to root → 3 copies per message.
4. Original middleware design reset the request ID in `finally` before the summary log, so it logged `request_id: null`.

**Fix:** Corrected typos, cleared uvicorn handlers, moved summary logging into `finally` with reset as the last step.

**Prevention:** Run `ruff check` before running code; add Ruff to CI (week 10).