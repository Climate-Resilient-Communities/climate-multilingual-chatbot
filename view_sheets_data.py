#!/usr/bin/env python3
"""
Script to view all data from the Google Sheets form responses
"""

import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()

def get_google_sheets_client():
    """Initialize Google Sheets client"""
    try:
        creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
        
        if not os.path.exists(creds_file):
            print(f"❌ Credentials file not found: {creds_file}")
            return None
        
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        credentials = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(credentials)
        
        print(f"✅ Successfully connected to Google Sheets")
        return client
        
    except Exception as e:
        print(f"❌ Error connecting to Google Sheets: {e}")
        return None

def display_sheets_data():
    """Display all data from the Google Sheets"""
    try:
        # Get the Google Sheets client
        client = get_google_sheets_client()
        if not client:
            return
        
        # Get the sheet ID from environment
        sheets_id = os.getenv("GOOGLE_SHEETS_ID")
        if not sheets_id:
            print("❌ GOOGLE_SHEETS_ID not found in environment")
            return
        
        print(f"📊 Opening Google Sheet: {sheets_id}")
        
        # Open the spreadsheet
        sheet = client.open_by_key(sheets_id)
        print(f"📋 Sheet title: {sheet.title}")
        
        # Get the first worksheet
        worksheet = sheet.get_worksheet(0)
        print(f"📄 Worksheet title: {worksheet.title}")
        
        # Get all records
        records = worksheet.get_all_records()
        print(f"📝 Total records found: {len(records)}")
        
        if len(records) == 0:
            print("\n🔍 No data found in the sheet")
            
            # Let's also check the raw values
            print("\n🔍 Checking raw values...")
            all_values = worksheet.get_all_values()
            print(f"Raw rows: {len(all_values)}")
            
            if all_values:
                print("\nFirst few rows:")
                for i, row in enumerate(all_values[:5]):
                    print(f"Row {i+1}: {row}")
            
            return
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(records)
        
        print(f"\n📊 GOOGLE SHEETS DATA TABLE")
        print("=" * 80)
        
        # Display column information
        print(f"Columns ({len(df.columns)}): {list(df.columns)}")
        print("=" * 80)
        
        # Display the data
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 50)
        
        print(df.to_string(index=True))
        
        print("=" * 80)
        
        # Count feedback types
        if 'What type of feedback are you sharing?' in df.columns:
            feedback_col = 'What type of feedback are you sharing?'
            feedback_counts = df[feedback_col].value_counts()
            print(f"\n📈 Feedback Type Breakdown:")
            for feedback_type, count in feedback_counts.items():
                print(f"  {feedback_type}: {count}")
        
        # Show languages used
        if 'Which language(s) were you using?' in df.columns:
            lang_col = 'Which language(s) were you using?'
            lang_counts = df[lang_col].value_counts()
            print(f"\n🌍 Languages Used:")
            for lang, count in lang_counts.items():
                print(f"  {lang}: {count}")
        
        print(f"\n✅ Data successfully retrieved from Google Sheets!")
        
    except Exception as e:
        print(f"❌ Error reading Google Sheets data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Google Sheets Data Viewer")
    print("=" * 50)
    display_sheets_data()