"""
Configuration for the Solana Memecoin Papertrading Bot
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Fake Balance ────────────────────────────────────────────────────────────
STARTING_BALANCE_SOL = float(os.getenv("STARTING_BALANCE_SOL", "10.0"))  # 10 SOL fake money

# ─── Trading Settings ────────────────────────────────────────────────────────
MAX_POSITIONS         = int(os.getenv("MAX_POSITIONS", "8"))           # max concurrent open trades
POSITION_SIZE_SOL     = float(os.getenv("POSITION_SIZE_SOL", "0.2"))  # SOL per trade
TAKE_PROFIT_TARGETS   = [2.0, 3.0, 5.0, 10.0]                        # 2x, 3x, 5x, 10x
PARTIAL_SELL_PCT      = 0.5                                            # sell 50% at first target
STOP_LOSS_PCT         = 0.30                                           # stop loss at -30%
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "45")) # how often to scan/update

# ─── Twitter (X) ─────────────────────────────────────────────────────────────
TWITTER_ENABLED          = os.getenv("TWITTER_ENABLED", "false").lower() == "true"
TWITTER_API_KEY          = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET       = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN     = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET    = os.getenv("TWITTER_ACCESS_SECRET", "")
TWITTER_BEARER_TOKEN     = os.getenv("TWITTER_BEARER_TOKEN", "")

# ─── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_ENABLED    = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")  # kanał np. @solarpbot lub -1001234567890

# ─── Solana / Price Source ────────────────────────────────────────────────────
# Bot automatically scans DexScreener for ALL trending Solana tokens.
# No manual watchlist needed — it discovers tokens live.
WATCHLIST_TOKENS = []  # legacy, no longer used

DEXSCREENER_URL  = "https://api.dexscreener.com/latest/dex/tokens/"
SOL_PRICE_URL    = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
LOG_FILE         = "bot.log"
POSITIONS_FILE   = "positions.json"

# ─── Web Dashboard ────────────────────────────────────────────────────────────
WEB_SERVER_HOST  = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT  = int(os.getenv("WEB_SERVER_PORT", "5000"))
