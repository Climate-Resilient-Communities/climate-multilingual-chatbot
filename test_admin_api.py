#!/usr/bin/env python3
"""
Test the updated admin API with manual feedback entries
"""

import requests
import json

def test_admin_api():
    """Test the admin API to see the new manual feedback data"""
    try:
        # Test the admin API endpoint
        url = "http://localhost:8001/admin/analytics"
        params = {"password": "mlcc_2025"}
        
        print("🔍 Testing Admin API with manual feedback...")
        print(f"URL: {url}")
        print(f"Password: {params['password']}")
        print("=" * 60)
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Response successful!")
            print(json.dumps(data, indent=2))
            
            # Check if manual feedback is included
            if 'manual_feedback' in data:
                print("\n📋 Manual Feedback Summary:")
                print(f"  Count: {data['manual_feedback']['count']}")
                print(f"  Entries: {len(data['manual_feedback']['entries'])}")
                
                if data['manual_feedback']['entries']:
                    print("\n📝 Manual Feedback Entries:")
                    for i, entry in enumerate(data['manual_feedback']['entries'], 1):
                        print(f"  {i}. {entry['timestamp']} - {entry['feedback_type']}")
                        print(f"     Language: {entry['language']}")
                        print(f"     Description: {entry['description'][:50]}...")
                        print()
            else:
                print("⚠️  No manual_feedback key found in response")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_admin_api()