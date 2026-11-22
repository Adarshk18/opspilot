# Incident Catalog

| ID | Chaos switch | User-visible symptom | Key evidence | Correct diagnosis |
|---|---|---|---|---|
| INC-01 | db_latency_seconds=2 | All requests succeed but slowly | p50 ~2000ms at concurrency 5, ~4000ms at concurrency 10; no errors | Slow database queries; requests queue for connections under load |
| INC-02 | hold_connection_seconds=3 + concurrent orders | ~half of orders fail, rest very slow | 500s with TimeoutError (pool limit); max latency ~20s from row-lock waits; checked_out = 5 | Long transactions holding row locks exhaust the connection pool; no lock_timeout |
| INC-03 | error_rate=0.4 | ~40% of orders fail, fast | 500s with PaymentProviderError; p50 ~40ms; pool not saturated | Third-party payment provider failing |
| INC-04 | leak_mb_per_request=5 | No errors, latency higher than baseline | memory_rss_mb grows ~5MB per request (before: ?, after: ?) | Memory leak in /products |