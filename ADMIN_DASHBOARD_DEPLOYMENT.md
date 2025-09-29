# Admin Dashboard Deployment Guide

## Overview

The Climate Chatbot includes an integrated admin dashboard for monitoring query analytics, safety metrics, and cost tracking. This guide covers production deployment of the dashboard components.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Main API       │    │ Dashboard API   │
│   Dashboard     │◄──►│   (Port 8000)    │◄──►│ (Port 8001)     │
│                 │    │   Proxy Endpoint │    │ SQLite Database │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Components

### 1. Dashboard API Server (`src/dashboard/api/admin_server.py`)

- **Purpose**: Serves comprehensive analytics data from SQLite database
- **Port**: 8001 (configurable via `DASHBOARD_PORT`)
- **Database**: `admin_analytics.db` (auto-created)
- **Authentication**: Environment variable `ADMIN_PASSWORD`

### 2. Main API Proxy (`src/webui/api/routers/admin_simple.py`)

- **Purpose**: Proxies dashboard requests from frontend to dashboard server
- **Endpoint**: `/api/v1/admin/analytics`
- **Fallback**: Provides minimal data when dashboard server unavailable

### 3. Query Logger (`src/utils/query_logger.py`)

- **Purpose**: Logs real-time queries from main application to analytics database
- **Integration**: Called from `src/main_nova.py`

## Production Deployment

### Environment Variables

```bash
# Required
ADMIN_PASSWORD=your_secure_password_here

# Optional - Dashboard server configuration
DASHBOARD_HOST=localhost          # Default: localhost
DASHBOARD_PORT=8001              # Default: 8001
ENVIRONMENT=production           # Set for production optimizations

# Optional - Google Sheets integration
GOOGLE_SHEETS_ID=your_sheets_id
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/credentials.json
```

### Deployment Steps

1. **Install Dependencies**

   ```bash
   pip install fastapi uvicorn httpx python-dotenv sqlite3
   ```

2. **Set Environment Variables**

   ```bash
   # Create .env file or set system environment variables
   echo "ADMIN_PASSWORD=your_secure_password" >> .env
   echo "ENVIRONMENT=production" >> .env
   ```

3. **Start Dashboard Server**

   ```bash
   # Option 1: Using startup script (recommended)
   python start_admin_dashboard.py

   # Option 2: Direct server start
   python src/dashboard/api/admin_server.py

   # Option 3: Using backward compatibility wrapper
   python admin_api_server.py
   ```

4. **Start Main API** (if needed)
   ```bash
   uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000
   ```

### Production Considerations

#### Security

- Use strong `ADMIN_PASSWORD` (recommended: 20+ characters)
- Consider firewall rules for port 8001
- Enable HTTPS in production (configure reverse proxy)
- Regularly rotate admin password

#### Performance

- SQLite database handles thousands of queries efficiently
- Consider moving to PostgreSQL for high-volume deployments
- Monitor disk space for `admin_analytics.db`

#### Monitoring

- Dashboard server logs to console (redirect to file in production)
- Health check endpoint: `http://localhost:8001/health`
- Monitor HTTP 503 responses from proxy (indicates dashboard server issues)

#### Scaling

- Dashboard server is stateless (except SQLite database)
- Can run multiple instances with shared database
- Consider read replicas for high-traffic deployments

## API Endpoints

### Dashboard Server (Port 8001)

- `GET /admin/analytics?password=<pass>` - Main analytics data
- `GET /admin/queries/detailed?password=<pass>` - Detailed query breakdown
- `POST /admin/queries/store` - Store new query data
- `GET /health` - Health check

### Main API Proxy (Port 8000)

- `GET /api/v1/admin/analytics?password=<pass>` - Proxied analytics data

## Troubleshooting

### Common Issues

**"Dashboard server unavailable"**

- Check if dashboard server is running on port 8001
- Verify `ADMIN_PASSWORD` is set correctly
- Check firewall/network connectivity

**"Invalid admin credentials"**

- Verify `ADMIN_PASSWORD` matches in both .env and request
- Check for trailing spaces in password
- Ensure .env file is loaded properly

**Empty analytics data**

- Verify query logger is integrated in main application
- Check `admin_analytics.db` exists and has data
- Review application logs for integration errors

### Logs and Debugging

```bash
# Enable debug logging (development only)
export ENVIRONMENT=development

# Check dashboard server status
curl -f http://localhost:8001/health

# Test proxy endpoint
curl "http://localhost:8000/api/v1/admin/analytics?password=your_password"
```

## Database Schema

The analytics database (`admin_analytics.db`) contains:

```sql
-- Query analytics with classifications
CREATE TABLE detailed_queries (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    query_text TEXT NOT NULL,
    classification TEXT NOT NULL,  -- 'on-topic', 'off-topic', 'harmful'
    safety_score REAL,
    language TEXT,
    model TEXT,
    response_generated BOOLEAN,
    blocked_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Integration with Main Application

To enable real-time analytics, ensure query logging is integrated:

```python
# In your main application (src/main_nova.py)
from src.utils.query_logger import log_user_query

# After processing each query
log_user_query(
    query_text=user_input,
    classification="on-topic",  # or "off-topic", "harmful"
    safety_score=0.95,
    language="english",
    model="aws_nova_lite",
    response_generated=True
)
```

## Maintenance

- **Database Cleanup**: Archive old queries periodically
- **Log Rotation**: Rotate server logs in production
- **Updates**: Test dashboard updates in staging environment
- **Backups**: Regular backup of `admin_analytics.db`

---

For additional support or advanced configuration, refer to the source code documentation in `src/dashboard/`.
