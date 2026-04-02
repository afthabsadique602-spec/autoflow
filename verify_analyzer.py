import pandas as pd
from tools.data_analyzer import analyze_data
import io

def test_analysis():
    # Create test data with specific issues
    data = """Name,Age,Email
Alice,25,alice@example.com
Bob, ,bob@example.com
Charlie,thirty,charlie@example.com
David,40,
    ,50,eve@example.com
"""
    df = pd.read_csv(io.StringIO(data))
    
    print("Testing analyze_data...")
    analysis = analyze_data(df)
    
    for col in analysis['columns']:
        print(f"Column: {col['name']}")
        print(f"  Type: {col['type']}")
        print(f"  Missing: {col['missing']}")
        print(f"  Issues: {col['issues']}")
        
    # Check for Empty Spaces in 'Name' (line 6 has a space as name? No, actually line 4 has nothing, line 6 has nothing)
    # Wait, line 3 (Bob, ,) has a space in Email? No, Age.
    # Name has a leading space in line 6? No, it's just empty.
    
    # Specific checks
    age_col = next(c for c in analysis['columns'] if c['name'] == 'Age')
    # Bob has " " (space) in Age? No, I put "Bob, ,". pd.read_csv might treat that as NaN or " ".
    # Let's see.
    
if __name__ == "__main__":
    test_analysis()
