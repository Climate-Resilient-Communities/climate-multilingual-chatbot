#!/usr/bin/env python3
"""
Quick start script for the query logging admin dashboard.
This script starts the admin API server with proper error handling.
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

def check_dependencies():
    """Check if all required components are available"""
    print("🔍 Checking system dependencies...")
    
    # Check if database exists
    if not Path("admin_analytics.db").exists():
        print("❌ Database not found. Please run setup_query_logging.py first")
        return False
    
    # Check if admin API server exists
    if not Path("admin_api_server.py").exists():
        print("❌ Admin API server not found")
        return False
    
    # Check admin password
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        print("⚠️  ADMIN_PASSWORD not set in environment")
        print("   Using default password for demo purposes")
        os.environ["ADMIN_PASSWORD"] = "demo_password_123"
        admin_password = "demo_password_123"
    
    print(f"✅ All dependencies ready")
    print(f"🔑 Admin password: {admin_password}")
    return True

def start_admin_server():
    """Start the admin API server"""
    try:
        print("🚀 Starting admin API server...")
        print("   Port: 8001")
        print("   Host: localhost")
        print("   Press Ctrl+C to stop")
        print("-" * 50)
        
        # Start the server
        process = subprocess.run([
            sys.executable, "admin_api_server.py"
        ], check=False)
        
        return process.returncode == 0
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        return True
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return False

def show_dashboard_info():
    """Show information about accessing the dashboard"""
    admin_password = os.getenv("ADMIN_PASSWORD", "demo_password_123")
    
    print("\n" + "=" * 60)
    print("📊 ADMIN DASHBOARD ACCESS INFORMATION")
    print("=" * 60)
    print(f"🌐 Dashboard URL: http://localhost:8001/admin/analytics")
    print(f"🔑 Admin Password: {admin_password}")
    print(f"📝 Full URL with password: http://localhost:8001/admin/analytics?password={admin_password}")
    print("\n📋 Available Endpoints:")
    print("   • GET  /admin/analytics - Main dashboard data")
    print("   • GET  /admin/queries/detailed - Detailed query breakdown")
    print("   • POST /admin/queries/store - Store new query data")
    print("   • GET  /health - Health check")
    print("\n💡 Tips:")
    print("   • The dashboard will show sample data from the setup")
    print("   • Use the query logger utility to add real data from your app")
    print("   • See QUERY_LOGGING_INTEGRATION.md for integration guide")
    print("=" * 60)

def main():
    """Main startup function"""
    print("🎯 Climate Chatbot - Query Logging Admin Dashboard")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Startup failed. Please fix the issues above.")
        return False
    
    # Show access information
    show_dashboard_info()
    
    # Ask user if they want to start the server
    try:
        choice = input("\n❓ Start the admin server now? (y/n): ").lower().strip()
        if choice not in ['y', 'yes']:
            print("👋 Startup cancelled. You can run this script again anytime.")
            return True
    except KeyboardInterrupt:
        print("\n👋 Startup cancelled.")
        return True
    
    # Start server
    success = start_admin_server()
    
    if success:
        print("\n✅ Server session completed successfully")
    else:
        print("\n❌ Server encountered issues")
    
    return success

if __name__ == "__main__":
    main()