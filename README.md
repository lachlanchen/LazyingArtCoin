# Cryptocurrency Credits Payout MVP (Tornado + SQLite + Web3)

This is a minimal Tornado web service that lets your website award credits to users and pay them out in cryptocurrency (ETH or an ERC‑20 token).

- SQLite ledger for user credits and payouts
- REST endpoints and simple HTML forms
- Ethereum/Web3 signing with a private key (Sepolia by default)
- Idempotent payouts via `idempotency_key`

## Features
- Earn credits: increase a user’s credit balance
- Request payout: convert credits → on-chain transfer
- Basic nonce locking and idempotency tracking
- Minimal UI: forms for earn/payout and a user page for history

## Quick Start (Local)

1) Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Configure environment

Create `.env` (or export vars) with your RPC and key. For Sepolia:

```bash
cp .env.example .env
# edit .env and set WEB3_PROVIDER_URL + PAYOUT_PRIVATE_KEY
```

Required env vars:
- `WEB3_PROVIDER_URL` – your Ethereum RPC (e.g., Alchemy/Infura Sepolia)
- `PAYOUT_PRIVATE_KEY` – private key that pays out (funded for gas)

Optional env vars:
- `CHAIN_ID` – default `11155111` (Sepolia)
- `TOKEN_ADDRESS` – ERC‑20 token address; if unset, pays native ETH
- `TOKEN_DECIMALS` – override token decimals (default tries `decimals()`)
- `UNITS_PER_CREDIT` – base units per credit (default `1e15 wei` => 0.001 ETH)
- `DB_PATH` – SQLite file path (default `data/app.db`)
- `PORT` – server port (default `8080`)

3) Run the server

```bash
python -m app.server
```

Open http://localhost:8080 to use the forms.

### Web UI
- Home (`/`): forms to award credits and request a payout.
- User page (`/user/<id>`): shows current credit balance and payout history.
- Health (`/health`): shows the payer address and whether token mode is enabled.

The server loads `.env` automatically (via python-dotenv) before reading config, so running `python -m app.server` with a `.env` file in the project root is sufficient.

## Endpoints
- `GET /health` – health and config info
- `POST /earn` – award credits
  - JSON: `{ "user_id": "u1", "credits": 100 }`
  - Form: `user_id`, `credits`
- `POST /payout` – request payout
  - JSON: `{ "user_id": "u1", "address": "0x...", "credits": 50, "idempotency_key": "uuid-1" }`
  - Form: `user_id`, `address`, `credits`, optional `idempotency_key`
- `GET /user/<user_id>` – user balance + payout history

## Docker

Build and run:

```bash
docker build -t credits-payout-mvp .
# copy .env with your values in the same dir
docker run --rm -p 8080:8080 --env-file .env -v $(pwd)/data:/app/data credits-payout-mvp
```

## Notes
- This is an MVP. For production, use a real queue + DB transactions, HSM/key vault, and custodial payout infra if possible.
- Compliance: paying users can be regulated. Confirm legal/tax obligations in your jurisdiction.
- Security: never commit `.env` or private keys; use a vault/KMS and strict network access.

## License
MIT (example; adapt to your needs).
