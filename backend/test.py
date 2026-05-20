import yfinance as yf
info = yf.Ticker("PIS.BK").info
print(info.get("sector"))      # อาจได้ None หรือ ""
print(info.get("industry"))    # ลองดูตัวนี้แทน

from services.data_fetcher import normalize_dr_symbol
import yfinance as yf

def _get_sector(symbol: str, fa_cache: dict | None) -> str:
    """Resolve sector with three-way branching:
    1. DR stocks (e.g. AAPL01.BK) — FA cache has base-company data fetched via normalize_dr_symbol
    2. Regular Thai stocks (.BK)   — THAI_SECTOR_MAP first, FA cache as fallback
    3. US stocks                   — FA cache (yfinance sector field)
    """
    def _from_cache() -> str | None:
        if fa_cache:
            s = fa_cache.get("sector")
            if s and s not in ("N/A", "Other", ""):
                return s
        return None

    base = normalize_dr_symbol(symbol)
    if base != symbol:
        # DR stock: fundamental data comes from base US ticker, so FA cache already has US sector
        return _from_cache() or "Other"

    if symbol.endswith(".BK"):
        # Regular Thai stock: static map is more reliable than yfinance .BK sector data
        mapped = THAI_SECTOR_MAP.get(symbol)
        if mapped:
            return mapped
        return _from_cache() or "Other"

    # US stock: use FA cache (yfinance sector)
    return _from_cache() or "Other"

symbol = 'AAPL01.BK'
normalized = normalize_dr_symbol(symbol)
print('normalized:', normalized)

info = yf.Ticker(normalized).info
print('sector:', info.get('sector'))
