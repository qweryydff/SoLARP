"""
SoLARP – Web Dashboard Server
Serves the landing page and provides API endpoints for live bot data.
Run standalone:  python web_server.py
Or import and call start_server_thread() from main.py.
"""

import json
import os
import time
import logging
import threading
from flask import Flask, jsonify, send_from_directory

from config import STARTING_BALANCE_SOL, POSITIONS_FILE, WEB_SERVER_HOST, WEB_SERVER_PORT

logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", static_url_path="")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _load_portfolio_data() -> dict:
    """Read positions.json and compute stats."""
    data = {
        "balance_sol": STARTING_BALANCE_SOL,
        "positions": {},
        "closed_trades": [],
    }
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            pass

    balance = data.get("balance_sol", STARTING_BALANCE_SOL)
    positions = data.get("positions", {})
    closed = data.get("closed_trades", [])

    # Compute stats
    total_closed_pnl = sum(t.get("pnl_sol", 0) for t in closed)
    wins = sum(1 for t in closed if t.get("pnl_sol", 0) > 0)
    win_rate = (wins / len(closed) * 100) if closed else 0

    # Estimated total balance (free + invested in open positions)
    invested_sol = sum(p.get("sol_invested", 0) for p in positions.values())
    total_balance = balance + invested_sol

    # Best trade
    best_trade = max(closed, key=lambda t: t.get("pnl_sol", 0)) if closed else None
    best_mult = best_trade.get("multiplier", 1) if best_trade else 0

    # Open positions details
    open_positions = []
    for sym, pos in positions.items():
        entry_price = pos.get("entry_price_usd", 0)
        sol_invested = pos.get("sol_invested", 0)
        timestamp = pos.get("timestamp", 0)
        age_hours = (time.time() - timestamp) / 3600 if timestamp else 0
        open_positions.append({
            "symbol": sym,
            "entry_price_usd": entry_price,
            "sol_invested": sol_invested,
            "age_hours": round(age_hours, 1),
            "contract": pos.get("contract", ""),
            "dca_done": pos.get("dca_done", False),
            "partial_sold": pos.get("partial_sold", False),
        })

    # Recent closed trades (last 20)
    recent_trades = []
    for t in reversed(closed[-20:]):
        recent_trades.append({
            "symbol": t.get("symbol", "?"),
            "multiplier": round(t.get("multiplier", 1), 2),
            "pnl_sol": round(t.get("pnl_sol", 0), 4),
            "reason": t.get("reason", ""),
            "timestamp": t.get("timestamp", 0),
        })

    return {
        "balance_sol": round(balance, 4),
        "total_balance_sol": round(total_balance, 4),
        "starting_balance": STARTING_BALANCE_SOL,
        "overall_pnl_sol": round(total_balance - STARTING_BALANCE_SOL, 4),
        "overall_pnl_pct": round((total_balance - STARTING_BALANCE_SOL) / STARTING_BALANCE_SOL * 100, 2),
        "closed_pnl_sol": round(total_closed_pnl, 4),
        "total_trades": len(closed),
        "open_positions_count": len(positions),
        "win_rate": round(win_rate, 1),
        "best_multiplier": round(best_mult, 2),
        "open_positions": open_positions,
        "recent_trades": recent_trades,
    }


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/stats")
def api_stats():
    return jsonify(_load_portfolio_data())


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "timestamp": time.time()})


# ─── Start ───────────────────────────────────────────────────────────────────

def start_server_thread():
    """Start Flask web server in a background daemon thread."""
    def _run():
        logger.info(f"🌐 SoLARP Dashboard starting on http://localhost:{WEB_SERVER_PORT}")
        # use_reloader=False is critical — reloader forks a child process
        # which conflicts with the main bot loop and scheduler.
        app.run(host=WEB_SERVER_HOST, port=WEB_SERVER_PORT, debug=False, use_reloader=False)

    t = threading.Thread(target=_run, daemon=True, name="web-server")
    t.start()
    return t


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info(f"🌐 SoLARP Dashboard starting on http://localhost:{WEB_SERVER_PORT}")
    app.run(host=WEB_SERVER_HOST, port=WEB_SERVER_PORT, debug=True)
