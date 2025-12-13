"""FRED (Federal Reserve Economic Data) API 연동 서비스.

유동성 지표 데이터를 FRED에서 조회하고 캐싱합니다.

핵심 지표:
- WALCL: Federal Reserve Total Assets (연준 총자산)
- WDTGAL: Treasury General Account (재무부 일반계정, TGA)
- RRPONTSYD: Overnight Reverse Repurchase Agreements (역레포, RRP)
- SP500: S&P 500 Index

순유동성 공식:
Net Liquidity = WALCL - (WDTGAL + RRPONTSYD)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서)
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)


class LiquidityData(TypedDict):
    """유동성 데이터 구조."""

    fed_assets: float  # WALCL (조 달러)
    fed_assets_str: str
    tga_balance: float  # WDTGAL (조 달러)
    tga_balance_str: str
    rrp_balance: float  # RRPONTSYD (조 달러)
    rrp_balance_str: str
    net_liquidity: float  # 순유동성 (조 달러)
    net_liquidity_str: str
    sp500: float
    sp500_str: str
    # 변화율 (전주 대비)
    fed_assets_change: float
    tga_change: float
    rrp_change: float
    net_liquidity_change: float
    sp500_change: float


class LiquidityHistoryPoint(TypedDict):
    """시계열 데이터 포인트."""

    date: str  # YYYY-MM-DD
    fed_assets: float
    tga_balance: float
    rrp_balance: float
    net_liquidity: float
    sp500: float


@dataclass(frozen=True)
class _LiquidityCache:
    fetched_at_epoch: float
    data: LiquidityData
    history: list[LiquidityHistoryPoint]
    last_updated: str


_LIQUIDITY_CACHE: _LiquidityCache | None = None

# FRED API 키 (환경변수에서 로드)
# 무료 API 키: https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")


def _fmt_compact(value: float, decimals: int = 2) -> str:
    """큰 숫자를 T/B/M 형식으로 포맷팅."""
    abs_v = abs(value)
    if abs_v >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.{decimals}f}T"
    if abs_v >= 1_000_000_000:
        return f"${value / 1_000_000_000:.{decimals}f}B"
    if abs_v >= 1_000_000:
        return f"${value / 1_000_000:.{decimals}f}M"
    return f"${value:,.0f}"


def _fmt_pct(value: float, decimals: int = 2) -> str:
    """백분율 포맷팅."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def _fetch_fred_series(
    series_id: str,
    *,
    start_date: str = "2000-01-01",
    api_key: str = "",
) -> pd.DataFrame:
    """FRED에서 시계열 데이터를 조회합니다.

    Args:
        series_id: FRED 시리즈 ID (예: WALCL, WDTGAL)
        start_date: 조회 시작일 (YYYY-MM-DD)
        api_key: FRED API 키

    Returns:
        DataFrame with 'date' and 'value' columns
    """
    if not api_key:
        raise ValueError("FRED_API_KEY 환경변수를 설정해주세요.")

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
        "sort_order": "asc",
    }

    response = httpx.get(url, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()
    observations = data.get("observations", [])

    records = []
    for obs in observations:
        date_str = obs.get("date")
        value_str = obs.get("value")
        # FRED는 결측치를 "."로 표시
        if value_str and value_str != ".":
            records.append({"date": date_str, "value": float(value_str)})

    df = pd.DataFrame(records)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def _merge_series(
    walcl: pd.DataFrame,
    wdtgal: pd.DataFrame,
    rrpontsyd: pd.DataFrame,
    sp500: pd.DataFrame,
) -> pd.DataFrame:
    """여러 시계열을 날짜 기준으로 병합합니다.

    FRED 데이터는 주간(WALCL, WDTGAL) 또는 일간(RRPONTSYD, SP500)으로 업데이트되므로
    forward fill을 적용하여 결측치를 채웁니다.
    """
    # 각 시리즈에 고유 컬럼명 부여
    walcl = walcl.rename(columns={"value": "fed_assets"}).set_index("date")
    wdtgal = wdtgal.rename(columns={"value": "tga_balance"}).set_index("date")
    rrpontsyd = rrpontsyd.rename(columns={"value": "rrp_balance"}).set_index("date")
    sp500 = sp500.rename(columns={"value": "sp500"}).set_index("date")

    # 병합 (outer join으로 모든 날짜 포함)
    merged = pd.concat([walcl, wdtgal, rrpontsyd, sp500], axis=1)

    # Forward fill로 결측치 채우기 (주간 데이터 → 일간으로 확장)
    merged = merged.ffill()

    # 모든 값이 있는 행만 유지
    merged = merged.dropna()

    # Net Liquidity 계산: WALCL - (WDTGAL + RRPONTSYD)
    # 단위: WALCL/WDTGAL는 백만 달러, RRPONTSYD는 십억 달러
    # 통일을 위해 모두 백만 달러로 변환
    merged["rrp_balance_millions"] = merged["rrp_balance"] * 1000  # 십억 → 백만
    merged["net_liquidity"] = (
        merged["fed_assets"] - merged["tga_balance"] - merged["rrp_balance_millions"]
    )

    merged = merged.reset_index()
    return merged


def get_liquidity_data(
    *,
    ttl_seconds: int = 3600,
    api_key: str | None = None,
) -> tuple[LiquidityData, list[LiquidityHistoryPoint], str, bool]:
    """유동성 데이터를 조회합니다 (캐싱 적용).

    Args:
        ttl_seconds: 캐시 TTL (기본 1시간, FRED 데이터는 일별 업데이트)
        api_key: FRED API 키 (None이면 환경변수 사용)

    Returns:
        (current_data, history, last_updated_str, is_cached)
    """
    global _LIQUIDITY_CACHE

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    now_epoch = now.timestamp()

    # 캐시 확인
    if _LIQUIDITY_CACHE is not None and (now_epoch - _LIQUIDITY_CACHE.fetched_at_epoch) < ttl_seconds:
        return (
            _LIQUIDITY_CACHE.data,
            _LIQUIDITY_CACHE.history,
            _LIQUIDITY_CACHE.last_updated,
            True,
        )

    key = api_key or FRED_API_KEY
    if not key:
        raise ValueError(
            "FRED_API_KEY 환경변수를 설정해주세요. "
            "무료 API 키 발급: https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    # FRED에서 데이터 조회
    walcl = _fetch_fred_series("WALCL", api_key=key)  # 연준 총자산 (백만 달러)
    wdtgal = _fetch_fred_series("WDTGAL", api_key=key)  # TGA (백만 달러)
    rrpontsyd = _fetch_fred_series("RRPONTSYD", api_key=key)  # 역레포 (십억 달러)
    sp500 = _fetch_fred_series("SP500", api_key=key)  # S&P 500

    # 시계열 병합
    merged = _merge_series(walcl, wdtgal, rrpontsyd, sp500)

    if merged.empty:
        raise ValueError("FRED 데이터를 병합할 수 없습니다.")

    # 최신 데이터 추출
    latest = merged.iloc[-1]
    prev_week = merged.iloc[-6] if len(merged) > 5 else merged.iloc[0]

    # 단위 변환: 백만 달러 → 실제 달러
    fed_assets = float(latest["fed_assets"]) * 1_000_000
    tga_balance = float(latest["tga_balance"]) * 1_000_000
    rrp_balance = float(latest["rrp_balance"]) * 1_000_000_000  # 십억 → 달러
    net_liquidity = float(latest["net_liquidity"]) * 1_000_000
    sp500_val = float(latest["sp500"])

    # 전주 대비 변화율
    prev_fed = float(prev_week["fed_assets"]) * 1_000_000
    prev_tga = float(prev_week["tga_balance"]) * 1_000_000
    prev_rrp = float(prev_week["rrp_balance"]) * 1_000_000_000
    prev_net = float(prev_week["net_liquidity"]) * 1_000_000
    prev_sp = float(prev_week["sp500"])

    def _calc_change(curr: float, prev: float) -> float:
        if prev == 0:
            return 0.0
        return ((curr - prev) / abs(prev)) * 100

    current_data: LiquidityData = {
        "fed_assets": fed_assets,
        "fed_assets_str": _fmt_compact(fed_assets),
        "tga_balance": tga_balance,
        "tga_balance_str": _fmt_compact(tga_balance),
        "rrp_balance": rrp_balance,
        "rrp_balance_str": _fmt_compact(rrp_balance),
        "net_liquidity": net_liquidity,
        "net_liquidity_str": _fmt_compact(net_liquidity),
        "sp500": sp500_val,
        "sp500_str": f"{sp500_val:,.2f}",
        "fed_assets_change": _calc_change(fed_assets, prev_fed),
        "tga_change": _calc_change(tga_balance, prev_tga),
        "rrp_change": _calc_change(rrp_balance, prev_rrp),
        "net_liquidity_change": _calc_change(net_liquidity, prev_net),
        "sp500_change": _calc_change(sp500_val, prev_sp),
    }

    # 시계열 히스토리 (차트용)
    history: list[LiquidityHistoryPoint] = []
    for _, row in merged.iterrows():
        history.append(
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "fed_assets": float(row["fed_assets"]) * 1_000_000,
                "tga_balance": float(row["tga_balance"]) * 1_000_000,
                "rrp_balance": float(row["rrp_balance"]) * 1_000_000_000,
                "net_liquidity": float(row["net_liquidity"]) * 1_000_000,
                "sp500": float(row["sp500"]),
            }
        )

    last_updated = now.strftime("%Y-%m-%d %H:%M KST")

    _LIQUIDITY_CACHE = _LiquidityCache(
        fetched_at_epoch=now_epoch,
        data=current_data,
        history=history,
        last_updated=last_updated,
    )

    return current_data, history, last_updated, False


def fmt_pct(value: float) -> str:
    """백분율 포맷팅 (UI용 export)."""
    return _fmt_pct(value)
