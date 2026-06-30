import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio

from services.portfolio_rebuilder import _build_price_matrix


async def main():
    symbols = ['AAPL01.BK', 'AMZN01.BK', 'BH.BK', 'GOOGL01.BK', 'GULF.BK', 'ICHI.BK', 'KBANK.BK', 'MICRON01.BK', 'NVDA01.BK', 'SCB.BK', 'TOA.BK']

    dates = [
        "2026-05-23",
        "2026-05-25",
        "2026-05-26",
    ]

    matrix = await _build_price_matrix(symbols, dates)

    print("=" * 80)
    print("FINAL PRICE MATRIX")
    print("=" * 80)

    for sym in symbols:
        print(sym)
        for d in dates:
            print(f"  {d} -> {matrix[sym][d]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())