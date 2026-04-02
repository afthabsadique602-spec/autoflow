import requests
import os
import json

BASE_URL = "http://127.0.0.1:5002"

def test_analyze_no_file():
    print("\n--- Testing /analyze with no file ---")
    resp = requests.post(f"{BASE_URL}/analyze", files={})
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")

def test_analyze_empty_filename():
    print("\n--- Testing /analyze with empty filename ---")
    # Simulate a file with no name
    files = {'file': ('', b'some data')}
    resp = requests.post(f"{BASE_URL}/analyze", files=files)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")

def test_data_insight_no_data():
    print("\n--- Testing /data_insight with no data source ---")
    resp = requests.post(f"{BASE_URL}/data_insight", data={'focus': 'business'})
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")

def test_data_insight_with_file():
    print("\n--- Testing /data_insight with actual file ---")
    file_path = "test_insights.csv"
    with open(file_path, 'rb') as f:
        files = {'file': (file_path, f)}
        resp = requests.post(f"{BASE_URL}/data_insight", files=files, data={'focus': 'business'})
    print(f"Status: {resp.status_code}")
    # print(f"Body: {resp.text[:500]}...")
    print(f"Body: {resp.text}")

def test_data_insight_with_temp_file_as_dir():
    print("\n--- Testing /data_insight with temp_file pointing to a directory (uploads) ---")
    resp = requests.post(f"{BASE_URL}/data_insight", data={'temp_file': 'uploads', 'focus': 'business'})
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")

if __name__ == "__main__":
    test_analyze_no_file()
    test_analyze_empty_filename()
    test_data_insight_no_data()
    test_data_insight_with_file()
    test_data_insight_with_temp_file_as_dir()
