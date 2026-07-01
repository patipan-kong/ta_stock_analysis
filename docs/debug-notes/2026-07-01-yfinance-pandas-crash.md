# Investigation: Analyze All stalled

## Symptoms
- Analyze All stuck at 0/86
- Worker never completed

## Root Cause
yfinance -> Quote.info -> _fetch_complementary()

calls

pd.Timestamp.floor()
pd.Timestamp.ceil()

which causes Windows native access violation (0xC0000005)
under Python 3.13.3.

## Verified

Windows
Python 3.13.3
Fresh venv
Fresh pandas 3.0.4
=> crash

Linux
Python 3.11.9
pandas 3.0.4
=> OK

## Temporary workaround

floor() -> normalize()

ceil() -> replace(hour=23, minute=59, second=59)