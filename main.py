"""
Main entry point for the Solana Memecoin Papertrading Bot.

Run:  python main.py

This starts THREE things in parallel:
  1. Web dashboard   → http://localhost:5000  (Flask, background thread)
  2. Telegram listener (bot commands /start, /positions …)
  3. Trading loop    (scans DexScreener, executes paper trades, posts to Telegram/Twitter)
"""

import logging
import time
import sys
import os
import schedule
import requests as _requests

from config import WATCHLIST_TOKENS, SCAN_INTERVAL_SECONDS, WEB_SERVER_PORT
from portfolio import Portfolio
from strategy import scan_and_trade
from message_generator import build_post, build_daily_summary
from twitter_poster import TwitterPoster
from telegram_poster import TelegramPoster
from bot_listener import start_listener_thread
from web_server import start_server_thread, append_to_feed
from market_thoughts import send_market_thought

# ─── Logging setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


# ─── Globals ─────────────────────────────────────────────────────────────────
portfolio = Portfolio()
twitter   = TwitterPoster()
telegram  = TelegramPoster()


# ─── Core loop ───────────────────────────────────────────────────────────────

def run_scan():
    logger.info("═" * 60)
    logger.info("Running scan …")

    events = scan_and_trade(portfolio, WATCHLIST_TOKENS)

    for event in events:
        post = build_post(event, portfolio)
        if not post:
            continue

        logger.info(f"\n{'─'*50}\n{post}\n{'─'*50}")

        # Post to Twitter
        twitter.post(post)

        # Post to Telegram
        telegram.post(post)

        # Save to web feed
        kind = event.get("type", "trade")
        append_to_feed(post, kind=kind)

        # Small delay between posts so we don't spam
        time.sleep(2)

    if not events:
        logger.info("No trades this scan.")


def run_daily_summary():
    summary = build_daily_summary(portfolio)
    logger.info(f"\n{'═'*50}\nDAILY SUMMARY\n{summary}\n{'═'*50}")
    twitter.post(summary)
    telegram.post(summary)
    append_to_feed(summary, kind="summary")


def run_market_thought():
    send_market_thought(portfolio, telegram, twitter)


def keep_alive():
    """Ping own web server every 14 min so Render free tier doesn't sleep."""
    render_url = os.getenv("RENDER_EXTERNAL_URL", "")
    if not render_url:
        return
    try:
        _requests.get(f"{render_url}/api/stats", timeout=10)
        logger.debug("Keep-alive ping sent.")
    except Exception:
        pass


# ─── Scheduler ───────────────────────────────────────────────────────────────

def start():
    logger.info("🚀 Solana Memecoin Papertrading Bot starting …")
    logger.info(f"   Scan interval: {SCAN_INTERVAL_SECONDS}s")
    logger.info(f"   {portfolio.summary()}")

    # Start web dashboard (Flask) in background thread
    start_server_thread()
    logger.info(f"   Web dashboard running 🌐  http://localhost:{WEB_SERVER_PORT}")

    # Start Telegram bot listener (handles /start and key verification)
    start_listener_thread()
    logger.info("   Telegram listener running 👂 (key: SOLAPE2026)")

    # Run immediately on start
    run_scan()

    # Schedule periodic scans
    schedule.every(SCAN_INTERVAL_SECONDS).seconds.do(run_scan)

    # Market thoughts every 1 hour
    schedule.every(1).hours.do(run_market_thought)

    # Send first market thought immediately on start
    run_market_thought()

    # Keep-alive ping every 14 min (prevents Render free tier from sleeping)
    schedule.every(14).minutes.do(keep_alive)

    # Daily summary at 20:00
    schedule.every().day.at("20:00").do(run_daily_summary)

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
        portfolio.save()


if __name__ == "__main__":
    start()
