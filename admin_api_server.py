#!/usr/bin/env python3
"""
Backward compatibility wrapper for admin_api_server.py
This file maintains compatibility for any scripts that still reference the old filename.
"""

# Import and run the renamed admin server
if __name__ == "__main__":
    from src.dashboard.api.admin_server import app
    import uvicorn
    import os
    
    print("🔄 Loading admin server from new location: src/dashboard/api/admin_server.py")
    print("✅ Admin password loaded from environment")
    print("🚀 Starting Climate Chatbot Admin API...")
    print("📂 Initializing database...")
    print("📊 Admin dashboard will be available at: http://localhost:8001/admin/analytics")
    admin_password = os.getenv("ADMIN_PASSWORD")
    print(f"🔑 Admin password: {admin_password}")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)