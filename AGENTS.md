# Repository Guidelines

## Project Structure & Module Organization
- Core service lives in `app/`; `server.py` wires Tornado handlers, `db.py` manages SQLite access, and `eth.py` signs Ethereum transactions.
- HTML templates and forms sit in `app/templates/`, with matching assets under `app/static/`.
- Runtime data (SQLite WAL, logs) defaults to `data/`; keep this directory writable but untracked.
- Environment samples and infrastructure helpers live at the repo root (`.env.example`, `Dockerfile`, `requirements.txt`).

## Build, Test, and Development Commands
- Create an isolated environment: `python3 -m venv .venv && source .venv/bin/activate`.
- Install dependencies: `pip install -r requirements.txt`.
- Run the web service locally: `python -m app.server`; visit `http://localhost:8080`.
- Build a container image when validating deploys: `docker build -t credits-payout-mvp .` and run with `docker run --rm -p 8080:8080 --env-file .env -v $(pwd)/data:/app/data credits-payout-mvp`.

## Coding Style & Naming Conventions
- Follow standard Python formatting: 4-space indents, `snake_case` for functions/variables, `SCREAMING_SNAKE_CASE` for env-driven constants, and type hints for public callables.
- Prefer asynchronous request handlers and `asyncio.to_thread` for blocking DB or Web3 calls to match the existing pattern in `app/server.py`.
- Keep modules small and co-locate Tornado handlers with their templates/static assets for clarity.

## Testing Guidelines
- No automated suite exists yet; add pytest-based tests under `tests/` when touching business logic.
- Name tests descriptively (`test_payout_happy_path.py`) and cover credit ledger math plus idempotency edge cases.
- Before opening a PR, run `pytest -q` (once tests exist) and exercise `/earn`, `/payout`, and `/health` via `curl` or the forms to confirm end-to-end flows.

## Commit & Pull Request Guidelines
- History is absent in this workspace; adopt imperative, present-tense commit subjects (`Add payout retry guard`) and group related changes per commit.
- Pull requests should summarize the change, list manual verification (commands run, endpoints hit), call out config or migration steps, and link any tracking issues.
- Include screenshots or sample payloads when altering templates or response shapes for faster review.

## Security & Configuration Tips
- Never commit secrets; copy `.env.example` to `.env`, populate RPC and key values locally, and rotate compromised keys immediately.
- Confirm Sepolia accounts remain funded before testing payouts, and throttle on-chain calls when scripting bulk payouts.
- If you change `UNITS_PER_CREDIT` or token decimals, document the conversion in your PR to prevent ledger mismatches.
