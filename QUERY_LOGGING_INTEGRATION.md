# Query Logging Integration Guide

This guide explains how to integrate detailed query logging into your climate chatbot application for enhanced admin analytics.

## Overview

The query logging system captures detailed information about user interactions, including:

- Query text and classification (on-topic, off-topic, harmful)
- Safety scores and language detection
- Model usage and response generation status
- Blocking reasons for harmful content

## Files Added/Modified

### 1. Dashboard Frontend (`src/webui/app/src/app/admin/dashboard/page.tsx`)

- **Enhanced Safety & Sentiment section** with better visual grouping
- **New Query Content Details section** showing actual query messages by category
- **Scrollable interface** for browsing queries with metadata

### 2. Admin API Server (`admin_api_server.py`)

- **Database initialization** for SQLite storage
- **New endpoints** for storing and retrieving detailed queries
- **Enhanced analytics endpoint** with detailed query data

### 3. Query Logger Utility (`src/utils/query_logger.py`)

- **Standalone utility** for logging queries from main application
- **Thread-safe database operations**
- **Convenient logging functions**

## Integration Steps

### Step 1: Install Dependencies

```bash
# Ensure SQLite3 is available (usually built into Python)
pip install sqlite3  # If needed
```

### Step 2: Import Query Logger in Your Main Application

In your main chatbot processing file (e.g., `src/models/gen_response_nova.py` or similar):

```python
from utils.query_logger import log_user_query
```

### Step 3: Add Logging Calls

#### For On-Topic Climate Queries

```python
# After determining the query is climate-related and generating a response
log_user_query(
    session_id=session_id,  # Your session ID
    query_text=user_query,  # Original user query
    classification="on-topic",
    safety_score=0.95,  # High safety score for clean climate queries
    language=detected_language,
    model="aws_nova_lite",  # Or whatever model you're using
    response_generated=True
)
```

#### For Off-Topic Queries

```python
# When query is not climate-related but safe
log_user_query(
    session_id=session_id,
    query_text=user_query,
    classification="off-topic",
    safety_score=0.85,  # Good safety score but not climate-related
    language=detected_language,
    model=current_model,
    response_generated=False  # Usually don't generate responses for off-topic
)
```

#### For Harmful/Blocked Queries

```python
# When content is blocked by safety guardrails
log_user_query(
    session_id=session_id,
    query_text="[Content filtered]",  # Don't store actual harmful text
    classification="harmful",
    safety_score=0.15,  # Low safety score
    language=detected_language,
    model=current_model,
    response_generated=False,
    blocked_reason="Inappropriate content detected"
)
```

### Step 4: Integration Points in Your Pipeline

Identify key points in your processing pipeline to add logging:

#### A. Query Classification Stage

```python
# In your query router/classifier
def classify_and_process_query(query, session_id, language):
    # Your existing classification logic
    classification = determine_classification(query)
    safety_score = get_safety_score(query)

    # Log the classification
    log_user_query(
        session_id=session_id,
        query_text=query,
        classification=classification,
        safety_score=safety_score,
        language=language,
        model=get_current_model(),
        response_generated=classification == "on-topic"
    )

    # Continue with your existing logic
    if classification == "on-topic":
        return generate_climate_response(query)
    else:
        return handle_off_topic_or_harmful(query)
```

#### B. Safety Guardrail Integration

```python
# In your input guardrail/safety check
def check_input_safety(query, session_id):
    safety_result = your_safety_check(query)

    if not safety_result.is_safe:
        # Log harmful content
        log_user_query(
            session_id=session_id,
            query_text="[Content filtered]",
            classification="harmful",
            safety_score=safety_result.score,
            language=detect_language(query),
            model="safety_filter",
            response_generated=False,
            blocked_reason=safety_result.reason
        )
        return False, "Content blocked for safety reasons"

    return True, None
```

### Step 5: Start Admin API Server

```bash
# Start the enhanced admin API server with query logging support
python admin_api_server.py
```

### Step 6: Populate Sample Data (Optional)

For testing purposes, you can populate sample queries:

```bash
# Call the sample population endpoint
curl -X POST "http://localhost:8001/admin/queries/populate-sample?password=YOUR_ADMIN_PASSWORD"
```

## Dashboard Features

After integration, your admin dashboard will show:

### Enhanced Safety & Sentiment Section

- **Grouped metrics** for On-Topic, Off-Topic, and Harmful content
- **Visual separation** from other interaction metrics
- **Percentage calculations** for each category

### Query Content Details Section

- **Three columns** showing actual queries by classification
- **Scrollable lists** with timestamps and metadata
- **Safety scores** and blocking reasons
- **Session IDs** for tracking
- **Language and model information**

## Database Schema

The system creates a SQLite database (`admin_analytics.db`) with:

```sql
CREATE TABLE detailed_queries (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    query_text TEXT NOT NULL,
    classification TEXT CHECK (classification IN ('on-topic', 'off-topic', 'harmful')),
    safety_score REAL NOT NULL,
    language TEXT NOT NULL,
    model TEXT NOT NULL,
    response_generated BOOLEAN NOT NULL,
    blocked_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### Store Query Details

```http
POST /admin/queries/store?password=ADMIN_PASSWORD
Content-Type: application/json

{
    "session_id": "sess_123",
    "query_text": "Climate query text",
    "classification": "on-topic",
    "safety_score": 0.95,
    "language": "English",
    "model": "aws_nova_lite",
    "response_generated": true
}
```

### Get Detailed Queries

```http
GET /admin/queries/detailed?password=ADMIN_PASSWORD
```

Returns:

```json
{
    "detailed_queries": {
        "on_topic": [...],
        "off_topic": [...],
        "harmful": [...]
    },
    "statistics": {
        "on_topic": 42,
        "off_topic": 8,
        "harmful": 2
    },
    "total_stored": 52
}
```

## Security Considerations

1. **Harmful Content**: Actual harmful query text is never stored - only filtered placeholders
2. **Admin Authentication**: All endpoints require admin password
3. **Local Storage**: Database is stored locally, not transmitted
4. **Query Truncation**: Long queries are truncated to prevent storage issues

## Monitoring and Maintenance

- **Database Size**: Monitor `admin_analytics.db` size for large deployments
- **Cleanup**: Consider periodic cleanup of old queries
- **Backup**: Include database in backup procedures
- **Performance**: Database operations are optimized with indexes

## Troubleshooting

### Database Issues

```python
# Test database connectivity
from src.utils.query_logger import QueryLogger
logger = QueryLogger()
stats = logger.get_statistics()
print(f"Database working: {len(stats) >= 0}")
```

### Logging Failures

```python
# Check logging with minimal example
success = log_user_query(
    session_id="test",
    query_text="test query",
    classification="on-topic",
    safety_score=0.9
)
print(f"Logging works: {success}")
```

This integration provides comprehensive query tracking while maintaining security and performance standards.
