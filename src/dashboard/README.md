# Climate Chatbot Admin Dashboard

This directory contains all the dashboard-related components for monitoring and analytics of the climate chatbot application.

## Directory Structure

```
src/dashboard/
├── README.md                    # This file
├── api/                        # Admin API server
│   └── admin_server.py         # FastAPI server for dashboard data
├── database/                   # Database utilities
│   └── query_logger.py         # Query logging utility
├── setup/                      # Setup and initialization scripts
│   ├── setup_query_logging.py # Database setup and testing
│   ├── cleanup_test_data.py    # Clean test data from database
│   └── prepare_real_queries.py # Migration script for real data
└── test_*.py                   # Test files for dashboard components
```

## Components

### 🖥️ Admin API Server (`api/admin_server.py`)

- **Purpose**: FastAPI server providing analytics data and admin endpoints
- **Port**: 8001 (configurable)
- **Authentication**: Admin password via environment variable
- **Features**:
  - Real-time query analytics
  - Cost breakdown per model
  - Safety & sentiment analysis
  - Query content details with classifications

### 🗄️ Query Logger (`database/query_logger.py`)

- **Purpose**: Utility for logging user queries with classifications
- **Features**:
  - Thread-safe database operations
  - Query classification (on-topic, off-topic, harmful)
  - Safety score tracking
  - Multi-language support
  - Model usage tracking

### 🔧 Setup Scripts (`setup/`)

- **`setup_query_logging.py`**: Initialize database and test all components
- **`cleanup_test_data.py`**: Remove sample data for production
- **`prepare_real_queries.py`**: Prepare system for real query integration

## Quick Start

### 1. Initialize Dashboard

```bash
# From project root
python src/dashboard/setup/setup_query_logging.py
```

### 2. Start Admin Server

```bash
# From project root
python start_admin_dashboard.py
# OR directly:
python src/dashboard/api/admin_server.py
```

### 3. Access Dashboard

- **URL**: http://localhost:8001/admin/analytics
- **Password**: Check your `.env` file for `ADMIN_PASSWORD`

## Integration with Main Application

The query logger is integrated with the main climate chatbot application (`src/main_nova.py`) to automatically log:

1. **On-Topic Queries**: Successful climate-related questions
2. **Off-Topic Queries**: Non-climate questions that are rejected
3. **Harmful Queries**: Content blocked by safety guardrails

### Integration Points in `main_nova.py`:

- `process_input_guards()`: Logs harmful and off-topic content
- `process_query()`: Logs successful climate queries and rejections
- Cached responses: Logs cache hits as successful queries

## Environment Variables

Required environment variables in `.env`:

```bash
ADMIN_PASSWORD=your_secure_password_here
CORS_ORIGINS=http://localhost:9002,http://127.0.0.1:9002
```

Optional:

```bash
DB_PATH=admin_analytics.db  # Database file path
```

## API Endpoints

### Analytics Endpoints

- `GET /admin/analytics?password={admin_password}` - Main dashboard data
- `GET /admin/queries/detailed?password={admin_password}` - Query breakdowns
- `GET /health` - Health check

### Management Endpoints

- `POST /admin/queries/store` - Store new query data
- `POST /admin/queries/populate-sample` - Add sample data (development only)

## Database Schema

The system uses SQLite with the following main table:

```sql
CREATE TABLE detailed_queries (
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
);
```

## Testing

Run dashboard tests:

```bash
# From project root
python src/dashboard/test_admin_api.py
python src/dashboard/test_query_logging.py
python src/dashboard/test_enhanced_tracking.py
```

## Troubleshooting

### Common Issues

1. **Database not found**: Run `setup_query_logging.py`
2. **Import errors**: Check Python path and virtual environment
3. **Permission denied**: Check file permissions and admin password
4. **Port already in use**: Kill existing processes or change port

### Logs and Debugging

- Check terminal output when starting the admin server
- Database operations include error handling with warnings
- Use `test_enhanced_tracking.py` to verify real-time tracking

## Security Notes

- Admin password should be strong and kept secure
- Database contains user query data - handle appropriately
- CORS origins should be restricted in production
- Consider HTTPS for production deployment

## Future Enhancements

- [ ] Real-time dashboard updates via WebSocket
- [ ] Export functionality for analytics data
- [ ] User session tracking and analysis
- [ ] Integration with cloud databases
- [ ] Advanced filtering and search capabilities
