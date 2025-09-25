import errno
import os
import json
import asyncio
from typing import Any, Dict

from dotenv import load_dotenv
import tornado.ioloop
import tornado.web

# Load environment before importing modules that read env at import time
load_dotenv()

if __package__ in (None, ""):
    # Allow running as `python app/server.py` by adding the project root to sys.path
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, eth, settings as app_settings


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


class HealthHandler(tornado.web.RequestHandler):
    def get(self):
        status = eth.current_status()
        self.write({
            "status": "ok" if status["configured"] else "needs_config",
            "from": status["from_address"],
            "token_mode": bool(status["token_mode"]),
            "asset": status["asset"] or "ETH",
            "error": status["error"],
        })


class EarnHandler(tornado.web.RequestHandler):
    async def post(self):
        if self.request.headers.get("Content-Type", "").startswith("application/json"):
            data = json.loads(self.request.body or b"{}")
        else:
            data = {k: self.get_body_argument(k) for k in ["user_id", "credits"] if self.get_body_argument(k, None) is not None}
        try:
            user_id = str(data["user_id"]).strip()
            credits = int(data["credits"])  # type: ignore
            if credits <= 0:
                raise ValueError("credits must be > 0")
        except Exception as e:
            self.set_status(400)
            self.write({"error": f"bad request: {e}"})
            return

        new_balance = await asyncio.to_thread(db.add_credits, user_id, credits, "earn")

        if self.request.headers.get("Accept", "").startswith("application/json"):
            self.write({"user_id": user_id, "credits_total": new_balance})
        else:
            self.redirect(f"/user/{user_id}")


class PayoutHandler(tornado.web.RequestHandler):
    async def post(self):
        if self.request.headers.get("Content-Type", "").startswith("application/json"):
            data = json.loads(self.request.body or b"{}")
        else:
            fields = ["user_id", "address", "credits", "idempotency_key"]
            data = {k: self.get_body_argument(k, None) for k in fields}
        try:
            user_id = str(data["user_id"]).strip()
            to = eth.as_checksum(str(data["address"]))
            credits = int(data["credits"])  # type: ignore
            idempotency_key = (data.get("idempotency_key") or "").strip() or None  # type: ignore
            if credits <= 0:
                raise ValueError("credits must be > 0")
        except Exception as e:
            self.set_status(400)
            self.write({"error": f"bad request: {e}"})
            return

        try:
            eth.ensure_ready()
        except eth.PayoutConfigError as exc:
            self.set_status(503)
            self.write({"error": str(exc)})
            return

        status = eth.current_status()
        units = credits * eth.UNITS_PER_CREDIT
        asset = status["asset"] or "ETH"

        # Create a pending payout and reserve credits
        try:
            payout_row = await asyncio.to_thread(
                db.debit_credits_for_payout, user_id, credits, to, str(units), asset, idempotency_key
            )
        except ValueError as e:
            self.set_status(400)
            self.write({"error": str(e)})
            return
        except Exception as e:
            self.set_status(500)
            self.write({"error": f"could not create payout: {e}"})
            return

        # If already exists and was returned due to idempotency, short-circuit
        if payout_row.get("status") != "pending":
            self.write({
                "payout": payout_row,
            })
            return

        try:
            if status["token_mode"]:
                tx_hash = await eth.send_erc20(to, units)
            else:
                tx_hash = await eth.send_native(to, units)
        except Exception as e:
            # Note: For MVP, we keep the debit and mark pending; admins can reconcile/refund manually.
            self.set_status(502)
            self.write({
                "error": f"payout broadcast failed: {str(e)[:200]}",
                "payout": payout_row,
            })
            return

        await asyncio.to_thread(db.set_payout_sent, payout_row["id"], tx_hash)

        result = {
            "status": "sent",
            "tx_hash": tx_hash,
            "asset": asset,
            "to": to,
            "credits_debited": credits,
            "units_sent": str(units),
            "payout_id": payout_row["id"],
        }

        if self.request.headers.get("Accept", "").startswith("application/json"):
            self.write(result)
        else:
            self.redirect(f"/user/{user_id}")


class UserPageHandler(tornado.web.RequestHandler):
    async def get(self, user_id: str):
        bal = await asyncio.to_thread(lambda: db.get_balance(db._connect(), user_id))
        payouts = list(await asyncio.to_thread(lambda: list(db.list_user_payouts(user_id))))
        self.render("user.html", user_id=user_id, balance=bal, payouts=payouts)


class SettingsHandler(tornado.web.RequestHandler):
    def get(self):
        status = eth.current_status()
        snapshot = app_settings.snapshot()
        env_overrides = {key: app_settings.has_env_override(key) for key in app_settings.MANAGED_KEYS}
        self.render(
            "settings.html",
            status=status,
            settings=snapshot,
            masked_private_key=app_settings.masked("PAYOUT_PRIVATE_KEY"),
            env_overrides=env_overrides,
            saved=self.get_query_argument("saved", default="0") == "1",
            error_message=None,
        )

    def post(self):
        env_overrides = {key: app_settings.has_env_override(key) for key in app_settings.MANAGED_KEYS}
        updates = {}
        errors = []

        def _value(name: str) -> Optional[str]:
            raw = self.get_body_argument(name, "").strip()
            return raw or None

        # Simple numeric validation helpers
        numeric_fields = {
            "CHAIN_ID": "Chain ID",
            "UNITS_PER_CREDIT": "Units per credit",
            "TOKEN_DECIMALS": "Token decimals",
        }

        for key in ["WEB3_PROVIDER_URL", "CHAIN_ID", "TOKEN_ADDRESS", "TOKEN_DECIMALS", "UNITS_PER_CREDIT"]:
            if env_overrides.get(key):
                continue
            value = _value(key)
            if value and key in numeric_fields:
                try:
                    int(value, 0)
                except ValueError:
                    errors.append(f"{numeric_fields[key]} must be an integer (dec or 0x hex)")
            updates[key] = value

        if not env_overrides.get("PAYOUT_PRIVATE_KEY"):
            clear_flag = self.get_body_argument("clear_private_key", "") == "on"
            provided = _value("PAYOUT_PRIVATE_KEY")
            if clear_flag:
                updates["PAYOUT_PRIVATE_KEY"] = None
            elif provided:
                updates["PAYOUT_PRIVATE_KEY"] = provided

        if errors:
            status = eth.current_status()
            snapshot = app_settings.snapshot()
            self.set_status(400)
            self.render(
                "settings.html",
                status=status,
                settings=snapshot,
                masked_private_key=app_settings.masked("PAYOUT_PRIVATE_KEY"),
                env_overrides=env_overrides,
                saved=False,
                error_message="; ".join(errors),
            )
            return

        if updates:
            app_settings.set_many({k: v for k, v in updates.items() if k in app_settings.MANAGED_KEYS})
        eth.reload()
        self.redirect("/settings?saved=1")


def make_app() -> tornado.web.Application:
    settings = dict(
        debug=True,
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        autoreload=False,
    )
    return tornado.web.Application(
        [
            (r"/", IndexHandler),
            (r"/health", HealthHandler),
            (r"/earn", EarnHandler),
            (r"/payout", PayoutHandler),
            (r"/user/(.+)", UserPageHandler),
            (r"/settings", SettingsHandler),
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": settings["static_path"]}),
        ],
        **settings,
    )


def _bind_with_fallback(app: tornado.web.Application, preferred_port: int, attempts: int = 5) -> int:
    port = preferred_port
    for _ in range(attempts):
        try:
            app.listen(port)
            return port
        except OSError as exc:
            if getattr(exc, "errno", None) != errno.EADDRINUSE:
                raise
            port += 1
    raise RuntimeError(f"Could not bind to ports {preferred_port}-{port}")


def main():
    db.init_db()
    app = make_app()
    preferred_port = int(os.environ.get("PORT", "8080"))
    bound_port = _bind_with_fallback(app, preferred_port)
    from_addr = eth.current_from_address() or "unconfigured"
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Listening on :{bound_port} as {from_addr}.")
    print(f"Open http://{host}:{bound_port}/ in your browser.")
    if bound_port != preferred_port:
        print(f"Port {preferred_port} was busy; using {bound_port} instead.")
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
