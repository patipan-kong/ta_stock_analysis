import re
import traceback
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

# DR (Depository Receipt) symbols traded on the Thai SET: letters + 2 digits + .BK
# e.g. AAPL01.BK, AMD08.BK, MSFT12.BK → base US ticker: AAPL, AMD, MSFT
_DR_RE = re.compile(r'^([A-Z]+)\d{2}\.BK$')

def normalize_dr_symbol(symbol: str) -> str:
    """Strip the DR digit-suffix so yfinance can find the underlying US company.

    AAPL01.BK → 'AAPL'   (DR → base ticker)
    PTT.BK    → 'PTT.BK' (unchanged — regular Thai stock)
    AAPL      → 'AAPL'   (unchanged — already a US ticker)
    """
    m = _DR_RE.match(symbol)
    return m.group(1) if m else symbol


def resolve_symbol(symbol: str) -> str:
    """Append .BK for Thai stocks if not already present and not a US ticker."""
    symbol = symbol.upper()
    if symbol.endswith(".BK"):
        return symbol
    # Heuristic: Thai SET symbols are 1-5 uppercase letters without digits (mostly)
    # Frontend sends symbols without .BK; we rely on caller to pass the flag
    return symbol


def fetch_history(symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def fetch_info(symbol: str) -> dict:
    """Fetch yfinance .info for a symbol.
    Callers are responsible for normalising DR symbols via normalize_dr_symbol() first."""
    try:
        ticker = yf.Ticker(symbol)
        return ticker.info or {}
    except Exception:
        return {}


def fetch_price_info(symbol: str) -> dict:
    try:
        # ลองส่องดูว่า symbol ที่ส่งเข้ามาหน้าตาเป็นยังไง มี .BK ไหม
        # print(f"Fetching price for: {symbol}") 
        
        fi = yf.Ticker(symbol).fast_info
        current_price: float | None = fi.last_price
        prev_close: float | None = fi.previous_close
        change_percent: float | None = None
        if current_price is not None and prev_close and prev_close != 0:
            change_percent = round((current_price - prev_close) / prev_close * 100, 2)
        return {
            "current_price": round(current_price, 4) if current_price is not None else None,
            "change_percent": change_percent,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        # 🚨 จุดสำคัญ: พ่น Error ตัวจริงออกมาดูใน pm2 logs
        print(f"❌ Error fetching price for {symbol}: {str(e)}")
        traceback.print_exc() 
        return {"current_price": None, "change_percent": None, "last_updated": None}


def fetch_news(symbol: str) -> list[dict]:
    """Callers are responsible for normalising DR symbols via normalize_dr_symbol() first."""
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news or []
        result = []
        for item in news[:10]:
            content = item.get("content", {})
            result.append({
                "title": content.get("title", ""),
                "publisher": content.get("provider", {}).get("displayName", "") if isinstance(content.get("provider"), dict) else "",
                "link": content.get("canonicalUrl", {}).get("url", "") if isinstance(content.get("canonicalUrl"), dict) else "",
                "published": content.get("pubDate", ""),
            })
        return result
    except Exception:
        return []
