"""
Generates human-style social media posts about trades.
Mimics the tone of a degen CT trader.
"""

import random
from typing import Optional
from portfolio import Portfolio


# ─── Copy banks ──────────────────────────────────────────────────────────────

BUY_TEMPLATES = [
    "just ape'd into ${symbol} 🦍\nsmall bag, watching how it moves",
    "i buy a small amount of ${symbol} 👀\nlets see how it moves",
    "picked up some ${symbol} 👁️\n1h momentum looking decent rn",
    "entered ${symbol} 🎯\nchart looks good, letting it cook",
    "snagged a small ${symbol} bag 💼\nwe'll see if it pumps",
    "buying ${symbol} rn\nvol is moving",
]

PARTIAL_SELL_TEMPLATES = [
    "i have {mult} on ${symbol}, i sold {pct}% 💰\nstill holding the rest, letting runners run",
    "${symbol} is at {mult} 🚀\ntook {pct}% off the table, free ride from here",
    "secured {pct}% profits on ${symbol} at {mult} ✅\nkeeping rest for higher targets",
    "partial exit on ${symbol} 🎯\n{mult} bag → sold {pct}%, holding the rest",
    "${symbol} printing 🖨️ | {mult}\ncashed out {pct}%, riding free tokens now",
]

FULL_TP_TEMPLATES = [
    "closed ${symbol} at {mult} 💸\n{pnl_sol} SOL profit\nnot bad",
    "took full profit on ${symbol} 🏁\n{mult} from entry\n{pnl_sol} SOL",
    "${symbol} done ✅\nfull close at {mult}\nbanked {pnl_sol} SOL",
    "sold everything on ${symbol} 💰\n{mult} exit | {pnl_sol} SOL\nonto the next",
]

STOP_LOSS_TEMPLATES = [
    "took the L on ${symbol} 🔴\n{pnl_sol} SOL\nit happens, moving on",
    "stopped out of ${symbol} 😮‍💨\n{pnl_sol} SOL\nmoving on",
    "${symbol} wasn't it 🫠\n{pnl_sol} SOL\ncut losses, stay disciplined",
    "sold ${symbol} at a loss 🔴\n{pnl_sol} SOL\ncan't win every trade",
]

STALE_SELL_TEMPLATES = [
    "closing ${symbol}, not moving 🥱\n{pnl_sol} SOL\ncapital better used elsewhere",
    "${symbol} closed after 48h\n{pnl_sol} SOL\nfreed up capital",
]

DCA_TEMPLATES = [
    "adding more ${symbol} 📉➕\ndown {down_pct}% — averaging down my entry\nnew avg: {avg_entry}",
    "dca'd into ${symbol} 💸\nposition was -${down_pct}%, bought more\nnew avg entry: {avg_entry}",
    "averaged down on ${symbol} 👇\n-{down_pct}% from entry, adding {sol_added} SOL\nnew avg: {avg_entry}",
]

EARLY_JEET_TEMPLATES = [
    "sorry i must jeet ${symbol} 🏃\nportfolio is in the red, taking this +{gain_pct}% to recover\n{pnl_sol} SOL",
    "jeeting ${symbol} to recover losses 😬\n+{gain_pct}% | {pnl_sol} SOL\nsorry had to",
    "cutting ${symbol} early 🫡\n+{gain_pct}% | {pnl_sol} SOL\nneed to cover the losses on other trades",
    "taking ${symbol} profit to offset my bags 🩹\n+{gain_pct}% | {pnl_sol} SOL",
]

STATS_FOOTER = "\n\n📊 {open_pos} open | {closed} trades closed"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _total_balance(portfolio: Portfolio, current_prices: dict = None) -> float:
    """
    Free balance + estimated value of all open positions in SOL.
    current_prices: dict of symbol → current_price_usd (optional, from event)
    """
    total = portfolio.balance_sol
    if current_prices:
        from price_fetcher import get_sol_price_usd
        sol_price = get_sol_price_usd()
        for sym, pos in portfolio.positions.items():
            price = current_prices.get(sym, pos.entry_price_usd)
            usd_val = pos.tokens_bought * price
            total += usd_val / sol_price if sol_price > 0 else 0
    else:
        # fallback: assume positions are at entry value
        for sym, pos in portfolio.positions.items():
            total += pos.sol_invested
    return total


# ─── Builder ─────────────────────────────────────────────────────────────────

def _fmt_mult(mult: float) -> str:
    if mult >= 10:
        return f"{mult:.1f}x"
    return f"{mult:.2f}x"


def _fmt_price(price_usd: float) -> str:
    if price_usd < 0.000001:
        return f"${price_usd:.10f}"
    if price_usd < 0.001:
        return f"${price_usd:.8f}"
    if price_usd < 1:
        return f"${price_usd:.6f}"
    return f"${price_usd:.4f}"


def _fmt_mcap(fdv: float) -> str:
    """Format market cap to human-readable string."""
    if fdv <= 0:
        return "unknown"
    if fdv >= 1_000_000_000:
        return f"${fdv/1_000_000_000:.2f}B"
    if fdv >= 1_000_000:
        return f"${fdv/1_000_000:.2f}M"
    if fdv >= 1_000:
        return f"${fdv/1_000:.1f}K"
    return f"${fdv:.0f}"


def build_post(event: dict, portfolio: Portfolio) -> Optional[str]:
    """
    Takes an event dict from strategy.py and returns a social media post string.
    Returns None if event type is unknown.
    """
    etype  = event.get("type")
    symbol = event.get("symbol", "???")
    footer = STATS_FOOTER.format(
        open_pos = len(portfolio.positions),
        closed   = len(portfolio.closed_trades),
    )

    if etype == "buy":
        sol_amount  = event.get("sol_amount", 0)
        fdv         = event.get("stats", {}).get("fdv", 0)
        mcap_str    = _fmt_mcap(fdv)
        overall_bal = _total_balance(portfolio)

        tmpl = random.choice(BUY_TEMPLATES)
        body = tmpl.replace("${symbol}", f"${symbol}")
        ca   = event.get("contract", "")
        body += (
            f"\n\nca: {ca}"
            f"\nentry: {mcap_str} mcap"
            f"\nsize: {sol_amount:.2f} SOL"
            f"\nremaining: {portfolio.balance_sol:.3f} SOL"
            f"\noverall balance: {overall_bal:.3f} SOL"
        )
        return body + footer

    elif etype == "partial_sell":
        mult        = _fmt_mult(event.get("multiplier", 1))
        pct         = int(event.get("pct", 0.5) * 100)
        overall_bal = _total_balance(portfolio)
        tmpl = random.choice(PARTIAL_SELL_TEMPLATES)
        body = (tmpl
                .replace("${symbol}", f"${symbol}")
                .replace("{mult}", mult)
                .replace("{pct}", str(pct)))
        body += f"\n\noverall balance: {overall_bal:.3f} SOL"
        return body + footer

    elif etype == "full_sell":
        mult        = _fmt_mult(event.get("multiplier", 1))
        pnl_sol     = event.get("pnl_sol", 0)
        pnl_str     = f"{pnl_sol:+.3f}"
        overall_bal = _total_balance(portfolio)
        tmpl = random.choice(FULL_TP_TEMPLATES)
        body = (tmpl
                .replace("${symbol}", f"${symbol}")
                .replace("{mult}", mult)
                .replace("{pnl_sol}", pnl_str))
        body += f"\n\noverall balance: {overall_bal:.3f} SOL"
        return body + footer

    elif etype == "stop_loss":
        pnl_sol     = event.get("pnl_sol", 0)
        pnl_str     = f"{pnl_sol:+.3f}"
        overall_bal = _total_balance(portfolio)
        tmpl = random.choice(STOP_LOSS_TEMPLATES)
        body = (tmpl
                .replace("${symbol}", f"${symbol}")
                .replace("{pnl_sol}", pnl_str))
        body += f"\n\noverall balance: {overall_bal:.3f} SOL"
        return body + footer

    elif etype == "stale_sell":
        pnl_sol     = event.get("pnl_sol", 0)
        pnl_str     = f"{pnl_sol:+.3f}"
        overall_bal = _total_balance(portfolio)
        tmpl = random.choice(STALE_SELL_TEMPLATES)
        body = (tmpl
                .replace("${symbol}", f"${symbol}")
                .replace("{pnl_sol}", pnl_str))
        body += f"\n\noverall balance: {overall_bal:.3f} SOL"
        return body + footer

    elif etype == "dca_buy":
        sol_added   = event.get("sol_added", 0)
        avg_entry   = event.get("avg_entry", 0)
        multiplier  = event.get("multiplier", 1.0)
        down_pct    = int(round((1 - multiplier) * 100))
        overall_bal = _total_balance(portfolio)
        avg_entry_str = _fmt_price(avg_entry)
        tmpl = random.choice(DCA_TEMPLATES)
        body = (tmpl
                .replace("${symbol}", f"${symbol}")
                .replace("{down_pct}", str(down_pct))
                .replace("{sol_added}", f"{sol_added:.2f} SOL")
                .replace("{avg_entry}", avg_entry_str))
        body += (
            f"\n\nsize added: {sol_added:.2f} SOL"
            f"\nnew avg entry: {avg_entry_str}"
            f"\noverall balance: {overall_bal:.3f} SOL"
        )
        return body + footer

    elif etype == "early_jeet":
        pct         = event.get("pct", 100)
        pnl_sol     = event.get("pnl_sol", 0)
        pnl_str     = f"{pnl_sol:+.3f}"
        multiplier  = event.get("multiplier", 1.0)
        gain_pct    = int(round((multiplier - 1) * 100))
        overall_bal = _total_balance(portfolio)
        tmpl = random.choice(EARLY_JEET_TEMPLATES)
        body = (tmpl
                .replace("${symbol}", f"${symbol}")
                .replace("{gain_pct}", str(gain_pct))
                .replace("{pnl_sol}", pnl_str)
                .replace("{pct}", str(pct)))
        body += f"\n\noverall balance: {overall_bal:.3f} SOL"
        return body + footer

    return None


def build_daily_summary(portfolio: Portfolio) -> str:
    """Build a daily portfolio update post."""
    lines = [
        "📈 daily portfolio update",
        f"balance: {portfolio.balance_sol:.4f} SOL",
        f"open positions: {len(portfolio.positions)}",
    ]
    if portfolio.positions:
        lines.append("\ncurrent holds:")
        for sym in portfolio.positions:
            lines.append(f"  • ${sym}")

    pnl = portfolio.total_pnl_sol()
    wr  = portfolio.win_rate()
    lines.append(f"\nall-time PnL: {pnl:+.4f} SOL")
    lines.append(f"win rate: {wr:.1f}% ({len(portfolio.closed_trades)} trades)")
    lines.append("\n#Solana #memecoin #papertrading")
    return "\n".join(lines)
