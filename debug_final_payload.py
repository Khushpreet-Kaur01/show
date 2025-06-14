#!/usr/bin/env python3
"""
Debug script to test different payload formats for final submission
"""

import requests
import json
from config.settings import Config

def test_minimal_payloads():
    """Test with very minimal payloads to isolate the issue"""
    
    print("🔍 Testing Minimal Final Payloads")
    print("=" * 50)
    
    headers = {
        "x-api-key": Config.API_KEY,
        "Content-Type": "application/json"
    }
    
    final_url = f"{Config.API_BASE_URL}/api/v1/admin/survey/final"
    
    # Test 1: Single MCQ question with minimal data
    test_mcq = {
        "questions": [{
            "question": "Test question?",
            "questionType": "MCQ",  # Try uppercase
            "questionCategory": "Test",
            "questionLevel": "Beginner",
            "timesSkipped": 0,
            "timesAnswered": 0,
            "answers": [
                {"answer": "Option A", "responseCount": 1, "isCorrect": True, "rank": 1, "score": 100},
                {"answer": "Option B", "responseCount": 0, "isCorrect": False, "rank": 0, "score": 0},
                {"answer": "Option C", "responseCount": 0, "isCorrect": False, "rank": 0, "score": 0},
                {"answer": "Option D", "responseCount": 0, "isCorrect": False, "rank": 0, "score": 0}
            ]
        }]
    }
    
    print("Test 1: Simple MCQ with uppercase questionType")
    try:
        response = requests.post(final_url, headers=headers, json=test_mcq, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code != 400:
            print("✅ SUCCESS!")
            print(f"Response: {response.text[:200]}")
        else:
            print(f"❌ Failed: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Test 2: Same but with lowercase questionType
    test_mcq_lower = test_mcq.copy()
    test_mcq_lower["questions"][0]["questionType"] = "mcq"
    
    print("Test 2: Simple MCQ with lowercase questionType")
    try:
        response = requests.post(final_url, headers=headers, json=test_mcq_lower, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code != 400:
            print("✅ SUCCESS!")
            print(f"Response: {response.text[:200]}")
        else:
            print(f"❌ Failed: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Test 3: Single Input question
    test_input = {
        "questions": [{
            "question": "Test input question?",
            "questionType": "Input",
            "questionCategory": "Test",
            "questionLevel": "Beginner",
            "timesSkipped": 0,
            "timesAnswered": 5,
            "answers": [
                {"answer": "Answer 1", "responseCount": 3, "isCorrect": True, "rank": 1, "score": 100},
                {"answer": "Answer 2", "responseCount": 2, "isCorrect": True, "rank": 2, "score": 80},
                {"answer": "Answer 3", "responseCount": 1, "isCorrect": True, "rank": 3, "score": 60}
            ]
        }]
    }
    
    print("Test 3: Simple Input question")
    try:
        response = requests.post(final_url, headers=headers, json=test_input, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code != 400:
            print("✅ SUCCESS!")
            print(f"Response: {response.text[:200]}")
        else:
            print(f"❌ Failed: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Test 4: Check if it's a collection validation issue
    test_empty = {"questions": []}
    
    print("Test 4: Empty questions array")
    try:
        response = requests.post(final_url, headers=headers, json=test_empty, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

def test_field_variations():
    """Test different field name variations"""
    
    print("\n🔧 Testing Field Name Variations")
    print("=" * 40)
    
    headers = {
        "x-api-key": Config.API_KEY,
        "Content-Type": "application/json"
    }
    
    final_url = f"{Config.API_BASE_URL}/api/v1/admin/survey/final"
    
    # Base question structure
    base_question = {
        "question": "Test question?",
        "questionType": "MCQ",
        "questionCategory": "Test", 
        "questionLevel": "Beginner",
        "timesSkipped": 0,
        "timesAnswered": 0,
        "answers": [
            {"answer": "Option A", "responseCount": 1, "isCorrect": True, "rank": 1, "score": 100},
            {"answer": "Option B", "responseCount": 0, "isCorrect": False, "rank": 0, "score": 0},
            {"answer": "Option C", "responseCount": 0, "isCorrect": False, "rank": 0, "score": 0},
            {"answer": "Option D", "responseCount": 0, "isCorrect": False, "rank": 0, "score": 0}
        ]
    }
    
    variations = [
        # Test different collection names
        {"finalQuestions": [base_question]},
        {"data": [base_question]},
        
        # Test with _id fields
        {
            "questions": [{
                **base_question,
                "_id": "test-question-id",
                "answers": [
                    {**ans, "_id": f"test-answer-{i}"} 
                    for i, ans in enumerate(base_question["answers"])
                ]
            }]
        },
        
        # Test without optional fields
        {
            "questions": [{
                "question": "Test question?",
                "questionType": "MCQ",
                "answers": [
                    {"answer": "Option A", "isCorrect": True},
                    {"answer": "Option B", "isCorrect": False},
                    {"answer": "Option C", "isCorrect": False},
                    {"answer": "Option D", "isCorrect": False}
                ]
            }]
        }
    ]
    
    for i, variation in enumerate(variations, 1):
        print(f"Variation {i}: {list(variation.keys())[0]}")
        try:
            response = requests.post(final_url, headers=headers, json=variation, timeout=30)
            print(f"  Status: {response.status_code}")
            if response.status_code not in [400, 500]:
                print(f"  ✅ SUCCESS! Response: {response.text[:100]}")
                break
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    test_minimal_payloads()
    test_field_variations()
    
    print("\n💡 RECOMMENDATIONS:")
    print("1. Try the successful format from above")
    print("2. Check if server expects different field names")
    print("3. Verify if collection name should be 'finalQuestions'")
    print("4. Check if _id fields are required")