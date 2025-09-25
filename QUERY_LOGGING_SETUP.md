# Query Logging System - Quick Setup Guide

## ✅ SQLite Setup Complete!

Great news! SQLite is already built into Python, so no additional installation is needed. The setup has been completed successfully.

## 📁 Files Created

- **`setup_query_logging.py`** - Initial setup and database creation
- **`test_query_logging.py`** - System validation and testing  
- **`start_admin_dashboard.py`** - Quick start script for admin dashboard
- **`admin_analytics.db`** - SQLite database with sample data (24KB)
- **`src/utils/query_logger.py`** - Utility for logging queries from your main app
- **`QUERY_LOGGING_INTEGRATION.md`** - Complete integration guide

## 🚀 Quick Start (3 Steps)

### 1. Verify Setup (Already Done!)
```bash
python test_query_logging.py
```
✅ All tests passed - Your system is ready!

### 2. Start Admin Dashboard
```bash
python start_admin_dashboard.py
```
This will:
- Check all dependencies  
- Show you the dashboard URL and password
- Start the admin API server on port 8001

### 3. View Dashboard
Open in browser: `http://localhost:8001/admin/analytics?password=demo_password_123`

## 📊 What You'll See

### Enhanced Dashboard Features:
- **Safety & Sentiment Section**: Grouped On-Topic, Off-Topic, Harmful metrics with percentages
- **Query Content Details**: Three scrollable columns showing actual user messages:
  - 🟢 **On-Topic**: Climate-related queries with high safety scores
  - 🟠 **Off-Topic**: Non-climate queries (cooking, pizza, etc.)  
  - 🔴 **Harmful**: Blocked content with safety violations

### Sample Data Included:
- 5 on-topic climate queries (English & Spanish)
- 2 off-topic queries (cooking, pizza)
- 2 harmful queries (filtered content)

## 🔗 Integration with Your Main App

To start logging real queries from your climate chatbot:

1. **Import the logger** in your main processing files:
   ```python
   from utils.query_logger import log_user_query
   ```

2. **Add logging calls** after query processing:
   ```python
   # For climate-related queries
   log_user_query(
       session_id=session_id,
       query_text=user_query,
       classification="on-topic", 
       safety_score=0.95,
       language=detected_language,
       model="aws_nova_lite",
       response_generated=True
   )
   
   # For blocked content
   log_user_query(
       session_id=session_id,
       query_text="[Content filtered]",
       classification="harmful",
       safety_score=0.1, 
       language=detected_language,
       model="aws_nova_lite",
       response_generated=False,
       blocked_reason="Safety violation"
   )
   ```

3. **See complete guide**: Check `QUERY_LOGGING_INTEGRATION.md` for detailed integration steps

## 🛠️ Troubleshooting

### Database Issues
```bash
# Test database connectivity
python -c "import sqlite3; print('SQLite version:', sqlite3.sqlite_version)"
```

### Server Won't Start
```bash
# Check if port 8001 is in use
netstat -an | findstr 8001
```

### No Data in Dashboard
- Restart server: `python admin_api_server.py`
- Repopulate sample data: Run `setup_query_logging.py` again

## 🔧 Configuration

### Environment Variables
```bash
# Optional: Set custom admin password
set ADMIN_PASSWORD=your_secure_password_here
```

### Database Location
- File: `admin_analytics.db` (SQLite)
- Location: Project root directory
- Size: ~24KB with sample data

## 📈 Next Steps

1. **Test the dashboard** - Start server and explore the interface
2. **Review integration guide** - See how to add logging to your main app
3. **Customize as needed** - Modify queries, add fields, adjust UI

Your query logging system is now fully operational! 🎉