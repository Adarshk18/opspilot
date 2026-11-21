import argparse
import asyncio
import time
from collections import Counter

import httpx


async def send_one(client: httpx.AsyncClient, method: str, path: str, body: dict | None) -> tuple[str, float]:
    start = time.perf_counter()
    try:
        response = await client.request(method, path, json=body)
        outcome = str(response.status_code)
    except httpx.HTTPError as exc:
        outcome = type(exc).__name__
    return outcome, (time.perf_counter() - start) * 1000


def percentile(sorted_values: list[float], fraction: float) -> float:
    index = min(len(sorted_values) - 1, int(fraction * len(sorted_values)))
    return sorted_values[index]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Send concurrent requests to ShopLite.")
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--method", default="GET")
    parser.add_argument("--path", default="/products")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--product-id", type=int, default=2)
    args = parser.parse_args()

    body = {"product_id": args.product_id, "quantity": 1} if args.method == "POST" else None
    limit = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30) as client:

        async def limited() -> tuple[str, float]:
            async with limit:
                return await send_one(client, args.method, args.path, body)

        results = await asyncio.gather(*(limited() for _ in range(args.requests)))

    outcomes = Counter(outcome for outcome, _ in results)
    latencies = sorted(ms for _, ms in results)
    print(f"outcomes: {dict(outcomes)}")
    print(
        f"p50={percentile(latencies, 0.50):.0f}ms  "
        f"p95={percentile(latencies, 0.95):.0f}ms  "
        f"max={latencies[-1]:.0f}ms"
    )


if __name__ == "__main__":
    asyncio.run(main())