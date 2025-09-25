"""
Query logger utility for storing detailed query information for admin analytics.
This module provides functions to log user queries with their classifications
and safety scores to a local database for dashboard analysis.
"""

import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import os

# Database path - same as admin API server
DB_PATH = "admin_analytics.db"
db_lock = threading.Lock()

class QueryLogger:
    """Utility class for logging detailed query information"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for detailed query tracking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
        except Exception as e:
            print(f"Warning: Failed to initialize query logger database: {e}")
    
    def log_query(
        self,
        session_id: str,
        query_text: str,
        classification: str,
        safety_score: float,
        language: str,
        model: str,
        response_generated: bool,
        blocked_reason: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> bool:
        """
        Log a detailed query to the database
        
        Args:
            session_id: Unique session identifier
            query_text: The actual query text (will be truncated for harmful content)
            classification: 'on-topic', 'off-topic', or 'harmful'
            safety_score: Safety score between 0 and 1 (1 = safe, 0 = harmful)
            language: Query language
            model: Model used for processing
            response_generated: Whether a response was generated
            blocked_reason: Reason for blocking if applicable
            timestamp: ISO timestamp (current time if not provided)
        
        Returns:
            bool: True if successfully logged, False otherwise
        """
        with db_lock:
            try:
                # Validate inputs
                if classification not in ['on-topic', 'off-topic', 'harmful']:
                    print(f"Warning: Invalid classification '{classification}', skipping log")
                    return False
                
                if not (0 <= safety_score <= 1):
                    print(f"Warning: Invalid safety_score '{safety_score}', must be between 0 and 1")
                    return False
                
                # Sanitize query text for harmful content
                if classification == 'harmful':
                    query_text = f"[Content filtered - {blocked_reason or 'safety violation'}]"
                
                # Use current timestamp if not provided
                if not timestamp:
                    timestamp = datetime.now().isoformat()
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO detailed_queries 
                        (id, timestamp, session_id, query_text, classification, safety_score, 
                         language, model, response_generated, blocked_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(uuid.uuid4()),
                        timestamp,
                        session_id,
                        query_text[:500],  # Limit query text length
                        classification,
                        safety_score,
                        language,
                        model,
                        response_generated,
                        blocked_reason
                    ))
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Warning: Failed to log query: {e}")
                return False
    
    def get_recent_queries(self, limit: int = 50) -> Dict[str, Any]:
        """Get recent queries grouped by classification"""
        with db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    result = {
                        'on_topic': [],
                        'off_topic': [],
                        'harmful': []
                    }
                    
                    for classification in ['on-topic', 'off-topic', 'harmful']:
                        cursor.execute('''
                            SELECT id, timestamp, session_id, query_text, classification, 
                                   safety_score, language, model, response_generated, blocked_reason
                            FROM detailed_queries 
                            WHERE classification = ?
                            ORDER BY timestamp DESC
                            LIMIT ?
                        ''', (classification, limit))
                        
                        queries = []
                        for row in cursor.fetchall():
                            queries.append({
                                'id': row[0],
                                'timestamp': row[1],
                                'session_id': row[2],
                                'query_text': row[3],
                                'classification': row[4],
                                'safety_score': row[5],
                                'language': row[6],
                                'model': row[7],
                                'response_generated': bool(row[8]),
                                'blocked_reason': row[9]
                            })
                        
                        result[classification.replace('-', '_')] = queries
                    
                    return result
            except Exception as e:
                print(f"Warning: Failed to retrieve queries: {e}")
                return {'on_topic': [], 'off_topic': [], 'harmful': []}
    
    def get_statistics(self) -> Dict[str, int]:
        """Get query statistics by classification"""
        with db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT classification, COUNT(*) 
                        FROM detailed_queries 
                        GROUP BY classification
                    ''')
                    
                    stats = {}
                    for classification, count in cursor.fetchall():
                        stats[classification.replace('-', '_')] = count
                    
                    return stats
            except Exception as e:
                print(f"Warning: Failed to get statistics: {e}")
                return {}

# Global instance
_query_logger = None

def get_query_logger() -> QueryLogger:
    """Get global query logger instance"""
    global _query_logger
    if _query_logger is None:
        _query_logger = QueryLogger()
    return _query_logger

def log_user_query(
    query: str,
    language: str,
    classification: str,
    safety_score: float,
    response_status: str,
    details: Optional[Dict[str, Any]] = None,
    session_id: str = "default",
    model: str = "aws_nova_lite"
) -> bool:
    """
    Simplified convenience function to log a user query (matches main_nova.py calls)
    
    Args:
        query: The actual query text
        language: Query language 
        classification: 'on-topic', 'off-topic', or 'harmful'
        safety_score: Safety score between 0 and 1
        response_status: Status like "completed", "blocked", "rejected" 
        details: Additional details (will be converted to JSON string for blocked_reason)
        session_id: Session identifier (default: "default")
        model: Model used (default: "aws_nova_lite")
    
    Returns:
        bool: True if successfully logged, False otherwise
    """
    try:
        logger = get_query_logger()
        
        # Convert details to string for database storage
        blocked_reason = None
        if details:
            import json
            blocked_reason = json.dumps(details)
        
        response_generated = (response_status == "completed")
        
        return logger.log_query(
            session_id=session_id,
            query_text=query,
            classification=classification,
            safety_score=safety_score,
            language=language,
            model=model,
            response_generated=response_generated,
            blocked_reason=blocked_reason
        )
    except Exception as e:
        print(f"Warning: Failed to log user query: {e}")
        return False

def log_user_query_detailed(
    session_id: str,
    query_text: str,
    classification: str,
    safety_score: float,
    language: str = "English",
    model: str = "unknown",
    response_generated: bool = True,
    blocked_reason: Optional[str] = None
) -> bool:
    """
    Detailed convenience function to log a user query (for direct database calls)
    
    Args:
        session_id: Unique session identifier
        query_text: The actual query text
        classification: 'on-topic', 'off-topic', or 'harmful'
        safety_score: Safety score between 0 and 1
        language: Query language (default: English)
        model: Model used for processing (default: unknown)
        response_generated: Whether a response was generated (default: True)
        blocked_reason: Reason for blocking if applicable
    
    Returns:
        bool: True if successfully logged, False otherwise
    """
    try:
        logger = get_query_logger()
        return logger.log_query(
            session_id=session_id,
            query_text=query_text,
            classification=classification,
            safety_score=safety_score,
            language=language,
            model=model,
            response_generated=response_generated,
            blocked_reason=blocked_reason
        )
    except Exception as e:
        print(f"Warning: Failed to log user query: {e}")
        return False

# Example usage:
if __name__ == "__main__":
    # Test the query logger
    logger = QueryLogger()
    
    # Log some sample queries
    test_queries = [
        {
            "session_id": "test_session_1",
            "query_text": "What are the effects of climate change on polar ice caps?",
            "classification": "on-topic",
            "safety_score": 0.95,
            "language": "English",
            "model": "aws_nova_lite",
            "response_generated": True
        },
        {
            "session_id": "test_session_2", 
            "query_text": "How do I bake a chocolate cake?",
            "classification": "off-topic",
            "safety_score": 0.85,
            "language": "English",
            "model": "aws_nova_lite",
            "response_generated": False
        },
        {
            "session_id": "test_session_3",
            "query_text": "[Harmful content detected]",
            "classification": "harmful",
            "safety_score": 0.1,
            "language": "English", 
            "model": "aws_nova_lite",
            "response_generated": False,
            "blocked_reason": "Inappropriate content"
        }
    ]
    
    for query in test_queries:
        success = logger.log_query(**query)
        print(f"Logged query: {success}")
    
    # Print statistics
    stats = logger.get_statistics()
    print(f"Statistics: {stats}")
    
    # Print recent queries
    recent = logger.get_recent_queries(limit=5)
    for classification, queries in recent.items():
        print(f"{classification}: {len(queries)} queries")