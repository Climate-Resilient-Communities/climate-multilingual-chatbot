#!/usr/bin/env python3
"""
Cleanup test data from the analytics database
"""

import sqlite3

def cleanup_test_data():
    """Remove any test queries from the database"""
    try:
        conn = sqlite3.connect('admin_analytics.db')
        cursor = conn.cursor()
        
        # Delete test queries
        cursor.execute('DELETE FROM detailed_queries WHERE session_id = "default"')
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"Cleaned up {deleted_count} test queries")
        print("Database is ready for production use!")
        
    except Exception as e:
        print(f"Error cleaning up test data: {e}")

if __name__ == "__main__":
    cleanup_test_data()