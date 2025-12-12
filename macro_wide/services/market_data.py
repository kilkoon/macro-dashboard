"""Market data providers (free, no API key).

Design goals:
- Provider isolation: easy to swap data sources later.
- Caching: avoid rate-limits and keep Reflex Cloud usage reasonable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, TypedDict

import httpx


class Indicator(TypedDict):
    name: str
    value: str
    change: str
    is_positive: bool
    source: str


@dataclass(frozen=True)
class _Cache:
    fetched_at_epoch: float
    indicators: list[Indicator]
    last_updated: str


_CACHE: _Cache | None = None


def _fmt_number(x: float, decimals: int = 2) -> str:
    return f"{x:,.{decimals}f}"


def _fmt_pct(x: float, decimals: int = 2) -> str:
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.{decimals}f}%"


def _fetch_effr() -> tuple[float, str]:
    """Fetch NY Fed Effective Federal Funds Rate (EFFR).

    Returns:
        (rate_percent, effective_date_yyyy_mm_dd)
    """
    url = "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/1.json"
    r = httpx.get(url, timeout=10)
    r.raise_for_status()
    payload = r.json()
    rate = float(payload["refRates"][0]["percentRate"])
    effective_date = str(payload["refRates"][0]["effectiveDate"])
    return rate, effective_date


def _fetch_yfinance_quotes(symbols: list[str]) -> dict[str, dict[str, float]]:
    """Fetch last close and previous close for each symbol via yfinance.

    Returns:
        {symbol: {"last": float, "prev": float}}
    """
    # Import yfinance lazily so this module stays lightweight and easy to replace.
    import pandas as pd  # type: ignore
    import yfinance as yf  # type: ignore

    if not symbols:
        return {}

    # NOTE:
    # - Windows 환경에서 yfinance가 내부적으로 사용하는 sqlite 캐시가 간헐적으로 잠기는 케이스가 있어
    #   threads를 끄고(단일 스레드) 다운로드를 수행합니다.
    df = yf.download(
        tickers=" ".join(symbols),
        period="10d",  # include enough days to survive weekends/holidays
        interval="1d",
        progress=False,
        group_by="column",
        auto_adjust=False,
        threads=False,
    )

    out: dict[str, dict[str, float]] = {}

    if isinstance(df.columns, pd.MultiIndex):
        # columns: ('Close', 'SYMBOL') etc.
        closes = df["Close"]
        for sym in symbols:
            series = closes[sym].dropna()
            if len(series) < 2:
                continue
            out[sym] = {"last": float(series.iloc[-1]), "prev": float(series.iloc[-2])}
        return out

    # Single symbol case (no MultiIndex)
    close = df["Close"].dropna()
    if len(close) >= 2:
        out[symbols[0]] = {"last": float(close.iloc[-1]), "prev": float(close.iloc[-2])}
    return out


def get_indicators(*, ttl_seconds: int = 300) -> tuple[list[Indicator], str, bool]:
    """Get indicators with a simple in-memory TTL cache.

    Args:
        ttl_seconds: Cache TTL. Default 300s = 5 minutes.

    Returns:
        (indicators, last_updated_str, is_cached)
    """
    global _CACHE

    # NOTE: Reflex Cloud 런타임은 UTC로 동작하는 경우가 많아,
    # 사용자에게 익숙한 KST(Asia/Seoul)로 Updated 시간을 고정 표시합니다.
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    now_epoch = now.timestamp()

    if _CACHE is not None and (now_epoch - _CACHE.fetched_at_epoch) < ttl_seconds:
        return _CACHE.indicators, _CACHE.last_updated, True

    # Define the set in one place to make future provider swaps easy.
    y_symbols = {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "USD/KRW": "KRW=X",
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD",
        "XRP": "XRP-USD",
    }

    quotes = _fetch_yfinance_quotes(list(y_symbols.values()))
    effr_rate, effr_date = _fetch_effr()

    def _mk_from_quote(name: str, sym: str, *, decimals: int, prefix: str = "") -> Indicator:
        q = quotes.get(sym)
        if not q:
            return {
                "name": name,
                "value": "—",
                "change": "—",
                "is_positive": True,
                "source": "yfinance",
            }
        last = q["last"]
        prev = q["prev"]
        pct = ((last - prev) / prev) * 100.0 if prev else 0.0
        return {
            "name": name,
            "value": f"{prefix}{_fmt_number(last, decimals=decimals)}",
            "change": _fmt_pct(pct, decimals=2),
            "is_positive": pct >= 0,
            "source": "yfinance",
        }

    indicators: list[Indicator] = [
        _mk_from_quote("KOSPI", y_symbols["KOSPI"], decimals=2),
        _mk_from_quote("KOSDAQ", y_symbols["KOSDAQ"], decimals=2),
        _mk_from_quote("S&P 500", y_symbols["S&P 500"], decimals=2),
        _mk_from_quote("NASDAQ", y_symbols["NASDAQ"], decimals=2),
        _mk_from_quote("USD/KRW", y_symbols["USD/KRW"], decimals=2),
        _mk_from_quote("Bitcoin", y_symbols["Bitcoin"], decimals=2, prefix="$"),
        _mk_from_quote("Ethereum", y_symbols["Ethereum"], decimals=2, prefix="$"),
        _mk_from_quote("XRP", y_symbols["XRP"], decimals=4, prefix="$"),
        {
            "name": "미국 기준금리 (EFFR)",
            "value": f"{effr_rate:.2f}%",
            "change": effr_date,
            "is_positive": True,
            "source": "nyfed",
        },
    ]

    last_updated = now.strftime("%Y-%m-%d %H:%M KST")
    _CACHE = _Cache(
        fetched_at_epoch=now_epoch,
        indicators=indicators,
        last_updated=last_updated,
    )
    return indicators, last_updated, False


