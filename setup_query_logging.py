#!/usr/bin/env python3
"""
Setup script for query logging database and admin analytics.
This script initializes the SQLite database and verifies everything is working.
"""

import sqlite3
import os
import sys
from pathlib import Path

def test_sqlite():
    """Test if SQLite is available"""
    try:
        import sqlite3
        print("✅ SQLite module is available")
        print(f"   SQLite version: {sqlite3.sqlite_version}")
        return True
    except ImportError:
        print("❌ SQLite module is not available")
        return False

def create_database(db_path="admin_analytics.db"):
    """Create and initialize the analytics database"""
    try:
        print(f"📂 Creating database at: {os.path.abspath(db_path)}")
        
        # Create database and tables
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create main table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detailed_queries (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    classification TEXT NOT NULL CHECK (classification IN ('on-topic', 'off-topic', 'harmful')),
                    safety_score REAL NOT NULL,
                    language TEXT NOT NULL,
                    model TEXT NOT NULL,
                    response_generated BOOLEAN NOT NULL,
                    blocked_reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_classification ON detailed_queries (classification);
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON detailed_queries (timestamp);
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_session ON detailed_queries (session_id);
            ''')
            
            conn.commit()
            
        print("✅ Database created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create database: {e}")
        return False

def test_database_operations(db_path="admin_analytics.db"):
    """Test basic database operations"""
    try:
        print("🔄 Testing database operations...")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Test insert
            test_data = (
                'test-id-001',
                '2025-09-24T10:00:00Z',
                'test-session-001',
                'What causes climate change?',
                'on-topic',
                0.95,
                'English',
                'aws_nova_lite',
                True,
                None
            )
            
            cursor.execute('''
                INSERT OR REPLACE INTO detailed_queries 
                (id, timestamp, session_id, query_text, classification, safety_score, 
                 language, model, response_generated, blocked_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', test_data)
            
            # Test select
            cursor.execute('SELECT COUNT(*) FROM detailed_queries WHERE id = ?', ('test-id-001',))
            count = cursor.fetchone()[0]
            
            if count == 1:
                print("✅ Database operations working correctly")
                
                # Clean up test data
                cursor.execute('DELETE FROM detailed_queries WHERE id = ?', ('test-id-001',))
                conn.commit()
                return True
            else:
                print("❌ Database operations failed")
                return False
                
    except Exception as e:
        print(f"❌ Database operation test failed: {e}")
        return False

def populate_sample_data(db_path="admin_analytics.db"):
    """Populate database with sample data for testing"""
    try:
        print("📝 Populating sample data...")
        
        from datetime import datetime, timedelta
        import uuid
        
        sample_queries = [
            {
                'id': str(uuid.uuid4()),
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
                'session_id': 'sess_001',
                'query_text': 'What are the main causes of climate change and how do they impact global temperatures?',
                'classification': 'on-topic',
                'safety_score': 0.95,
                'language': 'English',
                'model': 'aws_nova_lite',
                'response_generated': True,
                'blocked_reason': None
            },
            {
                'id': str(uuid.uuid4()),
                'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
                'session_id': 'sess_002',
                'query_text': 'How can renewable energy help reduce carbon emissions in developing countries?',
                'classification': 'on-topic',
                'safety_score': 0.92,
                'language': 'English',
                'model': 'cohere_command_a',
                'response_generated': True,
                'blocked_reason': None
            },
            {
                'id': str(uuid.uuid4()),
                'timestamp': (datetime.now() - timedelta(minutes=45)).isoformat(),
                'session_id': 'sess_003',
                'query_text': '¿Cuáles son los efectos del cambio climático en América Latina?',
                'classification': 'on-topic',
                'safety_score': 0.94,
                'language': 'Spanish',
                'model': 'aws_nova_lite',
                'response_generated': True,
                'blocked_reason': None
            },
            {
                'id': str(uuid.uuid4()),
                'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat(),
                'session_id': 'sess_004',
                'query_text': 'What is your favorite pizza topping?',
                'classification': 'off-topic',
                'safety_score': 0.85,
                'language': 'English',
                'model': 'aws_nova_lite',
                'response_generated': False,
                'blocked_reason': None
            },
            {
                'id': str(uuid.uuid4()),
                'timestamp': (datetime.now() - timedelta(minutes=20)).isoformat(),
                'session_id': 'sess_005',
                'query_text': 'How do I cook pasta?',
                'classification': 'off-topic',
                'safety_score': 0.88,
                'language': 'English',
                'model': 'aws_nova_lite',
                'response_generated': False,
                'blocked_reason': None
            },
            {
                'id': str(uuid.uuid4()),
                'timestamp': (datetime.now() - timedelta(minutes=10)).isoformat(),
                'session_id': 'sess_006',
                'query_text': '[Content filtered - inappropriate request]',
                'classification': 'harmful',
                'safety_score': 0.15,
                'language': 'English',
                'model': 'aws_nova_lite',
                'response_generated': False,
                'blocked_reason': 'Inappropriate content detected'
            },
            {
                'id': str(uuid.uuid4()),
                'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
                'session_id': 'sess_007',
                'query_text': '[Content filtered - safety violation]',
                'classification': 'harmful',
                'safety_score': 0.08,
                'language': 'English',
                'model': 'aws_nova_lite',
                'response_generated': False,
                'blocked_reason': 'Safety guardrail triggered'
            }
        ]
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            for query in sample_queries:
                cursor.execute('''
                    INSERT OR REPLACE INTO detailed_queries 
                    (id, timestamp, session_id, query_text, classification, safety_score, 
                     language, model, response_generated, blocked_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    query['id'],
                    query['timestamp'],
                    query['session_id'],
                    query['query_text'],
                    query['classification'],
                    query['safety_score'],
                    query['language'],
                    query['model'],
                    query['response_generated'],
                    query['blocked_reason']
                ))
            
            conn.commit()
            
            # Get counts by classification
            cursor.execute('''
                SELECT classification, COUNT(*) 
                FROM detailed_queries 
                GROUP BY classification
            ''')
            
            results = cursor.fetchall()
            print("✅ Sample data populated successfully:")
            for classification, count in results:
                print(f"   {classification}: {count} queries")
                
        return True
        
    except Exception as e:
        print(f"❌ Failed to populate sample data: {e}")
        return False

def test_query_logger():
    """Test the query logger utility"""
    try:
        print("🔄 Testing query logger utility...")
        
        # Add src to path
        sys.path.append('src')
        
        from utils.query_logger import QueryLogger, log_user_query
        
        # Test basic logging
        success = log_user_query(
            session_id="test_setup",
            query_text="Test query for setup validation",
            classification="on-topic",
            safety_score=0.9,
            language="English",
            model="test_model",
            response_generated=True
        )
        
        if success:
            print("✅ Query logger utility working correctly")
            return True
        else:
            print("❌ Query logger utility failed")
            return False
            
    except ImportError as e:
        print(f"⚠️  Query logger utility not yet available: {e}")
        print("   This is normal if you haven't integrated it yet")
        return True
    except Exception as e:
        print(f"❌ Query logger test failed: {e}")
        return False

def check_admin_api_server():
    """Check if admin_api_server.py exists and has the right imports"""
    try:
        print("🔄 Checking admin API server setup...")
        
        admin_api_path = "admin_api_server.py"
        if not os.path.exists(admin_api_path):
            print(f"❌ Admin API server not found at {admin_api_path}")
            return False
        
        with open(admin_api_path, 'r') as f:
            content = f.read()
        
        required_imports = ['sqlite3', 'threading', 'uuid']
        missing_imports = []
        
        for imp in required_imports:
            if f"import {imp}" not in content:
                missing_imports.append(imp)
        
        if missing_imports:
            print(f"⚠️  Admin API server missing imports: {missing_imports}")
        else:
            print("✅ Admin API server imports look good")
        
        # Check for database functions
        if "init_database" in content and "store_detailed_query" in content:
            print("✅ Admin API server has database functions")
            return True
        else:
            print("⚠️  Admin API server missing some database functions")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check admin API server: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Query Logging for Climate Chatbot Admin Dashboard")
    print("=" * 70)
    
    all_good = True
    
    # Test 1: Check SQLite availability
    if not test_sqlite():
        print("\n❌ CRITICAL: SQLite is not available. Please install Python with SQLite support.")
        return False
    
    # Test 2: Create database
    if not create_database():
        print("\n❌ CRITICAL: Failed to create database")
        all_good = False
    
    # Test 3: Test database operations
    if not test_database_operations():
        print("\n❌ CRITICAL: Database operations failed")
        all_good = False
    
    # Test 4: Populate sample data
    if not populate_sample_data():
        print("\n⚠️  WARNING: Failed to populate sample data")
    
    # Test 5: Test query logger utility
    test_query_logger()
    
    # Test 6: Check admin API server
    check_admin_api_server()
    
    print("\n" + "=" * 70)
    
    if all_good:
        print("✅ SETUP COMPLETE!")
        print("\nNext steps:")
        print("1. Start admin API server: python admin_api_server.py")
        print("2. View dashboard at: http://localhost:8001/admin/analytics?password=YOUR_PASSWORD")
        print("3. Follow QUERY_LOGGING_INTEGRATION.md to integrate with your main app")
        print(f"\nDatabase created at: {os.path.abspath('admin_analytics.db')}")
    else:
        print("❌ SETUP HAD ISSUES!")
        print("Please check the errors above and try again.")
    
    return all_good

if __name__ == "__main__":
    main()