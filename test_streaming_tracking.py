#!/usr/bin/env python3
"""Test script to simulate streaming endpoint tracking"""

import json
import os
from datetime import datetime

def simulate_streaming_interaction():
    """Simulate what happens when streaming endpoint is called"""
    analytics_file = "analytics_data.json"
    
    try:
        # Load current data
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"total_interactions": 0, "daily": {}}
        
        print(f"Before: {data}")
        
        # Increment counters (same logic as streaming endpoint)
        data["total_interactions"] += 1
        today = datetime.now().strftime("%Y-%m-%d")
        data["daily"][today] = data["daily"].get(today, 0) + 1
        
        # Write back to file
        with open(analytics_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"After: {data}")
        print(f"✅ Streaming interaction tracked: {data['total_interactions']} total")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing streaming endpoint interaction tracking...")
    simulate_streaming_interaction()