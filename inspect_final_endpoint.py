#!/usr/bin/env python3
"""
Inspect what the final endpoint actually contains
"""

import requests
import json
from config.settings import Config

def inspect_final_endpoint():
    """See what data the final endpoint returns"""
    
    print("🔍 Inspecting Final Endpoint Data")
    print("=" * 50)
    
    headers = {
        "x-api-key": Config.API_KEY,
        "Content-Type": "application/json"
    }
    
    final_url = f"{Config.API_BASE_URL}/api/v1/admin/survey/final"
    
    try:
        # GET the final endpoint to see what's there
        response = requests.get(final_url, headers=headers, timeout=30)
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("📊 Final Endpoint Contents:")
                print("-" * 30)
                print(json.dumps(data, indent=2))
                
                # Analyze the structure
                if isinstance(data, dict):
                    if 'data' in data and isinstance(data['data'], list):
                        print(f"\n📈 Analysis:")
                        print(f"- Total final questions: {len(data['data'])}")
                        
                        # Look at question structure
                        if data['data']:
                            sample = data['data'][0]
                            print(f"- Sample question keys: {list(sample.keys())}")
                            
                            if 'questionType' in sample:
                                types = {}
                                for q in data['data']:
                                    qtype = q.get('questionType', 'Unknown')
                                    types[qtype] = types.get(qtype, 0) + 1
                                print(f"- Question types: {types}")
                        
                        print(f"\n💡 INSIGHT:")
                        print(f"The final endpoint seems to be a READ-ONLY collection!")
                        print(f"It contains finalized questions that have been submitted.")
                        print(f"This explains why POST requests return 400 - it might not accept new submissions.")
                
            except json.JSONDecodeError:
                print("Response is not JSON:")
                print(response.text[:500])
        else:
            print(f"Error response: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error: {e}")

def compare_endpoints():
    """Compare the main endpoint vs final endpoint"""
    print("\n🔄 Comparing Endpoints:")
    print("=" * 30)
    
    headers = {
        "x-api-key": Config.API_KEY,
        "Content-Type": "application/json"
    }
    
    # Get main endpoint data
    main_url = f"{Config.API_BASE_URL}/api/v1/admin/survey"
    final_url = f"{Config.API_BASE_URL}/api/v1/admin/survey/final"
    
    try:
        main_response = requests.get(main_url, headers=headers, timeout=30)
        final_response = requests.get(final_url, headers=headers, timeout=30)
        
        if main_response.status_code == 200 and final_response.status_code == 200:
            main_data = main_response.json()
            final_data = final_response.json()
            
            main_questions = main_data.get('data', [])
            final_questions = final_data.get('data', [])
            
            print(f"Main endpoint questions: {len(main_questions)}")
            print(f"Final endpoint questions: {len(final_questions)}")
            
            # Check if any questions exist in both
            main_ids = {q.get('_id') for q in main_questions if '_id' in q}
            final_ids = {q.get('_id') for q in final_questions if '_id' in q}
            
            common_ids = main_ids.intersection(final_ids)
            print(f"Questions in both: {len(common_ids)}")
            
            if len(final_questions) > 0:
                print(f"\n📋 Sample final question structure:")
                sample_final = final_questions[0]
                print(json.dumps(sample_final, indent=2)[:500])
                print("...")
        
    except Exception as e:
        print(f"Error comparing: {e}")

def test_alternative_submission_methods():
    """Test if there might be other ways to submit to final"""
    print("\n🧪 Testing Alternative Submission Methods:")
    print("=" * 45)
    
    headers = {
        "x-api-key": Config.API_KEY,
        "Content-Type": "application/json"
    }
    
    base_url = Config.API_BASE_URL
    
    # Test different endpoints that might accept submissions
    test_endpoints = [
        "/api/v1/admin/survey/final/submit",
        "/api/v1/admin/survey/submit", 
        "/api/v1/admin/survey/finalize",
        "/api/v1/admin/final/submit",
        "/api/v1/survey/final/submit",
        "/api/v1/admin/survey/final/add",
    ]
    
    test_payload = {
        "questions": [{
            "question": "test",
            "questionType": "MCQ",
            "answers": [{
                "answer": "test answer",
                "isCorrect": True,
                "rank": 1,
                "score": 100
            }]
        }]
    }
    
    for endpoint in test_endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.post(url, headers=headers, json=test_payload, timeout=10)
            print(f"{endpoint}: {response.status_code}")
            if response.status_code not in [400, 404, 500]:
                print(f"  ✅ Potential success! Response: {response.text[:100]}")
        except Exception as e:
            print(f"{endpoint}: Error - {str(e)[:30]}")

if __name__ == "__main__":
    inspect_final_endpoint()
    compare_endpoints() 
    test_alternative_submission_methods()