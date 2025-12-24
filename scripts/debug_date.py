import pandas as pd
import numpy as np

# Sample data
data = {
    '日付': ['2025年12月14日', '2025年12月6日'],
    'past_1_date': ['2025/11/08', '2025/11/08']
}
df = pd.DataFrame(data)

print("Original DF:")
print(df)

# Try parsing
print("\nParsing Current Date:")
try:
    df['date_dt'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
    print(df['date_dt'])
except Exception as e:
    print(e)

print("\nParsing Past Date:")
try:
    df['past_1_dt'] = pd.to_datetime(df['past_1_date'], errors='coerce')
    print(df['past_1_dt'])
except Exception as e:
    print(e)

print("\nInterval:")
df['interval'] = (df['date_dt'] - df['past_1_dt']).dt.days
print(df['interval'])
