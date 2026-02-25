"""
Telegram bot handler – obsługuje /start i weryfikację klucza dostępu.
Działa równolegle z główną pętlą tradingową.
"""

import requests
import logging
import time
import threading

from auth import is_authorized, authorize, ACCESS_KEY
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

POLL_INTERVAL = 2  # sekundy między sprawdzaniem nowych wiadomości

# Trzyma ID ostatnio przetworzonej wiadomości żeby nie odpowiadać dwa razy
_last_update_id = 0


def _send(chat_id: int, text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Send error: {e}")


def _get_updates():
    global _last_update_id
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={"offset": _last_update_id + 1, "timeout": 20},
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("result", [])
    except Exception as e:
        logger.error(f"getUpdates error: {e}")
        return []


# chat_id → True/False (czeka na klucz)
_waiting_for_key: set = set()


def _handle_update(update: dict):
    global _last_update_id

    update_id = update.get("update_id", 0)
    if update_id <= _last_update_id:
        return
    _last_update_id = update_id

    msg = update.get("message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text    = msg.get("text", "").strip()
    name    = msg.get("from", {}).get("first_name", "anon")

    # ── /start ──
    if text == "/start":
        if is_authorized(chat_id):
            _send(chat_id, f"👋 welcome back {name}!\nyou're already authorized, signals incoming 🚀")
        else:
            _waiting_for_key.add(chat_id)
            _send(chat_id, "🔐 enter key:")
        return

    # ── /positions ──
    if text == "/positions":
        if not is_authorized(chat_id):
            _send(chat_id, "send /start to get access")
            return
        try:
            from portfolio import Portfolio
            from price_fetcher import get_token_stats, get_sol_price_usd
            portfolio = Portfolio()
            if not portfolio.positions:
                _send(chat_id, "📭 no open positions rn")
                return
            sol_price = get_sol_price_usd()
            lines = ["📊 open positions:\n"]
            for sym, pos in portfolio.positions.items():
                try:
                    stats = get_token_stats(pos.contract)
                    current_price = stats["price_usd"] if stats else pos.entry_price_usd
                    current_fdv   = stats["fdv"] if stats else 0
                except Exception:
                    current_price = pos.entry_price_usd
                    current_fdv   = 0
                mult     = pos.current_multiplier(current_price)
                pnl_sol  = pos.pnl_sol(current_price, sol_price)
                gain_pct = (mult - 1) * 100
                dca_tag  = " [DCA'd]" if pos.dca_done else ""

                # entry mcap = current fdv / current multiplier
                if current_fdv > 0 and mult > 0:
                    entry_fdv = current_fdv / mult
                    if entry_fdv >= 1_000_000_000:
                        entry_mcap_str = f"${entry_fdv/1_000_000_000:.2f}B"
                    elif entry_fdv >= 1_000_000:
                        entry_mcap_str = f"${entry_fdv/1_000_000:.2f}M"
                    elif entry_fdv >= 1_000:
                        entry_mcap_str = f"${entry_fdv/1_000:.1f}K"
                    else:
                        entry_mcap_str = f"${entry_fdv:.0f}"
                else:
                    entry_mcap_str = "unknown"

                lines.append(
                    f"${sym}{dca_tag}\n"
                    f"entry mcap: {entry_mcap_str}\n"
                    f"pnl: {gain_pct:+.1f}% | {pnl_sol:+.3f} SOL\n"
                )
            lines.append(f"balance: {portfolio.balance_sol:.3f} SOL free")
            _send(chat_id, "\n".join(lines))
        except Exception as e:
            logger.error(f"/positions error: {e}")
            _send(chat_id, "⚠️ couldn't fetch positions rn, try again")
        return

    # ── Oczekiwanie na klucz ──
    if chat_id in _waiting_for_key:
        if text == ACCESS_KEY:
            authorize(chat_id)
            _waiting_for_key.discard(chat_id)
            _send(chat_id,
                  f"✅ access granted {name}!\n"
                  f"you'll now receive all trade signals from the bot 📈\n\n"
                  f"#Solana #papertrading")
            logger.info(f"New authorized user: {chat_id} ({name})")
        else:
            _send(chat_id, "❌ wrong key\n\ntry again:")
        return

    # ── Nieznana komenda od niezautoryzowanego ──
    if not is_authorized(chat_id):
        _send(chat_id, "send /start to get access")


def run_bot_listener():
    """Uruchamia polling w osobnym wątku."""
    logger.info("Telegram bot listener started 👂")
    while True:
        try:
            updates = _get_updates()
            for update in updates:
                _handle_update(update)
        except Exception as e:
            logger.error(f"Listener error: {e}")
        time.sleep(POLL_INTERVAL)


def start_listener_thread():
    t = threading.Thread(target=run_bot_listener, daemon=True)
    t.start()
    return t
