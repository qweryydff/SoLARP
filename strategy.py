"""
Trading strategy logic.
Decides WHEN to buy, when to take partial profit, and when to stop-loss.
Now scans ALL trending Solana tokens from DexScreener live.
"""

import logging
import time
import random
from typing import List, Tuple

from config import (
    TAKE_PROFIT_TARGETS,
    PARTIAL_SELL_PCT,
    STOP_LOSS_PCT,
    MAX_POSITIONS,
    POSITION_SIZE_SOL,
)
from portfolio import Portfolio, Position
from price_fetcher import get_token_stats, get_sol_price_usd, scan_trending_solana_tokens

logger = logging.getLogger(__name__)

# DCA trigger: buy more when position is down this much
DCA_TRIGGER_PCT   = 0.20   # -20%
# Early jeet: sell a winner to recover losses when portfolio is in the red
EARLY_JEET_MIN_GAIN = 0.10  # position must be at least +10% to jeet
EARLY_JEET_MAX_GAIN = 0.35  # don't jeet positions already above +35% (let them run)


# ─── Buy Signal ──────────────────────────────────────────────────────────────

def should_buy(symbol: str, stats: dict, portfolio: Portfolio) -> Tuple[bool, str]:
    if symbol in portfolio.positions:
        return False, "already holding"
    if len(portfolio.positions) >= MAX_POSITIONS:
        return False, "max positions reached"
    if portfolio.balance_sol < POSITION_SIZE_SOL:
        return False, "insufficient balance"

    # ── Bezpieczeństwo ────────────────────────────────────────────────────────
    if stats["liquidity_usd"] < 50_000:
        return False, f"low liquidity (${stats['liquidity_usd']:,.0f})"

    if stats["volume_24h"] < 100_000:
        return False, f"low volume (${stats['volume_24h']:,.0f})"

    # Zbyt mały mcap = rug risk
    if stats["fdv"] < 150_000:
        return False, f"mcap too low (${stats['fdv']:,.0f})"

    # Zbyt duży mcap = już po pompie
    if stats["fdv"] > 80_000_000:
        return False, f"mcap too high (${stats['fdv']:,.0f})"

    # ── Momentum ──────────────────────────────────────────────────────────────
    change_1h = stats["price_change_1h"]
    change_6h = stats["price_change_6h"]

    # Musi rosnąć w 1h, ale nie być już po ogromnej pompie (>300% = prawdopodobnie za późno)
    if change_1h < 2.0:
        return False, f"not pumping enough ({change_1h:+.1f}% 1h)"

    if change_1h > 300.0:
        return False, f"pump too big, likely top ({change_1h:+.1f}% 1h)"

    # 6h nie może być ekstremalnie wysoka (>400% = już po pompie)
    if change_6h > 400.0:
        return False, f"6h already mooned ({change_6h:+.1f}%)"

    # 6h musi być pozytywna (trend w górę)
    if change_6h < -15.0:
        return False, f"6h trend negative ({change_6h:+.1f}%)"

    reason = (f"1h +{change_1h:.1f}% | "
              f"6h +{change_6h:.1f}% | "
              f"vol ${stats['volume_24h']:,.0f} | "
              f"liq ${stats['liquidity_usd']:,.0f} | "
              f"mcap ${stats['fdv']:,.0f}")
    return True, reason


# ─── Sell Signals ────────────────────────────────────────────────────────────

class SellSignal:
    NONE      = "none"
    PARTIAL   = "partial"
    FULL_TP   = "full_tp"
    STOP_LOSS = "stop_loss"
    STALE     = "stale"


def check_sell_signal(pos: Position, current_price_usd: float) -> Tuple[str, float]:
    mult = pos.current_multiplier(current_price_usd)

    if mult > pos.highest_mult:
        pos.highest_mult = mult

    # Stop loss
    if mult <= (1 - STOP_LOSS_PCT):
        return SellSignal.STOP_LOSS, mult

    # Take profit levels
    if pos.next_tp_index < len(TAKE_PROFIT_TARGETS):
        target = TAKE_PROFIT_TARGETS[pos.next_tp_index]
        if mult >= target:
            if not pos.partial_sold and pos.next_tp_index == 0:
                pos.next_tp_index += 1
                return SellSignal.PARTIAL, mult
            if pos.next_tp_index >= len(TAKE_PROFIT_TARGETS) - 1:
                return SellSignal.FULL_TP, mult
            pos.next_tp_index += 1
            return SellSignal.PARTIAL, mult

    # Stale: open > 24h and still below 1.5x
    age_hours = (time.time() - pos.timestamp) / 3600
    if age_hours > 24 and mult < 1.5:
        return SellSignal.STALE, mult

    return SellSignal.NONE, mult


# ─── Main scan ───────────────────────────────────────────────────────────────

def scan_and_trade(portfolio: Portfolio, _watchlist_unused: list = None) -> List[dict]:
    """
    1. Check existing positions for sell signals (uses live price per contract).
    2. Fetch ALL trending Solana tokens from DexScreener.
    3. Apply buy signal logic to each one.
    Returns list of event dicts for message generation.
    """
    events = []
    sol_price = get_sol_price_usd()
    logger.info(f"SOL: ${sol_price:.2f} | {portfolio.summary()}")

    # ── 1. Check existing positions ──
    for symbol, pos in list(portfolio.positions.items()):
        stats = get_token_stats(pos.contract)
        if not stats:
            logger.warning(f"Could not get price for {symbol}")
            continue

        current_price = stats["price_usd"]

        # Update current price for real-time PnL on dashboard
        pos.current_price_usd = current_price

        mult          = pos.current_multiplier(current_price)
        signal, mult  = check_sell_signal(pos, current_price)

        if signal == SellSignal.STOP_LOSS:
            result = portfolio.full_sell(symbol, current_price, sol_price, reason="SL")
            if result:
                events.append({"type": "stop_loss", "symbol": symbol,
                                "multiplier": mult, "pnl_sol": result["pnl_sol"]})

        elif signal == SellSignal.PARTIAL:
            result = portfolio.partial_sell(symbol, current_price, sol_price, PARTIAL_SELL_PCT)
            if result:
                events.append({"type": "partial_sell", "symbol": symbol,
                                "multiplier": mult, "pct": PARTIAL_SELL_PCT,
                                "sol_received": result["sol_received"]})

        elif signal == SellSignal.FULL_TP:
            result = portfolio.full_sell(symbol, current_price, sol_price, reason="TP")
            if result:
                events.append({"type": "full_sell", "symbol": symbol,
                                "multiplier": mult, "pnl_sol": result["pnl_sol"]})

        elif signal == SellSignal.STALE:
            result = portfolio.full_sell(symbol, current_price, sol_price, reason="STALE")
            if result:
                events.append({"type": "stale_sell", "symbol": symbol,
                                "multiplier": mult, "pnl_sol": result["pnl_sol"]})

        elif signal == SellSignal.NONE:
            # ── DCA: position down -20%, no DCA done yet ──
            if mult <= (1 - DCA_TRIGGER_PCT) and not pos.dca_done:
                result = portfolio.dca_buy(symbol, current_price, sol_price)
                if result:
                    logger.info(f"DCA {symbol}: added {result['sol_added']:.3f} SOL | new avg: ${result['avg_entry']:.8f}")
                    events.append({
                        "type":      "dca_buy",
                        "symbol":    symbol,
                        "sol_added": result["sol_added"],
                        "avg_entry": result["avg_entry"],
                        "current_price": current_price,
                        "multiplier": mult,
                    })

    # ── 2. Early jeet: if overall portfolio PnL is negative, sell a small winner ──
    # Build current prices dict from what we already fetched in position loop
    current_prices_map = {}
    for symbol, pos in portfolio.positions.items():
        stats = get_token_stats(pos.contract)
        if stats:
            current_prices_map[symbol] = stats["price_usd"]

    overall_pnl = portfolio.total_pnl_sol(current_prices_map)
    if overall_pnl < -0.1:  # in the red by at least 0.1 SOL (including unrealized)
        for symbol, pos in list(portfolio.positions.items()):
            if pos.early_jeet_done:
                continue  # already jeeted this position once
            current_price = current_prices_map.get(symbol, pos.entry_price_usd)
            mult = pos.current_multiplier(current_price)
            gain = mult - 1.0  # e.g. 0.15 = +15%

            if EARLY_JEET_MIN_GAIN <= gain <= EARLY_JEET_MAX_GAIN:
                # Jeet a random portion between 50-100%
                jeet_pct = random.choice([0.5, 0.75, 1.0])
                pos.early_jeet_done = True  # mark before sell to prevent double-trigger
                if jeet_pct == 1.0:
                    result = portfolio.full_sell(symbol, current_price, sol_price, reason="JEET")
                    if result:
                        events.append({
                            "type":       "early_jeet",
                            "symbol":     symbol,
                            "multiplier": mult,
                            "pct":        100,
                            "pnl_sol":    result["pnl_sol"],
                        })
                else:
                    result = portfolio.partial_sell(symbol, current_price, sol_price, jeet_pct)
                    if result:
                        events.append({
                            "type":       "early_jeet",
                            "symbol":     symbol,
                            "multiplier": mult,
                            "pct":        int(jeet_pct * 100),
                            "pnl_sol":    result["sol_received"] - pos.sol_invested * jeet_pct,
                        })
                break  # jeet only one position per scan

    # ── 2. Scan live trending tokens from DexScreener ──
    if len(portfolio.positions) < MAX_POSITIONS:
        logger.info("Scanning DexScreener for trending Solana tokens…")
        trending = scan_trending_solana_tokens(min_volume=150_000, min_liquidity=80_000, limit=50)
        logger.info(f"Evaluating {len(trending)} trending tokens for buy signals")

        for stats in trending:
            symbol   = stats.get("symbol", "").upper()
            contract = stats.get("contract", "")
            if not symbol or not contract:
                continue

            buy_ok, reason = should_buy(symbol, stats, portfolio)
            if buy_ok:
                pos = portfolio.buy(
                    symbol          = symbol,
                    contract        = contract,
                    token_price_usd = stats["price_usd"],
                    sol_price_usd   = sol_price,
                    sol_amount      = POSITION_SIZE_SOL,
                )
                if pos:
                    pos.entry_mcap = stats.get("fdv", 0)
                    portfolio.save()
                    logger.info(f"BUY signal: {symbol} | {reason}")
                    events.append({
                        "type":       "buy",
                        "symbol":     symbol,
                        "contract":   contract,
                        "price_usd":  stats["price_usd"],
                        "sol_amount": POSITION_SIZE_SOL,
                        "reason":     reason,
                        "stats":      stats,
                    })
            else:
                logger.debug(f"SKIP {symbol}: {reason}")
    else:
        logger.info("Max positions reached, skipping buy scan")

    return events

