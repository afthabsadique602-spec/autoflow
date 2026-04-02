import pandas as pd
import json
import os

# Mock data
df = pd.DataFrame({'A': [1, 2, 2], 'B': [4, 5, 5]})

# Mock the stats logic
stats = {
    'rows': int(len(df)),
    'dupes': int(df.duplicated().sum())
}

try:
    print("Testing JSON Serialization...")
    print(json.dumps(stats))
    print("SUCCESS: Native types serializable.")
except Exception as e:
    print(f"FAILURE: {e}")
