import asyncio

from app import chaos

PROVIDER_TIMEOUT_SECONDS = 3


class PaymentProviderError(Exception):
    """Raised when the external payment provider does not respond in time."""


async def authorize(product_id: int, quantity: int) -> None:
    """Simulated call to an external payment provider."""
    if chaos.should_fail_payment():
        await asyncio.sleep(PROVIDER_TIMEOUT_SECONDS)
        raise PaymentProviderError(
            f"payment provider timed out after {PROVIDER_TIMEOUT_SECONDS * 1000}ms"
        )