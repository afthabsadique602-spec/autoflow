import pandas as pd
import numpy as np
import os

# Create a dataset with 100 rows
data = {
    'ID': range(1, 101),
    'Name': ['User_' + str(i) for i in range(1, 101)],
    'Email': ['user' + str(i) + '@example.com' for i in range(1, 101)],
    'Department': np.random.choice(['Engineering', 'Marketing', 'Sales', 'HR', None], 100),
    'Salary': np.random.choice([50000, 60000, 75000, 90000, None], 100)
}

df = pd.DataFrame(data)

# Add 10 duplicates
duplicates = df.sample(10)
df = pd.concat([df, duplicates], ignore_index=True)

# Add some missing values randomly
for col in ['Email', 'Department', 'Salary']:
    df.loc[df.sample(frac=0.1).index, col] = np.nan

# Save as .xlsx
output_path = 'large_test_data.xlsx'
df.to_excel(output_path, index=False, engine='openpyxl')
print(f"Generated {output_path} with {len(df)} rows.")
