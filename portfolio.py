"""
Portfolio / fake balance manager.
Keeps track of SOL balance and open positions.
Persists state to a JSON file so it survives restarts.
"""

import json
import os
import time
import logging
from typing import Dict, Optional

from config import STARTING_BALANCE_SOL, POSITIONS_FILE

logger = logging.getLogger(__name__)


class Position:
    def __init__(
        self,
        symbol: str,
        contract: str,
        entry_price_usd: float,
        sol_invested: float,
        sol_price_at_entry: float,
        tokens_bought: float,
        timestamp: float,
    ):
        self.symbol           = symbol
        self.contract         = contract
        self.entry_price_usd  = entry_price_usd
        self.sol_invested     = sol_invested
        self.sol_price_at_entry = sol_price_at_entry
        self.tokens_bought    = tokens_bought
        self.timestamp        = timestamp
        self.partial_sold     = False   # True after first partial take-profit
        self.highest_mult     = 1.0     # track ATH multiplier for the post
        self.next_tp_index    = 0       # which take-profit level we're watching
        self.dca_done         = False   # True after DCA buy executed
        self.original_sol_invested = sol_invested  # for DCA sizing
        self.early_jeet_done  = False   # True after early jeet executed (once per position)

    def current_multiplier(self, current_price_usd: float) -> float:
        if self.entry_price_usd == 0:
            return 1.0
        return current_price_usd / self.entry_price_usd

    def pnl_sol(self, current_price_usd: float, sol_price_usd: float) -> float:
        current_value_usd = self.tokens_bought * current_price_usd
        invested_usd      = self.sol_invested * self.sol_price_at_entry
        return (current_value_usd - invested_usd) / sol_price_usd

    def to_dict(self) -> dict:
        return {
            "symbol":                  self.symbol,
            "contract":                self.contract,
            "entry_price_usd":         self.entry_price_usd,
            "sol_invested":            self.sol_invested,
            "sol_price_at_entry":      self.sol_price_at_entry,
            "tokens_bought":           self.tokens_bought,
            "timestamp":               self.timestamp,
            "partial_sold":            self.partial_sold,
            "highest_mult":            self.highest_mult,
            "next_tp_index":           self.next_tp_index,
            "dca_done":                self.dca_done,
            "original_sol_invested":   self.original_sol_invested,
            "early_jeet_done":         self.early_jeet_done,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Position":
        p = cls(
            symbol            = d["symbol"],
            contract          = d["contract"],
            entry_price_usd   = d["entry_price_usd"],
            sol_invested      = d["sol_invested"],
            sol_price_at_entry= d["sol_price_at_entry"],
            tokens_bought     = d["tokens_bought"],
            timestamp         = d["timestamp"],
        )
        p.partial_sold           = d.get("partial_sold", False)
        p.highest_mult           = d.get("highest_mult", 1.0)
        p.next_tp_index          = d.get("next_tp_index", 0)
        p.dca_done               = d.get("dca_done", False)
        p.original_sol_invested  = d.get("original_sol_invested", p.sol_invested)
        p.early_jeet_done        = d.get("early_jeet_done", False)
        return p


class Portfolio:
    def __init__(self):
        self.balance_sol: float = STARTING_BALANCE_SOL
        self.positions: Dict[str, Position] = {}  # keyed by symbol
        self.closed_trades: list = []
        self._load()

    # ─── Persistence ─────────────────────────────────────────────────────────
    def _load(self):
        if not os.path.exists(POSITIONS_FILE):
            return
        try:
            with open(POSITIONS_FILE, "r") as f:
                data = json.load(f)
            self.balance_sol    = data.get("balance_sol", STARTING_BALANCE_SOL)
            self.positions      = {
                sym: Position.from_dict(pos)
                for sym, pos in data.get("positions", {}).items()
            }
            self.closed_trades  = data.get("closed_trades", [])
            logger.info(f"Portfolio loaded – balance: {self.balance_sol:.4f} SOL, "
                        f"open positions: {list(self.positions.keys())}")
        except Exception as e:
            logger.warning(f"Could not load portfolio: {e}")

    def save(self):
        data = {
            "balance_sol":   self.balance_sol,
            "positions":     {sym: p.to_dict() for sym, p in self.positions.items()},
            "closed_trades": self.closed_trades,
        }
        with open(POSITIONS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    # ─── Trading Actions ─────────────────────────────────────────────────────
    def buy(
        self,
        symbol: str,
        contract: str,
        token_price_usd: float,
        sol_price_usd: float,
        sol_amount: float,
    ) -> Optional[Position]:
        if symbol in self.positions:
            logger.info(f"Already holding {symbol}, skipping buy")
            return None
        if self.balance_sol < sol_amount:
            logger.info(f"Not enough balance to buy {symbol}")
            return None

        usd_to_spend  = sol_amount * sol_price_usd
        tokens_bought = usd_to_spend / token_price_usd

        self.balance_sol -= sol_amount
        pos = Position(
            symbol            = symbol,
            contract          = contract,
            entry_price_usd   = token_price_usd,
            sol_invested      = sol_amount,
            sol_price_at_entry= sol_price_usd,
            tokens_bought     = tokens_bought,
            timestamp         = time.time(),
        )
        self.positions[symbol] = pos
        self.save()
        logger.info(f"BUY {symbol}: {tokens_bought:.2f} tokens @ ${token_price_usd:.8f}")
        return pos

    def dca_buy(
        self,
        symbol: str,
        token_price_usd: float,
        sol_price_usd: float,
    ) -> Optional[dict]:
        """
        Dollar-cost-average into an existing position.
        Buys half of the original position size, updates average entry price.
        """
        pos = self.positions.get(symbol)
        if not pos:
            return None
        if pos.dca_done:
            return None  # max 1 DCA per position

        sol_amount = pos.original_sol_invested * 0.5
        if self.balance_sol < sol_amount:
            sol_amount = self.balance_sol * 0.5  # use whatever is available
        if sol_amount < 0.05:
            return None  # too small to bother

        usd_to_spend    = sol_amount * sol_price_usd
        new_tokens      = usd_to_spend / token_price_usd

        # Update average entry price
        total_tokens    = pos.tokens_bought + new_tokens
        total_invested  = pos.sol_invested + sol_amount
        avg_price       = (pos.sol_invested * pos.sol_price_at_entry + sol_amount * sol_price_usd) / total_invested

        pos.tokens_bought    = total_tokens
        pos.sol_invested     = total_invested
        pos.sol_price_at_entry = avg_price / sol_price_usd * sol_price_usd  # keep in usd terms
        # Recalculate effective entry price in USD
        pos.entry_price_usd  = (pos.entry_price_usd * (total_tokens - new_tokens) + token_price_usd * new_tokens) / total_tokens
        pos.dca_done         = True
        self.balance_sol    -= sol_amount
        self.save()

        logger.info(f"DCA {symbol}: +{new_tokens:.2f} tokens @ ${token_price_usd:.8f} | new avg: ${pos.entry_price_usd:.8f}")
        return {
            "symbol":       symbol,
            "sol_added":    sol_amount,
            "new_tokens":   new_tokens,
            "avg_entry":    pos.entry_price_usd,
        }

    def partial_sell(
        self,
        symbol: str,
        current_price_usd: float,
        sol_price_usd: float,
        pct: float = 0.5,
    ) -> Optional[dict]:
        pos = self.positions.get(symbol)
        if not pos:
            return None

        tokens_to_sell = pos.tokens_bought * pct
        usd_received   = tokens_to_sell * current_price_usd
        sol_received   = usd_received / sol_price_usd

        pos.tokens_bought -= tokens_to_sell
        pos.partial_sold   = True
        pos.sol_invested  *= (1 - pct)   # reduce cost basis proportionally
        self.balance_sol  += sol_received
        self.save()

        mult = pos.current_multiplier(current_price_usd)
        logger.info(f"PARTIAL SELL {symbol}: {pct*100:.0f}% @ {mult:.2f}x | +{sol_received:.4f} SOL")
        return {"symbol": symbol, "pct": pct, "multiplier": mult, "sol_received": sol_received}

    def full_sell(
        self,
        symbol: str,
        current_price_usd: float,
        sol_price_usd: float,
        reason: str = "TP",
    ) -> Optional[dict]:
        pos = self.positions.get(symbol)
        if not pos:
            return None

        usd_received  = pos.tokens_bought * current_price_usd
        sol_received  = usd_received / sol_price_usd
        self.balance_sol += sol_received

        mult = pos.current_multiplier(current_price_usd)
        pnl_sol = sol_received - pos.sol_invested

        record = {
            "symbol":       symbol,
            "entry_price":  pos.entry_price_usd,
            "exit_price":   current_price_usd,
            "multiplier":   mult,
            "pnl_sol":      pnl_sol,
            "sol_received": sol_received,
            "reason":       reason,
            "timestamp":    time.time(),
        }
        self.closed_trades.append(record)
        del self.positions[symbol]
        self.save()

        logger.info(f"FULL SELL {symbol}: {mult:.2f}x | reason={reason} | pnl={pnl_sol:+.4f} SOL")
        return record

    # ─── Stats ───────────────────────────────────────────────────────────────
    def total_pnl_sol(self, current_prices: dict = None) -> float:
        """
        Total PnL: closed trades + unrealized open positions.
        current_prices: dict of symbol → current_price_usd (optional).
        If not provided, assumes open positions are at entry (0 unrealized).
        """
        closed_pnl = sum(t["pnl_sol"] for t in self.closed_trades)
        if not current_prices:
            return closed_pnl
        # add unrealized
        unrealized = 0.0
        from price_fetcher import get_sol_price_usd
        sol_price = get_sol_price_usd()
        for sym, pos in self.positions.items():
            price = current_prices.get(sym, pos.entry_price_usd)
            unrealized += pos.pnl_sol(price, sol_price)
        return closed_pnl + unrealized

    def win_rate(self) -> float:
        if not self.closed_trades:
            return 0.0
        wins = sum(1 for t in self.closed_trades if t["pnl_sol"] > 0)
        return wins / len(self.closed_trades) * 100

    def summary(self) -> str:
        trades = len(self.closed_trades)
        pnl    = self.total_pnl_sol()
        wr     = self.win_rate()
        return (f"Balance: {self.balance_sol:.4f} SOL | "
                f"Open: {len(self.positions)} | "
                f"Closed: {trades} | "
                f"PnL: {pnl:+.4f} SOL | "
                f"Win rate: {wr:.1f}%")
