#!/usr/bin/env python3
"""
Standalone admin API server for the climate chatbot dashboard.
This runs independently of the main application to avoid dependency conflicts.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from typing import Dict, Any
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Climate Chatbot Admin API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin password from environment
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
print(ADMIN_PASSWORD)

# Google Sheets configuration
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")

def get_google_sheets_client():
    """Initialize and return Google Sheets client"""
    try:
        if not GOOGLE_SERVICE_ACCOUNT_KEY:
            raise Exception("GOOGLE_SERVICE_ACCOUNT_KEY not found in environment")
        
        # Parse the service account key
        service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_KEY)
        
        # Define the scope
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        # Create credentials
        creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
        
        # Authorize and create client
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error creating Google Sheets client: {e}")
        return None

def read_feedback_from_sheets():
    """Read feedback data from Google Sheets"""
    try:
        client = get_google_sheets_client()
        if not client:
            return None
        
        # Open the sheet
        sheet = client.open_by_key(GOOGLE_SHEETS_ID)
        worksheet = sheet.sheet1  # Use the first worksheet
        
        # Get all records
        records = worksheet.get_all_records()
        
        # Count thumbs up and thumbs down
        thumbs_up = 0
        thumbs_down = 0
        
        for record in records:
            feedback_value = record.get('feedback', '').lower()
            if feedback_value == 'thumbs_up':
                thumbs_up += 1
            elif feedback_value == 'thumbs_down':
                thumbs_down += 1
        
        total_feedback = thumbs_up + thumbs_down
        positive_percentage = (thumbs_up / total_feedback * 100) if total_feedback > 0 else 0
        negative_percentage = (thumbs_down / total_feedback * 100) if total_feedback > 0 else 0
        
        return {
            "total_feedback": total_feedback,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "positive_percentage": round(positive_percentage, 1),
            "negative_percentage": round(negative_percentage, 1),
            "unrated": 0,
            "worksheet_title": worksheet.title,
            "last_updated": datetime.now().isoformat() + "Z"
        }
        
    except Exception as e:
        print(f"Error reading from Google Sheets: {e}")
        return None

@app.get("/")
async def root():
    return {"message": "Climate Chatbot Admin API", "status": "running"}

@app.get("/admin/analytics")
async def get_analytics(password: str = Query(..., description="Admin password")):
    """
    Get analytics data for the admin dashboard.
    Requires admin password for authentication.
    """
    
    # Verify admin password
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    # Try to get real data from Google Sheets
    sheets_data = read_feedback_from_sheets()
    
    if sheets_data:
        # Return real data from Google Sheets
        analytics_data = {
            "summary": {
                "total_feedback": sheets_data["total_feedback"],
                "thumbs_up": sheets_data["thumbs_up"],
                "thumbs_down": sheets_data["thumbs_down"],
                "positive_percentage": sheets_data["positive_percentage"],
                "negative_percentage": sheets_data["negative_percentage"],
                "unrated": sheets_data["unrated"]
            },
            "sheet_info": {
                "sheets_id": GOOGLE_SHEETS_ID,
                "worksheet_title": sheets_data["worksheet_title"],
                "last_updated": sheets_data["last_updated"]
            }
        }
    else:
        # Fallback to mock data if Google Sheets is not available
        analytics_data = {
            "summary": {
                "total_feedback": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "positive_percentage": 0,
                "negative_percentage": 0,
                "unrated": 0
            },
            "sheet_info": {
                "sheets_id": GOOGLE_SHEETS_ID or "Not configured",
                "worksheet_title": "Google Sheets not available",
                "last_updated": datetime.now().isoformat() + "Z"
            }
        }
    
    return analytics_data

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "admin-api"}

if __name__ == "__main__":
    print("🚀 Starting Climate Chatbot Admin API...")
    print(f"📊 Admin dashboard will be available at: http://localhost:8001/admin/analytics")
    print(f"🔑 Admin password: {ADMIN_PASSWORD}")
    print("="*60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # Different port to avoid conflicts
        reload=False,  # Disable reload to avoid warnings
        log_level="info"
    )