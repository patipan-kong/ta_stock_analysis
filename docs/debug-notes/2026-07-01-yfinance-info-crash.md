Environment
Python 3.13.3
pandas 3.0.4
yfinance 1.5.1
Root cause
Workaround

crash with
print(pd.Timestamp("2026-07-01").floor("D"))
print(pd.Timestamp("2026-07-01").ceil("D"))
print(pd.Timestamp("2026-07-01").round("D"))


Ticker.info crashes because pandas Timestamp.floor()/ceil()/round()
causes Windows access violation (0xC0000005).

Temporary local workaround:
- floor() -> normalize()
- ceil() -> replace(hour=23, minute=59, second=59)