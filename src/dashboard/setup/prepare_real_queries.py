#!/usr/bin/env python3
"""
Clear test data and prepare for real query logging.
This script removes sample data and sets up the system for production use.
"""

import sqlite3
import os
from datetime import datetime

def clear_test_data(db_path="admin_analytics.db"):
    """Remove all test/sample data from the database"""
    try:
        print("🗑️  Clearing test data from database...")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get current count
            cursor.execute("SELECT COUNT(*) FROM detailed_queries")
            before_count = cursor.fetchone()[0]
            
            # Clear all data
            cursor.execute("DELETE FROM detailed_queries")
            conn.commit()
            
            # Get new count
            cursor.execute("SELECT COUNT(*) FROM detailed_queries")
            after_count = cursor.fetchone()[0]
            
            print(f"✅ Cleared {before_count} test queries from database")
            print(f"   Database now has {after_count} queries (should be 0)")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to clear test data: {e}")
        return False

def verify_database_ready():
    """Verify database is ready for production use"""
    try:
        print("🔍 Verifying database is ready...")
        
        with sqlite3.connect("admin_analytics.db") as conn:
            cursor = conn.cursor()
            
            # Check table structure
            cursor.execute("PRAGMA table_info(detailed_queries)")
            columns = cursor.fetchall()
            
            required_columns = [
                'id', 'timestamp', 'session_id', 'query_text', 
                'classification', 'safety_score', 'language', 
                'model', 'response_generated', 'blocked_reason'
            ]
            
            existing_columns = [col[1] for col in columns]
            missing_columns = [col for col in required_columns if col not in existing_columns]
            
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            
            # Check indexes
            cursor.execute("PRAGMA index_list(detailed_queries)")
            indexes = cursor.fetchall()
            
            print("✅ Database structure verified:")
            print(f"   Columns: {len(existing_columns)}")
            print(f"   Indexes: {len(indexes)}")
            print(f"   Ready for real queries: Yes")
            
        return True
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def find_main_application_files():
    """Find the main application files where we need to add logging"""
    print("🔍 Scanning for main application files...")
    
    potential_files = [
        "src/models/gen_response_nova.py",
        "src/models/gen_response_unified.py", 
        "src/models/climate_pipeline.py",
        "src/models/nova_flow.py",
        "src/models/cohere_flow.py",
        "src/models/query_processing_chain.py",
        "src/models/input_guardrail.py",
        "src/models/hallucination_guard.py",
        "src/main_nova.py",
        "simple_api.py"
    ]
    
    found_files = []
    for file_path in potential_files:
        if os.path.exists(file_path):
            found_files.append(file_path)
    
    print(f"📁 Found {len(found_files)} main application files:")
    for file_path in found_files:
        print(f"   • {file_path}")
    
    return found_files

def show_integration_instructions():
    """Show instructions for integrating real query logging"""
    print("\n" + "=" * 70)
    print("🔗 INTEGRATION INSTRUCTIONS - REAL QUERY LOGGING")
    print("=" * 70)
    
    print("\n1️⃣ IMPORT THE QUERY LOGGER")
    print("Add this to your main processing files:")
    print("```python")
    print("from utils.query_logger import log_user_query")
    print("```")
    
    print("\n2️⃣ LOG ON-TOPIC CLIMATE QUERIES")
    print("When processing climate-related queries:")
    print("```python")
    print("# After generating a climate response")
    print("log_user_query(")
    print("    session_id=session_id,  # Your session ID")
    print("    query_text=user_query,  # Original user input")
    print("    classification='on-topic',")
    print("    safety_score=0.95,  # High score for clean climate content")
    print("    language=detected_language,")
    print("    model='aws_nova_lite',  # Or your current model")
    print("    response_generated=True")
    print(")")
    print("```")
    
    print("\n3️⃣ LOG OFF-TOPIC QUERIES")
    print("When queries are not climate-related:")
    print("```python")
    print("# For non-climate questions")
    print("log_user_query(")
    print("    session_id=session_id,")
    print("    query_text=user_query,")
    print("    classification='off-topic',")
    print("    safety_score=0.85,  # Good safety but not climate-related")
    print("    language=detected_language,")
    print("    model=current_model,")
    print("    response_generated=False  # Usually don't respond to off-topic")
    print(")")
    print("```")
    
    print("\n4️⃣ LOG HARMFUL/BLOCKED QUERIES")
    print("When content is blocked by safety filters:")
    print("```python")
    print("# For blocked harmful content")
    print("log_user_query(")
    print("    session_id=session_id,")
    print("    query_text='[Content filtered]',  # Don't store actual harmful text")
    print("    classification='harmful',")
    print("    safety_score=0.1,  # Low safety score")
    print("    language=detected_language,")
    print("    model=current_model,")
    print("    response_generated=False,")
    print("    blocked_reason='Safety guardrail triggered'")
    print(")")
    print("```")
    
    print("\n5️⃣ INTEGRATION POINTS")
    print("Add logging calls at these key points:")
    print("• After query classification (determine if climate-related)")
    print("• After safety/guardrail checks (identify harmful content)")
    print("• After response generation (log successful interactions)")
    print("• In error handlers (log failed/blocked interactions)")

def main():
    """Main function to prepare for real query logging"""
    print("🎯 Preparing Database for Real Query Logging")
    print("=" * 60)
    
    # Step 1: Clear test data
    if not clear_test_data():
        print("❌ Failed to clear test data")
        return False
    
    # Step 2: Verify database
    if not verify_database_ready():
        print("❌ Database verification failed")
        return False
    
    # Step 3: Find application files
    found_files = find_main_application_files()
    
    # Step 4: Show integration instructions
    show_integration_instructions()
    
    print(f"\n📋 NEXT STEPS:")
    print(f"1. Add query logging to your main application files")
    print(f"2. Test with a few real queries")
    print(f"3. Start admin dashboard: python start_admin_dashboard.py") 
    print(f"4. View real data at: http://localhost:8001/admin/analytics")
    
    print(f"\n✅ Database is ready for real queries!")
    print(f"   Database: admin_analytics.db (cleared and ready)")
    print(f"   Found {len(found_files)} application files to integrate")
    
    return True

if __name__ == "__main__":
    main()