"""
Price fetcher – uses DexScreener API (free, no key required)
to get real-time prices for Solana tokens.
Falls back to CoinGecko for SOL/USD.
Also includes a live scanner for trending Solana memecoins.
"""

import requests
import logging
import time
from typing import Optional, List, Dict

from config import DEXSCREENER_URL, SOL_PRICE_URL

logger = logging.getLogger(__name__)

# Simple in-memory cache to avoid hammering the API
_price_cache: dict = {}
_cache_ttl = 300  # seconds (5 min — avoid CoinGecko rate limits)


def _cached(key: str) -> Optional[float]:
    entry = _price_cache.get(key)
    if entry and time.time() - entry["ts"] < _cache_ttl:
        return entry["value"]
    return None


def _store(key: str, value: float):
    _price_cache[key] = {"value": value, "ts": time.time()}


def get_sol_price_usd() -> float:
    """Fetch current SOL price in USD from CoinGecko."""
    cached = _cached("SOL")
    if cached:
        return cached
    try:
        r = requests.get(SOL_PRICE_URL, timeout=10)
        r.raise_for_status()
        price = r.json()["solana"]["usd"]
        _store("SOL", price)
        return price
    except Exception as e:
        logger.error(f"Failed to fetch SOL price: {e}")
        return _price_cache.get("SOL", {}).get("value", 85.0)  # fallback to last known


def get_token_data(contract_address: str) -> Optional[dict]:
    """
    Fetch token data from DexScreener.
    Returns the best (highest liquidity) pair dict or None.
    """
    try:
        url = f"{DEXSCREENER_URL}{contract_address}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        pairs = r.json().get("pairs", [])

        if not pairs:
            return None

        sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
        if not sol_pairs:
            sol_pairs = pairs

        best = max(sol_pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
        return best

    except Exception as e:
        logger.error(f"DexScreener error for {contract_address}: {e}")
        return None


def get_token_price_usd(contract_address: str) -> Optional[float]:
    data = get_token_data(contract_address)
    if not data:
        return None
    try:
        return float(data["priceUsd"])
    except Exception:
        return None


def get_token_stats(contract_address: str) -> Optional[dict]:
    data = get_token_data(contract_address)
    if not data:
        return None
    try:
        return {
            "price_usd":        float(data.get("priceUsd", 0)),
            "volume_24h":       float(data.get("volume", {}).get("h24", 0) or 0),
            "liquidity_usd":    float(data.get("liquidity", {}).get("usd", 0) or 0),
            "price_change_1h":  float(data.get("priceChange", {}).get("h1", 0) or 0),
            "price_change_6h":  float(data.get("priceChange", {}).get("h6", 0) or 0),
            "price_change_24h": float(data.get("priceChange", {}).get("h24", 0) or 0),
            "fdv":              float(data.get("fdv", 0) or 0),
            "pair_address":     data.get("pairAddress", ""),
            "dex":              data.get("dexId", ""),
            "symbol":           data.get("baseToken", {}).get("symbol", ""),
            "name":             data.get("baseToken", {}).get("name", ""),
            "contract":         data.get("baseToken", {}).get("address", contract_address),
        }
    except Exception as e:
        logger.error(f"Stats parse error: {e}")
        return None


def scan_trending_solana_tokens(min_volume: float = 50_000,
                                 min_liquidity: float = 30_000,
                                 limit: int = 40) -> List[Dict]:
    """
    Pulls trending Solana token pairs from DexScreener using multiple endpoints.
    Returns a list of stats dicts ready for strategy evaluation.
    """
    raw_pairs = []  # list of raw DexScreener pair dicts

    # ── Endpoint 1: boosted tokens (addresses only → fetch stats separately) ─
    boosted_addrs = []
    try:
        r = requests.get("https://api.dexscreener.com/token-boosts/latest/v1", timeout=10)
        r.raise_for_status()
        boosted = r.json()
        if isinstance(boosted, list):
            for item in boosted:
                if item.get("chainId") == "solana":
                    addr = item.get("tokenAddress", "")
                    if addr:
                        boosted_addrs.append(addr)
    except Exception as e:
        logger.warning(f"Boosted tokens fetch failed: {e}")

    # ── Endpoint 2: top Solana pairs directly (has full pair data) ───────────
    for query in ["memecoin", "meme", "pump", "cat", "dog", "pepe", "raydium", "ai", "trump", "gork"]:
        try:
            r = requests.get(
                f"https://api.dexscreener.com/latest/dex/search?q={query}",
                timeout=10
            )
            r.raise_for_status()
            data = r.json().get("pairs", [])
            for p in data:
                if p.get("chainId") == "solana":
                    raw_pairs.append(p)
        except Exception as e:
            logger.warning(f"DexScreener search ({query}) failed: {e}")

    # ── Endpoint 3: token profiles ────────────────────────────────────────────
    try:
        r = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=10)
        r.raise_for_status()
        profiles = r.json()
        if isinstance(profiles, list):
            for item in profiles:
                if item.get("chainId") == "solana":
                    addr = item.get("tokenAddress", "")
                    if addr and addr not in boosted_addrs:
                        boosted_addrs.append(addr)
    except Exception as e:
        logger.warning(f"Token profiles fetch failed: {e}")

    # ── Fetch boosted/profile addresses in batch ──────────────────────────────
    for addr in boosted_addrs[:30]:
        try:
            data = get_token_data(addr)
            if data and data.get("chainId") == "solana":
                raw_pairs.append(data)
            time.sleep(0.1)
        except Exception:
            pass

    logger.info(f"Found {len(raw_pairs)} raw Solana pairs to evaluate")

    # ── Parse + filter ────────────────────────────────────────────────────────
    results = []
    seen_symbols = set()
    seen_contracts = set()

    for p in raw_pairs:
        try:
            sym      = p.get("baseToken", {}).get("symbol", "").upper()
            contract = p.get("baseToken", {}).get("address", "")
            if not sym or not contract:
                continue
            if sym in seen_symbols or contract in seen_contracts:
                continue
            if sym in ("USDC", "USDT", "SOL", "WSOL", "WBTC", "WETH", "RAY", "BONK"):
                continue

            vol   = float(p.get("volume", {}).get("h24", 0) or 0)
            liq   = float(p.get("liquidity", {}).get("usd", 0) or 0)
            fdv   = float(p.get("fdv", 0) or 0)
            price = float(p.get("priceUsd", 0) or 0)
            ch1h  = float(p.get("priceChange", {}).get("h1", 0) or 0)
            ch6h  = float(p.get("priceChange", {}).get("h6", 0) or 0)
            ch24h = float(p.get("priceChange", {}).get("h24", 0) or 0)

            if vol < min_volume or liq < min_liquidity or price <= 0:
                continue

            seen_symbols.add(sym)
            seen_contracts.add(contract)
            results.append({
                "symbol":           sym,
                "contract":         contract,
                "price_usd":        price,
                "volume_24h":       vol,
                "liquidity_usd":    liq,
                "fdv":              fdv,
                "price_change_1h":  ch1h,
                "price_change_6h":  ch6h,
                "price_change_24h": ch24h,
            })
        except Exception as e:
            logger.debug(f"Parse error: {e}")

    logger.info(f"Qualified tokens after filtering: {len(results)}")
    return results[:limit]

