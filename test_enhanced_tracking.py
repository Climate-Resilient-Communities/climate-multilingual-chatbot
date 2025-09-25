#!/usr/bin/env python3
"""
Test the enhanced tracking functionality
"""

import sys
sys.path.append('.')

from admin_api_server import get_detailed_queries_by_classification
import sqlite3

def test_enhanced_tracking():
    """Test the enhanced tracking functionality"""
    
    print("=== ENHANCED TRACKING TEST ===\n")
    
    # Test detailed queries
    result = get_detailed_queries_by_classification()
    print("Detailed queries tracking:")
    print(f"  On-topic: {len(result['on_topic'])} queries")
    print(f"  Off-topic: {len(result['off_topic'])} queries") 
    print(f"  Harmful: {len(result['harmful'])} queries")
    
    # Test database breakdown
    print("\nDatabase breakdown:")
    with sqlite3.connect('admin_analytics.db') as conn:
        cursor = conn.cursor()
        
        # Classification breakdown
        cursor.execute('SELECT classification, COUNT(*) FROM detailed_queries GROUP BY classification')
        print("  Classifications:")
        for classification, count in cursor.fetchall():
            print(f"    {classification}: {count}")
            
        # Language breakdown  
        cursor.execute('SELECT language, COUNT(*) FROM detailed_queries GROUP BY language')
        print("  Languages:")
        for language, count in cursor.fetchall():
            print(f"    {language}: {count}")
            
        # Model breakdown
        cursor.execute('SELECT model, COUNT(*) FROM detailed_queries GROUP BY model')
        print("  Models:")
        for model, count in cursor.fetchall():
            print(f"    {model}: {count}")
    
    # Show sample queries
    print("\nSample queries:")
    for category, queries in result.items():
        if queries:
            q = queries[0]
            print(f"  {q['classification']}: {q['query_text'][:50]}...")
    
    print("\n✅ Enhanced tracking is working!")

if __name__ == "__main__":
    test_enhanced_tracking()