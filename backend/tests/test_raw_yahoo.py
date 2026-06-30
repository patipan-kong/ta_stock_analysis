import yfinance as yf

t = yf.Ticker("GULF.BK")

print(type(t._data))
print(t._data)