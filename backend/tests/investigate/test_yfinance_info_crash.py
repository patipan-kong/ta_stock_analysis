import pandas as pd

print(pd.Timestamp("2026-07-01").floor("D"))
print(pd.Timestamp("2026-07-01").ceil("D"))
print(pd.Timestamp("2026-07-01").round("D"))