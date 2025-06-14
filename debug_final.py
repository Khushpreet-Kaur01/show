#!/usr/bin/env python3
import requests
from config.settings import Config

def test_final_endpoint():
    print("🔍 Testing Final Endpoint")
    print("=" * 50)
    
    base_url = Config.API_BASE_URL
    final_endpoint = "/api/v1/admin/survey/final"
    full_url = f"{base_url}{final_endpoint}"
    
    headers = {
        "x-api-key": Config.API_KEY,
        "Content-Type": "application/json"
    }
    
    print(f"Testing: {full_url}")
    
    # Test with empty payload
    try:
        payload = {"questions": []}
        response = requests.post(full_url, headers=headers, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_final_endpoint()