import os
from typing import Dict, Optional

from . import db

MANAGED_KEYS = {
    "WEB3_PROVIDER_URL": "Ethereum RPC endpoint",
    "PAYOUT_PRIVATE_KEY": "Hot wallet private key",
    "CHAIN_ID": "Chain ID",
    "TOKEN_ADDRESS": "ERC-20 contract address",
    "TOKEN_DECIMALS": "ERC-20 decimals override",
    "UNITS_PER_CREDIT": "Base units per credit",
}


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def get(key: str) -> Optional[str]:
    env_val = os.environ.get(key)
    if env_val is not None and env_val.strip():
        return env_val.strip()
    return db.get_setting(key)


def set(key: str, value: Optional[str]) -> None:
    if key not in MANAGED_KEYS:
        raise KeyError(f"Unsupported setting: {key}")
    db.set_setting(key, _normalize(value))


def set_many(updates: Dict[str, Optional[str]]) -> None:
    for key, value in updates.items():
        set(key, value)


def snapshot() -> Dict[str, Optional[str]]:
    return {key: get(key) for key in MANAGED_KEYS}


def masked(key: str) -> Optional[str]:
    if has_env_override(key):
        return "Configured via environment"
    value = get(key)
    if not value:
        return None
    if len(value) <= 10:
        return value
    return f"{value[:6]}…{value[-4:]}"


def env_override(key: str) -> Optional[str]:
    value = os.environ.get(key)
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def has_env_override(key: str) -> bool:
    return env_override(key) is not None
