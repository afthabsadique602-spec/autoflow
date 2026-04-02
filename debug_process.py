import requests
import json
import os

url = "http://127.0.0.1:5002/process"
file_path = r"C:\Users\aftha\.gemini\antigravity\scratch\autoflow\sample_data.csv"

if not os.path.exists(file_path):
    # Create sample data if missing
    with open(file_path, 'w') as f:
        f.write("id,name,email,salary\n1,John,john@example.com,50000\n2,Jane,,60000\n3,John,john@example.com,50000")

files = {'file': open(file_path, 'rb')}
settings = {
    "global": {"remove_duplicates": True, "trim_all": True},
    "columns": {
        "email": {"fill": "mode", "strip": True}
    }
}
data = {"settings": json.dumps(settings)}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
