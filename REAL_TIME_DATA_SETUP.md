# Real-Time Dashboard Data Setup Guide

## Current Status ✅

Your system is **properly configured** for real-time data collection:

- ✅ **Database exists**: `admin_analytics.db` with 8 queries
- ✅ **Query logger working**: Successfully logs new queries  
- ✅ **Main API running**: Port 8000 (PID 27108)
- ✅ **Dashboard API running**: Port 8001 (PID 33348)
- ✅ **Integration complete**: `main_nova.py` calls query logger

## To Get Real-Time Data 🔄

### 1. **Use Your Chat Interface**
Your main application needs to process actual user queries to generate real-time data:

```bash
# If using the web interface
http://localhost:8000

# If using direct API calls
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What causes climate change?", "session_id": "test123"}'
```

### 2. **Send Test Queries**
Each query you send through the interface will:
1. Get processed by `main_nova.py`
2. Be classified as on-topic/off-topic/harmful
3. Get logged to `admin_analytics.db`
4. Appear in your dashboard in real-time

### 3. **Watch Real-Time Updates**
- **Dashboard URL**: http://localhost:8001/admin/analytics?password=mlcc_2025
- **Proxy URL**: http://localhost:8000/api/v1/admin/analytics?password=mlcc_2025

Each new query will update:
- Vector search counts (should be ~100%)
- Query Content Details with real queries
- Safety & Sentiment metrics
- Cost analytics

## Test Real-Time Flow 🧪

Run this test to verify end-to-end real-time data flow:

```bash
# 1. Check current count
python -c "
import sqlite3
conn = sqlite3.connect('admin_analytics.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM detailed_queries')
print(f'Current count: {cursor.fetchone()[0]}')
conn.close()
"

# 2. Send a test query to your main API
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do solar panels help reduce carbon emissions?",
    "session_id": "realtime_test",
    "language": "english"
  }'

# 3. Check if count increased
python -c "
import sqlite3
conn = sqlite3.connect('admin_analytics.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM detailed_queries')
print(f'New count: {cursor.fetchone()[0]}')
cursor.execute('SELECT query_text, classification FROM detailed_queries ORDER BY timestamp DESC LIMIT 1')
latest = cursor.fetchone()
print(f'Latest: {latest[1]} - {latest[0][:50]}...')
conn.close()
"

# 4. Check dashboard shows new data
curl "http://localhost:8001/admin/analytics?password=mlcc_2025" | grep -A5 "interaction_breakdown"
```

## Current Database Content 📊

Your database currently has:
```
Total queries: 8
- on-topic: 3 (climate-related questions)
- off-topic: 2 (non-climate questions) 
- harmful: 2 (safety violations)
- Plus 1 test query from verification
```

## Frontend Integration 🖥️

If you have a React/Next.js frontend running, it should automatically:
1. Connect to `http://localhost:8000/api/v1/admin/analytics`
2. Get proxied to the dashboard server
3. Display real-time data from `admin_analytics.db`
4. Update when new queries are processed

## Troubleshooting 🔧

**If data isn't updating:**

1. **Check main app is processing queries**:
   ```bash
   # Look for query processing logs
   grep -i "query" logs/backend.log
   ```

2. **Verify query logger is being called**:
   ```bash
   # Add debug print to main_nova.py temporarily
   print(f"Logging query: {query[:50]}...")
   ```

3. **Test database connection**:
   ```bash
   python test_real_time_logging.py
   ```

4. **Check dashboard API**:
   ```bash
   curl -f http://localhost:8001/health
   ```

## Expected Real-Time Behavior 📈

When working correctly:
- **Each chat query** → New database entry
- **Dashboard refreshes** → Shows updated counts
- **Vector search** → Always ~100% (every query uses vectors)
- **Query details** → Shows actual user questions, not samples

---

**Your system is ready for real-time data!** Just start using the chat interface and watch the dashboard update with live analytics. 🚀