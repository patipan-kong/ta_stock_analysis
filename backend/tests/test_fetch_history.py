import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import pandas_ta as ta
from services.data_fetcher import fetch_history


df = fetch_history("GOOGL01.BK", "5y", "1d")

print(df.shape)
print(df.head())
print(df.tail())
print(df["Close"].iloc[-1])