import pandas as pd

print(pd.__version__)

t = pd.Timestamp.now("UTC")
print(t)

print("floor")
print(t.floor("D"))