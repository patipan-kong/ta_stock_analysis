import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yfinance as yf

print(yf.__version__)

t = yf.Ticker("AAPL")

print("fast_info")
print(t.fast_info)

print("history")
print(t.history(period="5d"))

print("ticker")
print(t)
print("quote")
q = t._quote
print(q)
print("q.info")
print(q.info)
print("info end")