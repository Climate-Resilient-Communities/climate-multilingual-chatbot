#!/usr/bin/env python3
"""
Test the updated feedback counting logic
"""

import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_feedback_counting():
    """Test the new feedback counting logic"""
    try:
        # Connect to Google Sheets
        creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Get the sheet
        sheets_id = os.getenv("GOOGLE_SHEETS_ID")
        sheet = client.open_by_key(sheets_id)
        worksheet = sheet.get_worksheet(0)
        
        # Get all records
        records = worksheet.get_all_records()
        
        print(f"📊 Testing Updated Feedback Counting Logic")
        print("=" * 60)
        print(f"Total records: {len(records)}")
        print()
        
        # Count using the NEW logic
        thumbs_up = 0
        thumbs_down = 0
        other_feedback = 0
        
        print("🔍 Analyzing each record:")
        for i, record in enumerate(records, 1):
            feedback_value = record.get('What type of feedback are you sharing?', '').lower()
            print(f"Row {i}: '{record.get('What type of feedback are you sharing?', 'N/A')}'")
            
            if 'thumbs up' in feedback_value or '👍' in feedback_value:
                thumbs_up += 1
                print(f"  ✅ Counted as THUMBS UP")
            elif 'thumbs down' in feedback_value or '👎' in feedback_value:
                thumbs_down += 1
                print(f"  ❌ Counted as THUMBS DOWN")
            else:
                other_feedback += 1
                print(f"  ℹ️  Counted as OTHER FEEDBACK")
            print()
        
        total_feedback = thumbs_up + thumbs_down
        positive_percentage = (thumbs_up / total_feedback * 100) if total_feedback > 0 else 0
        negative_percentage = (thumbs_down / total_feedback * 100) if total_feedback > 0 else 0
        
        print("📈 FINAL RESULTS:")
        print("=" * 60)
        print(f"👍 Thumbs Up: {thumbs_up}")
        print(f"👎 Thumbs Down: {thumbs_down}")
        print(f"📊 Total Thumbs Feedback: {total_feedback}")
        print(f"📝 Other Feedback: {other_feedback}")
        print(f"📊 Positive Rate: {positive_percentage:.1f}%")
        print(f"📊 Negative Rate: {negative_percentage:.1f}%")
        print("=" * 60)
        
        if total_feedback > 0:
            print("✅ SUCCESS: Your admin dashboard should now show these numbers!")
        else:
            print("⚠️  No thumbs feedback found yet")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_feedback_counting()