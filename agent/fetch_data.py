import os
import json
import tempfile
import logging
from datetime import datetime, timezone

import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup

from agent.top50_fallback import TOP_50

log = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "dashboard_data.json")

_SLICK_URL = "https://slickcharts.com/sp500"
_SLICK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_spx_history() -> dict:
    """Fetch SPX closing prices, compute 5d/10d MAs, return chart data + callout."""
    raw = yf.download("^GSPC", period="90d", interval="1d", auto_adjust=True, progress=False)
    # yfinance >=0.2.38 returns MultiIndex columns — flatten to single level
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)
    df = pd.DataFrame(index=raw.index)
    df.index = pd.to_datetime(df.index)
    df["close"] = raw["Close"].round(2)
    df = df.dropna(subset=["close"])
    df["ma5"] = df["close"].rolling(5).mean().round(2)
    df["ma10"] = df["close"].rolling(10).mean().round(2)
    df = df.dropna(subset=["ma5", "ma10"]).tail(60)

    chart = [
        {
            "date": idx.strftime("%Y-%m-%d"),
            "close": float(row["close"]),
            "ma5": float(row["ma5"]),
            "ma10": float(row["ma10"]),
        }
        for idx, row in df.iterrows()
    ]

    ma5_today = float(df["ma5"].iloc[-1])
    ma5_yesterday = float(df["ma5"].iloc[-2])
    direction = "higher" if ma5_today > ma5_yesterday else "lower"

    return {
        "chart": chart,
        "callout": {
            "direction": direction,
            "ma5_today": ma5_today,
            "ma5_yesterday": ma5_yesterday,
            "latest_close": float(df["close"].iloc[-1]),
            "ma10_today": float(df["ma10"].iloc[-1]),
        },
    }


def fetch_spx_holdings() -> list:
    """Scrape top-50 SPX holdings from slickcharts.com; fall back to static list."""
    try:
        resp = requests.get(_SLICK_URL, headers=_SLICK_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table")
        if not table:
            raise ValueError("No table found on slickcharts page")

        holdings = []
        for row in table.find("tbody").find_all("tr")[:50]:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) < 4:
                continue
            rank = int(cols[0])
            name = cols[1]
            symbol = cols[2]
            weight = float(cols[3].replace("%", "").replace(",", ""))
            holdings.append({"rank": rank, "name": name, "symbol": symbol, "weight": weight})

        if len(holdings) < 10:
            raise ValueError(f"Only parsed {len(holdings)} rows — page format may have changed")

        log.info("Fetched %d holdings from slickcharts", len(holdings))
        return holdings

    except Exception as exc:
        log.warning("slickcharts fetch failed (%s); using static fallback list", exc)
        return [dict(h) for h in TOP_50]


def fetch_holdings_prices(holdings: list) -> list:
    """Add latest close, yesterday close, and 52-week avg to each holding."""
    symbols = [h["symbol"] for h in holdings]

    raw = yf.download(
        symbols,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
    )

    results = []
    for holding in holdings:
        sym = holding["symbol"]
        try:
            # group_by="ticker" yields MultiIndex (SYMBOL, PRICE_TYPE)
            if isinstance(raw.columns, pd.MultiIndex):
                closes = raw[sym]["Close"].dropna()
            else:
                closes = raw["Close"].dropna()

            price_latest = round(float(closes.iloc[-1]), 2)
            price_yesterday = round(float(closes.iloc[-2]), 2) if len(closes) >= 2 else price_latest
            price_52w_avg = round(float(closes.mean()), 2)
        except Exception as exc:
            log.warning("Price fetch failed for %s: %s", sym, exc)
            price_latest = price_yesterday = price_52w_avg = None

        results.append({
            **holding,
            "price_latest": price_latest,
            "price_yesterday": price_yesterday,
            "price_52w_avg": price_52w_avg,
        })

    return results


def build_dashboard_data() -> dict:
    """Fetch all data and assemble the dashboard JSON."""
    log.info("Fetching SPX history...")
    spx = fetch_spx_history()

    log.info("Fetching SPX holdings...")
    holdings = fetch_spx_holdings()

    log.info("Fetching price data for %d holdings...", len(holdings))
    holdings = fetch_holdings_prices(holdings)

    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "spx": spx,
        "holdings": holdings,
    }


def save_data(data: dict) -> None:
    """Atomically write dashboard data to disk."""
    path = os.path.abspath(DATA_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise
    log.info("Saved dashboard data to %s", path)
