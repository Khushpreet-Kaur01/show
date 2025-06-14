#!/usr/bin/env python3
"""
Comprehensive debug script to figure out the correct format for final endpoint
"""

import requests
import json
from config.settings import Config

def test_final_endpoint_formats():
    """Test different data formats for the final endpoint"""
    
    print("🔍 Comprehensive Final Endpoint Testing")
    print("=" * 60)
    
    base_url = Config.API_BASE_URL
    final_endpoint = "/api/v1/admin/survey/final"
    full_url = f"{base_url}{final_endpoint}"
    
    headers = {
        "x-api-key": Config.API_KEY,
        "Content-Type": "application/json"
    }
    
    print(f"Testing: {full_url}")
    print(f"API Key: {Config.API_KEY[:8]}...")
    print()
    
    # Test different request methods
    methods_to_test = ['GET', 'POST', 'PUT', 'PATCH']
    
    print("📡 Testing HTTP Methods:")
    print("-" * 30)
    for method in methods_to_test:
        try:
            if method == 'GET':
                response = requests.get(full_url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(full_url, headers=headers, json={"questions": []}, timeout=10)
            elif method == 'PUT':
                response = requests.put(full_url, headers=headers, json={"questions": []}, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(full_url, headers=headers, json={"questions": []}, timeout=10)
                
            print(f"{method}: {response.status_code} - {response.text[:50]}...")
        except Exception as e:
            print(f"{method}: Error - {str(e)[:50]}...")
    
    print()
    
    # Test different payload formats
    print("📦 Testing Different Payload Formats:")
    print("-" * 40)
    
    test_payloads = [
        # Format 1: Empty
        {},
        
        # Format 2: Empty questions array
        {"questions": []},
        
        # Format 3: Single question with minimal data
        {"questions": [{"question": "test", "questionType": "MCQ"}]},
        
        # Format 4: Without questions wrapper
        [{"question": "test", "questionType": "MCQ"}],
        
        # Format 5: With different wrapper
        {"data": [{"question": "test", "questionType": "MCQ"}]},
        
        # Format 6: Single question (not array)
        {"question": "test", "questionType": "MCQ"},
        
        # Format 7: With questionId
        {"questions": [{"questionId": "test-id", "question": "test"}]},
        
        # Format 8: Minimal MCQ format (based on our working data)
        {
            "questions": [{
                "question": "test question",
                "questionType": "MCQ", 
                "answers": [{
                    "answer": "test answer",
                    "isCorrect": True,
                    "rank": 1,
                    "score": 100
                }]
            }]
        }
    ]
    
    for i, payload in enumerate(test_payloads, 1):
        try:
            response = requests.post(full_url, headers=headers, json=payload, timeout=10)
            print(f"Format {i}: {response.status_code} - {response.text[:80]}...")
            if response.status_code not in [400, 500]:
                print(f"  ✅ SUCCESS! Format {i} worked!")
                print(f"  Payload: {json.dumps(payload, indent=2)}")
                break
        except Exception as e:
            print(f"Format {i}: Error - {str(e)[:50]}...")
    
    print()
    
    # Test different headers
    print("🔧 Testing Different Headers:")
    print("-" * 30)
    
    header_variations = [
        # Original headers
        {"x-api-key": Config.API_KEY, "Content-Type": "application/json"},
        
        # Without Content-Type
        {"x-api-key": Config.API_KEY},
        
        # Different Content-Type
        {"x-api-key": Config.API_KEY, "Content-Type": "application/x-www-form-urlencoded"},
        
        # Different API key format
        {"Authorization": f"Bearer {Config.API_KEY}", "Content-Type": "application/json"},
        
        # Different API key header
        {"api-key": Config.API_KEY, "Content-Type": "application/json"},
        {"X-API-KEY": Config.API_KEY, "Content-Type": "application/json"},
    ]
    
    test_payload = {"questions": []}
    
    for i, test_headers in enumerate(header_variations, 1):
        try:
            response = requests.post(full_url, headers=test_headers, json=test_payload, timeout=10)
            print(f"Header {i}: {response.status_code} - {response.text[:50]}...")
            if response.status_code not in [400, 401, 500]:
                print(f"  ✅ SUCCESS! Header format {i} worked!")
                print(f"  Headers: {test_headers}")
                break
        except Exception as e:
            print(f"Header {i}: Error - {str(e)[:50]}...")
    
    print()
    print("🔍 ANALYSIS:")
    print("=" * 20)
    print("• 400 Bad Request means the endpoint exists but rejects our data format")
    print("• We need to find the correct payload structure the server expects")
    print("• Try the successful format from above, or contact the API developer")
    print()
    print("💡 Next Steps:")
    print("1. Check API documentation for the final endpoint format")
    print("2. Contact server administrator for correct payload format")
    print("3. Look at network requests from the frontend app (if any)")

def test_with_real_data():
    """Test with a real question from our successful ranking"""
    print("\n🎯 Testing with Real Question Data:")
    print("-" * 40)
    
    # Use the exact format from our successful ranking
    real_question = {
        "questions": [{
            "question": "mcq test advanced",
            "questionType": "Mcq",  # Note: capital M
            "questionCategory": "Culture",
            "questionLevel": "Advanced", 
            "timesSkipped": 0,
            "timesAnswered": 0,
            "answers": [{
                "answer": "3",
                "responseCount": 0,
                "isCorrect": True,
                "rank": 1,
                "score": 100
            }]
        }]
    }
    
    headers = {
        "x-api-key": Config.API_KEY,
        "Content-Type": "application/json"
    }
    
    full_url = f"{Config.API_BASE_URL}/api/v1/admin/survey/final"
    
    try:
        response = requests.post(full_url, headers=headers, json=real_question, timeout=30)
        print(f"Real Data Test: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ SUCCESS! Real data format works!")
        elif response.status_code == 400:
            print("❌ Still 400 - the server expects a different format")
        elif response.status_code == 500:
            print("❌ 500 - server error (might be processing our data)")
        else:
            print(f"🤔 Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_final_endpoint_formats()
    test_with_real_data()