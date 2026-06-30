from yfinance.scrapers.history import PriceHistory

old = PriceHistory.history

def debug_history(self, *a, **kw):
    print("ENTER")
    df = old(self, *a, **kw)
    print("EXIT")
    return df

PriceHistory.history = debug_history