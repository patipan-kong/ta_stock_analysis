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