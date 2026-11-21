import random 

from pydantic import BaseModel, Field

class ChaosConfig(BaseModel):
    db_latency_seconds: float = Field(default=0, ge=0, le=10)
    hold_connection_seconds: float = Field(default=0, ge=0, le=30)
    error_rate: float = Field(default=0, ge=0, le=1)
    leak_mb_per_request: int = Field(default=0, ge=0, le=50)


class PaymentProviderError(Exception):
    """Simulates a failing third party dependency"""


_config = ChaosConfig()
_leak: list[bytes] = []


def get_config()-> ChaosConfig:
    return _config


def set_config(new_config: ChaosConfig)-> None:
    global _config
    _config = new_config


def reset()->None:
    set_config(ChaosConfig())
    _leak.clear()

def maybe_fail() -> None:
    """Raise an error for a random fraction of calls."""
    if _config.error_rate > 0 and random.random() < _config.error_rate:
        raise PaymentProviderError("payment provider timed out after 3000ms")


def maybe_leak() -> None:
    """Keep a chunk of memory forever, like a real leak."""
    if _config.leak_mb_per_request > 0:
        _leak.append(b"x" * (_config.leak_mb_per_request * 1024 * 1024))


def leaked_mb() -> int:
    return sum(len(chunk) for chunk in _leak) // (1024 * 1024)

