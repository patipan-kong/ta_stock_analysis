import yfinance as yf

print("before")

t = yf.Ticker("AAPL01.BK")

print("after ticker")

df = t.history(period="5d", timeout=10)

print("after history")

print(df)
print(df.tail())
print(df["Close"].tail())

df2 = yf.Ticker("AAPL").history(period="5y")

print(df2["Close"].tail())