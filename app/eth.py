import asyncio
import threading
from typing import Any, Dict, Optional

from . import settings

try:
    from web3 import Web3  # type: ignore
    from eth_account import Account  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Web3 = None  # type: ignore
    Account = None  # type: ignore

DEFAULT_CHAIN_ID = 11155111
DEFAULT_UNITS_PER_CREDIT = 1_000_000_000_000_000  # 0.001 ETH


def _load_int(name: str, default: int) -> int:
    raw = settings.get(name)
    if raw is None:
        return default
    try:
        return int(raw, 0)
    except ValueError:
        return default


def _load_str(name: str) -> str:
    value = settings.get(name)
    return value.strip() if isinstance(value, str) else ""


CHAIN_ID = _load_int("CHAIN_ID", DEFAULT_CHAIN_ID)
UNITS_PER_CREDIT = _load_int("UNITS_PER_CREDIT", DEFAULT_UNITS_PER_CREDIT)
TOKEN_ADDRESS = _load_str("TOKEN_ADDRESS")
TOKEN_DECIMALS_OVERRIDE = _load_str("TOKEN_DECIMALS")

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
]


class PayoutConfigError(RuntimeError):
    pass


class _State:
    web3: Optional[Any] = None
    payer_account: Optional[Any] = None
    from_address: Optional[str] = None
    erc20: Optional[Any] = None
    token_symbol: Optional[str] = None
    token_decimals: Optional[int] = None
    error: Optional[str] = None
    initialized: bool = False


_state = _State()
_state_lock = threading.Lock()
nonce_lock = asyncio.Lock()


def reload() -> None:
    global CHAIN_ID, UNITS_PER_CREDIT, TOKEN_ADDRESS, TOKEN_DECIMALS_OVERRIDE
    with _state_lock:
        _state.web3 = None
        _state.payer_account = None
        _state.from_address = None
        _state.erc20 = None
        _state.token_symbol = None
        _state.token_decimals = None
        _state.error = None
        _state.initialized = False
    CHAIN_ID = _load_int("CHAIN_ID", DEFAULT_CHAIN_ID)
    UNITS_PER_CREDIT = _load_int("UNITS_PER_CREDIT", DEFAULT_UNITS_PER_CREDIT)
    TOKEN_ADDRESS = _load_str("TOKEN_ADDRESS")
    TOKEN_DECIMALS_OVERRIDE = _load_str("TOKEN_DECIMALS")


def _initialize_if_needed() -> None:
    if _state.initialized or _state.error:
        return
    with _state_lock:
        if _state.initialized or _state.error:
            return
        if Web3 is None or Account is None:
            _state.error = "web3.py dependencies are not installed"
            return

        provider = _load_str("WEB3_PROVIDER_URL")
        private_key = _load_str("PAYOUT_PRIVATE_KEY")
        required_pairs = [
            ("WEB3_PROVIDER_URL", provider),
            ("PAYOUT_PRIVATE_KEY", private_key),
        ]
        missing = [name for name, value in required_pairs if not value]
        if missing:
            _state.error = f"Missing payout settings: {', '.join(missing)}"
            return

        try:
            web3 = Web3(Web3.HTTPProvider(provider, request_kwargs={"timeout": 30}))
        except Exception as exc:  # pragma: no cover - initialization error
            _state.error = f"Failed to create Web3 provider: {exc}"[:200]
            return

        try:
            if not web3.is_connected():
                _state.error = "Web3 provider unreachable"
                return
        except Exception as exc:
            _state.error = f"Web3 provider health check failed: {exc}"[:200]
            return

        try:
            payer_account = Account.from_key(private_key)
        except Exception as exc:
            _state.error = f"Private key invalid: {exc}"[:200]
            return

        erc20 = None
        token_symbol: Optional[str] = None
        token_decimals: Optional[int] = None
        token_address = TOKEN_ADDRESS
        if token_address:
            try:
                token_addr = Web3.to_checksum_address(token_address)
                erc20 = web3.eth.contract(address=token_addr, abi=ERC20_ABI)
                if TOKEN_DECIMALS_OVERRIDE:
                    token_decimals = int(TOKEN_DECIMALS_OVERRIDE, 0)
                else:
                    token_decimals = erc20.functions.decimals().call()
                try:
                    token_symbol = erc20.functions.symbol().call()
                except Exception:
                    token_symbol = "TOKEN"
            except Exception as exc:
                _state.error = f"ERC-20 setup failed: {exc}"[:200]
                return

        _state.web3 = web3
        _state.payer_account = payer_account
        _state.from_address = payer_account.address
        _state.erc20 = erc20
        _state.token_symbol = token_symbol
        _state.token_decimals = token_decimals
        _state.error = None
        _state.initialized = True


def is_configured() -> bool:
    _initialize_if_needed()
    return _state.initialized and _state.error is None


def current_status() -> Dict[str, Optional[Any]]:
    _initialize_if_needed()
    asset = _state.token_symbol or ("ETH" if _state.initialized and _state.error is None and not TOKEN_ADDRESS else None)
    return {
        "configured": _state.initialized and _state.error is None,
        "from_address": _state.from_address,
        "token_mode": bool(_state.erc20),
        "asset": asset,
        "error": _state.error,
    }


def current_from_address() -> Optional[str]:
    _initialize_if_needed()
    return _state.from_address


def ensure_ready() -> None:
    _initialize_if_needed()
    if _state.error:
        raise PayoutConfigError(_state.error)
    if not _state.initialized:
        raise PayoutConfigError("Payout configuration incomplete")


def as_checksum(addr: str) -> str:
    if Web3 is None:
        raise PayoutConfigError("web3.py is not installed")
    if not Web3.is_address(addr):
        raise ValueError("invalid address")
    return Web3.to_checksum_address(addr)


async def send_native(to_address: str, amount_wei: int) -> str:
    ensure_ready()
    if _state.web3 is None or _state.payer_account is None or _state.from_address is None:
        raise PayoutConfigError("Payout engine not initialized")
    async with nonce_lock:
        nonce = await asyncio.to_thread(_state.web3.eth.get_transaction_count, _state.from_address, "pending")
        gas_price = await asyncio.to_thread(lambda: _state.web3.eth.gas_price)
        tx = {
            "chainId": CHAIN_ID,
            "nonce": nonce,
            "to": to_address,
            "value": amount_wei,
            "gas": 21_000,
            "gasPrice": gas_price,
        }
        signed = _state.payer_account.sign_transaction(tx)
        tx_hash = await asyncio.to_thread(_state.web3.eth.send_raw_transaction, signed.rawTransaction)
        return tx_hash.hex()


async def send_erc20(to_address: str, amount_units: int) -> str:
    ensure_ready()
    if _state.web3 is None or _state.payer_account is None or _state.from_address is None or _state.erc20 is None:
        raise PayoutConfigError("ERC-20 payout not configured")
    async with nonce_lock:
        fn = _state.erc20.functions.transfer(to_address, amount_units)
        try:
            gas_estimate = await asyncio.to_thread(fn.estimate_gas, {"from": _state.from_address})
        except Exception:
            gas_estimate = 60_000
        gas_price = await asyncio.to_thread(lambda: _state.web3.eth.gas_price)
        nonce = await asyncio.to_thread(_state.web3.eth.get_transaction_count, _state.from_address, "pending")
        tx = fn.build_transaction(
            {
                "chainId": CHAIN_ID,
                "gas": gas_estimate,
                "gasPrice": gas_price,
                "nonce": nonce,
            }
        )
        signed = _state.payer_account.sign_transaction(tx)
        tx_hash = await asyncio.to_thread(_state.web3.eth.send_raw_transaction, signed.rawTransaction)
        return tx_hash.hex()


def describe_asset() -> str:
    status = current_status()
    if status["token_mode"]:
        return status["asset"] or "TOKEN"
    return "ETH"


def token_decimals() -> Optional[int]:
    _initialize_if_needed()
    return _state.token_decimals


# Initialize state using any existing settings on import
reload()
