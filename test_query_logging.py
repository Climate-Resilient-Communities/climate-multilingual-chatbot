#!/usr/bin/env python3
"""
Quick test to verify the query logging system is working correctly.
"""

import sqlite3
import sys
import os

def test_database_connection():
    """Test basic database connectivity"""
    print("🔄 Testing database connection...")
    try:
        with sqlite3.connect("admin_analytics.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM detailed_queries")
            count = cursor.fetchone()[0]
            print(f"✅ Database connected successfully - {count} queries stored")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_query_retrieval():
    """Test retrieving queries by classification"""
    print("🔄 Testing query retrieval by classification...")
    try:
        with sqlite3.connect("admin_analytics.db") as conn:
            cursor = conn.cursor()
            
            # Get counts by classification
            cursor.execute("""
                SELECT classification, COUNT(*) 
                FROM detailed_queries 
                GROUP BY classification
                ORDER BY classification
            """)
            
            results = cursor.fetchall()
            print("✅ Query retrieval working:")
            for classification, count in results:
                print(f"   {classification}: {count} queries")
            
            # Get sample queries from each category
            print("\n📋 Sample queries:")
            for classification in ['on-topic', 'off-topic', 'harmful']:
                cursor.execute("""
                    SELECT session_id, query_text, safety_score, language 
                    FROM detailed_queries 
                    WHERE classification = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 2
                """, (classification,))
                
                queries = cursor.fetchall()
                print(f"\n  {classification.upper()}:")
                for session_id, query_text, safety_score, language in queries:
                    print(f"    [{session_id[:8]}] ({language}) Score: {safety_score:.2f}")
                    print(f"    → {query_text[:60]}{'...' if len(query_text) > 60 else ''}")
            
            return True
    except Exception as e:
        print(f"❌ Query retrieval failed: {e}")
        return False

def test_query_logger_import():
    """Test importing and using the query logger"""
    print("🔄 Testing query logger import...")
    try:
        # Add src to path if not already there
        if 'src' not in sys.path:
            sys.path.append('src')
        
        from utils.query_logger import log_user_query, get_query_logger
        
        # Test logging a new query
        success = log_user_query(
            session_id="test_verification",
            query_text="How does deforestation contribute to climate change?",
            classification="on-topic",
            safety_score=0.97,
            language="English",
            model="verification_test",
            response_generated=True
        )
        
        if success:
            print("✅ Query logger import and usage working")
            
            # Verify it was stored
            logger = get_query_logger()
            stats = logger.get_statistics()
            print(f"   Current statistics: {stats}")
            return True
        else:
            print("❌ Query logging failed")
            return False
            
    except ImportError as e:
        print(f"❌ Query logger import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Query logger test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Query Logging System")
    print("=" * 40)
    
    all_tests_passed = True
    
    # Test 1: Database connection
    if not test_database_connection():
        all_tests_passed = False
    
    print()
    
    # Test 2: Query retrieval
    if not test_query_retrieval():
        all_tests_passed = False
    
    print()
    
    # Test 3: Query logger import
    if not test_query_logger_import():
        all_tests_passed = False
    
    print("\n" + "=" * 40)
    if all_tests_passed:
        print("✅ ALL TESTS PASSED!")
        print("\n🎉 Your query logging system is ready to use!")
        print("\nQuick start:")
        print("1. Start admin server: python admin_api_server.py")
        print("2. Visit dashboard: http://localhost:8001/admin/analytics?password=YOUR_ADMIN_PASSWORD")
        print("3. Integrate with your app using the query logger utility")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please check the errors above.")

if __name__ == "__main__":
    main()