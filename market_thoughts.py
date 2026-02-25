"""
Market Thoughts – losowe "przemyślenia rynkowe" w stylu CT degen.
Bazują na aktualnych danych z DexScreener (trending tokens, momentum).
Wysyłane co kilka godzin na kanał i do użytkowników.
"""

import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Template pools ──────────────────────────────────────────────────────────

_BULLISH_OPENERS = [
    "ngl the market is giving me vibes rn 👀",
    "something is brewing on solana fr",
    "charts looking healthy today not gonna lie",
    "momentum is back. slowly but it's there",
    "sol chain has been printing lately",
    "seeing a lot of green on my scanner rn",
    "degens waking up. volume picking up across the board",
    "market feels different today. could be nothing. could be everything",
    "number of tokens pumping 1h is higher than usual. interesting.",
    "sol is doing its thing quietly. i like it",
]

_BEARISH_OPENERS = [
    "market is slow rn not gonna lie",
    "everything just bleeding a little. classic sol",
    "not a lot happening. accumulation phase or just dead?",
    "volume is thin today. waiting for a catalyst",
    "memecoins taking a breather. happens",
    "charts look choppy. patience is a virtue",
    "nothing exciting on the scanner. just noise",
    "market needs a reset before the next leg up imo",
]

_NEUTRAL_OPENERS = [
    "just ran my scanner. here's what i see:",
    "market update from the algo:",
    "current state of solana memecoins:",
    "scanning 200+ pairs rn. quick summary:",
    "mid-session update. things are moving:",
]

_ALPHA_LINES = [
    "volume > liquidity ratio looking sus on a few names. keeping watch",
    "low mcap plays ($200K-$2M range) showing the most momentum rn",
    "best setups have 1h >5% with flat 6h. means early not late",
    "liquidity matters more than mcap imo. always check liq first",
    "anything pumping 50%+ in 1h is usually a second chance dump. careful",
    "DCA triggers hitting on 2 positions. down bad but holding conviction",
    "partial sells locked in some gains. letting winners run on the rest",
    "stop losses are not weakness. they're how you survive to trade again",
    "if you're chasing 1h pumps above 100% you're usually last in",
    "the real alpha is in the 3-15% 1h range. still early, still moving",
    "volume confirms price. no volume = no conviction = no entry",
    "i only buy when 1h momentum + 6h trend + volume all align",
    "most people trade on vibes. i trade on data. both lose sometimes lol",
    "two types of plays: momentum and accumulation. right now it's momentum",
]

_CLOSERS = [
    "not financial advice. i'm a bot. 🤖",
    "nfa. dyor. lfg.",
    "i'm literally an algorithm. don't listen to me.",
    "paper trading only. zero real money. pure simulation.",
    "nfa. i've been wrong before. i'll be wrong again.",
    "just my scanner data. always do your own research.",
    "this is a larp. a very detailed larp. 🦍",
    "not advice. just vibes + data.",
    "remember: paper trading. no real funds at risk here.",
    "i scan 200+ tokens every 45s. this is what the data says.",
]

_MARKET_CONDITIONS = [
    "📊 {hot} tokens pumping 1h+ | {cold} bleeding | {flat} flat",
    "🔥 top sector: low-cap memes ($200K-$2M mcap)",
    "💧 avg liquidity on trending pairs: ${avg_liq}",
    "📈 {hot} tokens with positive 1h momentum out of top 30 scanned",
    "⚡ {scans} pairs evaluated this session",
]


# ─── Generator ───────────────────────────────────────────────────────────────

def build_market_thought(portfolio=None) -> str:
    """
    Buduje losowy post z 'przemyśleniami rynkowymi'.
    Opcjonalnie uwzględnia dane z portfolio (otwarte pozycje, PnL).
    """
    parts = []

    # 1. Opener — bullish/bearish/neutral losowo
    mood = random.choices(["bullish", "bearish", "neutral"], weights=[50, 25, 25])[0]
    if mood == "bullish":
        parts.append(random.choice(_BULLISH_OPENERS))
    elif mood == "bearish":
        parts.append(random.choice(_BEARISH_OPENERS))
    else:
        parts.append(random.choice(_NEUTRAL_OPENERS))

    parts.append("")  # pusty wiersz

    # 2. Alpha lines — 2-3 losowe
    alpha_count = random.randint(2, 3)
    chosen_alpha = random.sample(_ALPHA_LINES, alpha_count)
    for line in chosen_alpha:
        parts.append(f"→ {line}")

    parts.append("")

    # 3. Portfolio context (jeśli dostępny)
    if portfolio:
        open_count = len(portfolio.positions)
        closed_count = len(portfolio.closed_trades)
        balance = portfolio.balance_sol
        win_rate = portfolio.win_rate()

        if open_count > 0:
            symbols = ", ".join(f"${s}" for s in list(portfolio.positions.keys())[:4])
            parts.append(f"currently holding: {symbols}{'...' if open_count > 4 else ''}")

        if closed_count > 0:
            parts.append(f"trades closed this session: {closed_count} | win rate: {win_rate:.0f}%")

        parts.append(f"free balance: {balance:.2f} SOL")
        parts.append("")

    # 4. Closer
    parts.append(random.choice(_CLOSERS))

    return "\n".join(parts)


def send_market_thought(portfolio, telegram_poster, twitter_poster=None):
    """Generuje i wysyła przemyślenie rynkowe."""
    try:
        from web_server import append_to_feed
        thought = build_market_thought(portfolio)
        logger.info(f"\n{'─'*50}\nMARKET THOUGHT\n{thought}\n{'─'*50}")

        telegram_poster.post(thought)
        append_to_feed(thought, kind="thought")

        if twitter_poster:
            twitter_poster.post(thought)

    except Exception as e:
        logger.error(f"market_thought error: {e}")
