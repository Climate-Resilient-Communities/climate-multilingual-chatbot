#!/usr/bin/env python3
"""
Standalone admin API server for the climate chatbot dashboard.
This runs independently of the main application to avoid dependency conflicts.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# Add src to path for cost tracker import
sys.path.append('src')
try:
    from utils.cost_tracker import get_cost_tracker
except ImportError:
    print("Warning: Cost tracker not available. Analytics features will be limited.")
    get_cost_tracker = None

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Climate Chatbot Admin API", version="1.0.0")

# CORS configuration - environment-driven for security
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:9002,http://127.0.0.1:9002").split(",")
cors_origins = [origin.strip() for origin in cors_origins]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Environment-driven origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Admin password from environment
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if ADMIN_PASSWORD:
    print("✅ Admin password loaded from environment")
else:
    print("⚠️  Warning: ADMIN_PASSWORD not set in environment variables")

# Google Sheets configuration
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

def get_google_sheets_client():
    """Initialize and return Google Sheets client"""
    try:
        # Define the scope
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        # Use service account file (matches your .env configuration)
        if GOOGLE_SERVICE_ACCOUNT_FILE and os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
            creds = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scope)
        else:
            print(f"Google service account file not found: {GOOGLE_SERVICE_ACCOUNT_FILE}")
            return None
        
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
        
        # Count thumbs up and thumbs down from the Google Form format
        thumbs_up = 0
        thumbs_down = 0
        manual_entries = []
        
        # Category counters for thumbs feedback
        thumbs_up_categories = {
            "instructions": 0,      # Followed Instructions
            "comprehensive": 0,     # Comprehensive Answer
            "translation": 0,       # Good Translation
            "expected": 0,          # Response works as expected
            "other": 0             # Other
        }
        
        thumbs_down_categories = {
            "instructions": 0,      # Didn't follow instructions
            "no-response": 0,       # No Response Generated
            "unrelated": 0,         # Response Unrelated
            "translation": 0,       # Bad Translation
            "guard-filter": 0,      # Guard Filter Misclassified
            "other": 0             # Other
        }
        
        additional_feedback_comments = []
        
        for record in records:
            # The feedback type is stored in 'What type of feedback are you sharing?' column
            feedback_value = record.get('What type of feedback are you sharing?', '').lower()
            
            if 'thumbs up' in feedback_value or '👍' in feedback_value:
                thumbs_up += 1
                
                # Extract categories from the bug details field
                bug_details = record.get('If this is a bug, what were you trying to do when it happened? (N/A if not applicable)', '')
                if 'Categories:' in bug_details:
                    categories_text = bug_details.split('Categories:')[1].strip()
                    categories = [cat.strip() for cat in categories_text.split(',')]
                    for category in categories:
                        if category in thumbs_up_categories:
                            thumbs_up_categories[category] += 1
                
                # Extract additional feedback comment
                comment = record.get('Briefly describe your feedback', '').strip()
                if comment and comment not in ['thumbs_up', 'thumbs_down']:  # Allow test comments, filter automated ones
                    additional_feedback_comments.append({
                        "timestamp": record.get('Timestamp', ''),
                        "comment": comment,
                        "type": "positive"
                    })
                    
            elif 'thumbs down' in feedback_value or '👎' in feedback_value:
                thumbs_down += 1
                
                # Extract categories from the bug details field
                bug_details = record.get('If this is a bug, what were you trying to do when it happened? (N/A if not applicable)', '')
                if 'Categories:' in bug_details:
                    categories_text = bug_details.split('Categories:')[1].strip()
                    categories = [cat.strip() for cat in categories_text.split(',')]
                    for category in categories:
                        if category in thumbs_down_categories:
                            thumbs_down_categories[category] += 1
                
                # Extract additional feedback comment
                comment = record.get('Briefly describe your feedback', '').strip()
                if comment and comment not in ['thumbs_up', 'thumbs_down']:  # Allow test comments, filter automated ones
                    additional_feedback_comments.append({
                        "timestamp": record.get('Timestamp', ''),
                        "comment": comment,
                        "type": "negative"
                    })
            else:
                # Filter out old automated feedback entries - only include real manual form submissions
                # Skip entries that look like automated feedback (have feedback IDs or assistant message IDs)
                if (not feedback_value.startswith('fb_') and 
                    not record.get('Which language(s) were you using?', '').startswith('assistant_') and
                    record.get('Briefly describe your feedback', '') not in ['thumbs_up', 'thumbs_down']):
                    # This is a genuine manual form entry
                    manual_entries.append({
                        "timestamp": record.get('Timestamp', ''),
                        "feedback_type": record.get('What type of feedback are you sharing?', ''),
                        "language": record.get('Which language(s) were you using?', ''),
                        "description": record.get('Briefly describe your feedback', ''),
                        "bug_details": record.get('If this is a bug, what were you trying to do when it happened? (N/A if not applicable)', ''),
                        "evidence": record.get('If this is a bug, please share relevant conversation history (you can click download on the left panel) or screenshots when this bug occurs ', ''),
                        "usage_frequency": record.get('How often do you use the climate chatbot?', '')
                    })
        
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
            "manual_entries": manual_entries,
            "manual_entries_count": len(manual_entries),
            "category_breakdown": {
                "thumbs_up": thumbs_up_categories,
                "thumbs_down": thumbs_down_categories
            },
            "additional_feedback": additional_feedback_comments,
            "worksheet_title": worksheet.title,
            "last_updated": datetime.now().isoformat() + "Z"
        }
        
    except Exception as e:
        print(f"Error reading from Google Sheets: {e}")
        return None

@app.get("/")
async def root():
    return {"message": "Climate Chatbot Admin API", "status": "running"}

def get_feedback_analytics_data():
    """Get feedback analytics data without password protection (for internal use)"""
    # Try to get real data from Google Sheets
    sheets_data = read_feedback_from_sheets()
    
    if sheets_data:
        # Return real data from Google Sheets
        return {
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
            },
            "manual_feedback": {
                "entries": sheets_data["manual_entries"],
                "count": sheets_data["manual_entries_count"]
            },
            "category_breakdown": sheets_data["category_breakdown"],
            "additional_feedback": sheets_data["additional_feedback"]
        }
    else:
        # Fallback to mock data if Google Sheets is not available
        return {
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
            },
            "manual_feedback": {
                "entries": [],
                "count": 0
            },
            "category_breakdown": {
                "thumbs_up": {"instructions": 0, "comprehensive": 0, "translation": 0, "expected": 0, "other": 0},
                "thumbs_down": {"instructions": 0, "no-response": 0, "unrelated": 0, "translation": 0, "guard-filter": 0, "other": 0}
            },
            "additional_feedback": []
        }

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
            },
            "manual_feedback": {
                "entries": sheets_data["manual_entries"],
                "count": sheets_data["manual_entries_count"]
            },
            "category_breakdown": sheets_data["category_breakdown"],
            "additional_feedback": sheets_data["additional_feedback"]
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
            },
            "manual_feedback": {
                "entries": [],
                "count": 0
            },
            "category_breakdown": {
                "thumbs_up": {"instructions": 0, "comprehensive": 0, "translation": 0, "expected": 0, "other": 0},
                "thumbs_down": {"instructions": 0, "no-response": 0, "unrelated": 0, "translation": 0, "guard-filter": 0, "other": 0}
            },
            "additional_feedback": []
        }
    
    # Add cost analytics to any data (real or fallback) - using approximate calculations
    try:
        # Try to get actual interaction count from Redis first, fallback to feedback count
        total_interactions = analytics_data["summary"]["total_feedback"]
        
        # Try multiple sources for interaction count
        try:
            # Method 1: Try Redis
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            redis_total = redis_client.get("analytics:total_interactions")
            if redis_total:
                total_interactions = max(int(redis_total), total_interactions)
                print(f"Using Redis interaction count: {total_interactions}")
            else:
                raise Exception("No Redis data")
        except Exception:
            # Method 2: Try file-based analytics
            try:
                analytics_file = "analytics_data.json"
                if os.path.exists(analytics_file):
                    with open(analytics_file, 'r') as f:
                        file_data = json.load(f)
                    file_total = file_data.get("total_interactions", 0)
                    total_interactions = max(file_total, total_interactions)
                    print(f"Using file-based interaction count: {total_interactions}")
                else:
                    print(f"No file analytics found, using feedback count: {total_interactions}")
            except Exception as file_err:
                print(f"Could not read analytics file: {file_err}, using feedback count: {total_interactions}")
        
        # Approximate cost estimates per interaction (based on typical usage)
        # Nova: ~500 input tokens + 150 output tokens per query
        # Pinecone: ~1 vector search per query
        # Cohere: Used occasionally for reranking
        
        nova_cost_per_query = ((500 / 1_000_000) * 0.60) + ((150 / 1_000_000) * 2.40)  # ~$0.00066
        pinecone_cost_per_query = (1 / 1_000_000) * 0.20  # ~$0.0000002
        cohere_cost_per_query = ((300 / 1_000_000) * 5.00) + ((50 / 1_000_000) * 15.00)  # ~$0.0023
        
        # Estimate that 80% use Nova, 100% use Pinecone, 20% use Cohere
        estimated_nova_cost = total_interactions * 0.8 * nova_cost_per_query
        estimated_pinecone_cost = total_interactions * pinecone_cost_per_query
        estimated_cohere_cost = total_interactions * 0.2 * cohere_cost_per_query
        
        total_estimated_cost = estimated_nova_cost + estimated_pinecone_cost + estimated_cohere_cost
        
        # Create mock interaction breakdown based on feedback patterns
        interaction_breakdown = {}
        if total_interactions > 0:
            # Estimate based on typical patterns
            interaction_breakdown["climate_response"] = int(total_interactions * 0.7)
            interaction_breakdown["vector_search"] = total_interactions
            interaction_breakdown["translation"] = int(total_interactions * 0.3)
            interaction_breakdown["on-topic"] = int(total_interactions * 0.85)
            interaction_breakdown["off-topic"] = int(total_interactions * 0.15)
            interaction_breakdown["harmful"] = max(1, int(total_interactions * 0.02))
        
        # Language breakdown (approximate based on typical usage)
        language_breakdown = {
            "English": int(total_interactions * 0.4),
            "Spanish": int(total_interactions * 0.25),
            "French": int(total_interactions * 0.15),
            "Portuguese": int(total_interactions * 0.1),
            "Chinese": int(total_interactions * 0.1)
        }
        
        # Generate mock recent interactions
        recent_interactions = []
        for i in range(min(10, total_interactions)):
            recent_interactions.append({
                "timestamp": datetime.now().isoformat(),
                "session_id": f"session_{i+1:03d}",
                "model": "aws_nova_lite" if i % 5 != 0 else "cohere_command_a",
                "language": ["English", "Spanish", "French"][i % 3],
                "query_type": ["climate_response", "vector_search", "translation"][i % 3],
                "cost": nova_cost_per_query if i % 5 != 0 else cohere_cost_per_query,
                "processing_time": 1200 + (i * 100),
                "cache_hit": i % 3 == 0
            })
        
        analytics_data["cost_analytics"] = {
            "total_cost": round(total_estimated_cost, 6),
            "total_interactions": total_interactions,
            "model_breakdown": {
                "aws_nova_lite": {
                    "interactions": int(total_interactions * 0.8),
                    "cost": round(estimated_nova_cost, 6),
                    "input_tokens": int(total_interactions * 0.8 * 500),
                    "output_tokens": int(total_interactions * 0.8 * 150)
                },
                "cohere_command_a": {
                    "interactions": int(total_interactions * 0.2),
                    "cost": round(estimated_cohere_cost, 6),
                    "input_tokens": int(total_interactions * 0.2 * 300),
                    "output_tokens": int(total_interactions * 0.2 * 50)
                },
                "pinecone_operations": {
                    "interactions": total_interactions,
                    "cost": round(estimated_pinecone_cost, 6),
                    "input_tokens": 0,
                    "output_tokens": 0
                }
            },
            "cost_summary": {
                "cohere_cost": round(estimated_cohere_cost, 6),
                "nova_cost": round(estimated_nova_cost, 6),
                "pinecone_cost": round(estimated_pinecone_cost, 6)
            },
            "recent_interactions": recent_interactions,
            "interaction_breakdown": interaction_breakdown,
            "language_breakdown": language_breakdown
        }
        
        print(f"Generated cost analytics: Total cost ${total_estimated_cost:.6f} for {total_interactions} interactions")
        
    except Exception as e:
        print(f"Warning: Could not generate cost analytics: {e}")
        analytics_data["cost_analytics"] = {
            "total_cost": 0.0,
            "total_interactions": 0,
            "model_breakdown": {},
            "cost_summary": {"cohere_cost": 0.0, "nova_cost": 0.0, "pinecone_cost": 0.0},
            "recent_interactions": [],
            "interaction_breakdown": {},
            "language_breakdown": {}
        }
    
    return analytics_data

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "admin-api"}

@app.get("/analytics/costs")
async def get_cost_analytics():
    """Get comprehensive cost analytics from Google Sheets"""
    try:
        if not get_cost_tracker:
            # Fallback: return mock data if cost tracker not available
            return {
                "total_cost": 0.0,
                "total_interactions": 0,
                "model_breakdown": {},
                "daily_costs": {},
                "cost_summary": {
                    "cohere_cost": 0.0,
                    "nova_cost": 0.0,
                    "pinecone_cost": 0.0
                }
            }
        
        cost_tracker = get_cost_tracker()
        analytics_data = cost_tracker.get_analytics_from_sheets()
        
        return {
            "total_cost": analytics_data.get("total_cost", 0.0),
            "total_interactions": analytics_data.get("total_interactions", 0),
            "model_breakdown": analytics_data.get("model_breakdown", {}),
            "language_breakdown": analytics_data.get("language_breakdown", {}),
            "interaction_breakdown": analytics_data.get("interaction_breakdown", {}),
            "daily_costs": analytics_data.get("daily_costs", {}),
            "cost_summary": analytics_data.get("cost_summary", {
                "cohere_cost": 0.0,
                "nova_cost": 0.0,
                "pinecone_cost": 0.0
            })
        }
        
    except Exception as e:
        print(f"Error getting cost analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost analytics: {str(e)}")

@app.get("/analytics/interactions")
async def get_interaction_logs(limit: int = Query(50, description="Number of recent interactions to return")):
    """Get recent interaction logs"""
    try:
        if not get_cost_tracker:
            return {"interactions": [], "total_count": 0}
        
        cost_tracker = get_cost_tracker()
        analytics_data = cost_tracker.get_analytics_from_sheets()
        recent_interactions = analytics_data.get("recent_interactions", [])
        
        # Limit the results
        limited_interactions = recent_interactions[:limit]
        
        return {
            "interactions": limited_interactions,
            "total_count": analytics_data.get("total_interactions", 0)
        }
        
    except Exception as e:
        print(f"Error getting interaction logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get interaction logs: {str(e)}")

@app.get("/analytics/dashboard")
async def get_dashboard_analytics():
    """Get comprehensive dashboard analytics combining feedback and cost data"""
    try:
        # Get existing feedback data
        feedback_data = get_feedback_analytics_data()
        
        # Get cost analytics
        cost_analytics = {}
        if get_cost_tracker:
            cost_tracker = get_cost_tracker()
            cost_analytics = cost_tracker.get_analytics_from_sheets()
        
        # Combine both datasets
        dashboard_data = {
            **feedback_data,  # Existing feedback analytics
            "cost_analytics": {
                "total_cost": cost_analytics.get("total_cost", 0.0),
                "total_interactions": cost_analytics.get("total_interactions", 0),
                "model_breakdown": cost_analytics.get("model_breakdown", {}),
                "cost_summary": cost_analytics.get("cost_summary", {
                    "cohere_cost": 0.0,
                    "nova_cost": 0.0,
                    "pinecone_cost": 0.0
                }),
                "recent_interactions": cost_analytics.get("recent_interactions", [])[:10],  # Last 10 for dashboard
                "interaction_breakdown": cost_analytics.get("interaction_breakdown", {}),
                "language_breakdown": cost_analytics.get("language_breakdown", {})
            }
        }
        
        return dashboard_data
        
    except Exception as e:
        print(f"Error getting dashboard analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard analytics: {str(e)}")

@app.get("/analytics/test-increment")
async def test_increment_interactions():
    """Test endpoint to manually increment interaction counter"""
    try:
        import json
        analytics_file = "analytics_data.json"
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Load existing data
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"total_interactions": 0, "daily": {}}
        
        # Increment counters
        data["total_interactions"] = data.get("total_interactions", 0) + 1
        if today not in data["daily"]:
            data["daily"][today] = 0
        data["daily"][today] += 1
        
        # Save updated data
        with open(analytics_file, 'w') as f:
            json.dump(data, f)
        
        return {
            "success": True,
            "message": "Interaction count incremented",
            "total_interactions": data["total_interactions"],
            "daily_interactions": data["daily"][today]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to increment: {str(e)}")

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