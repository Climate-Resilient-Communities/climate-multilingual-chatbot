#!/usr/bin/env python3
"""
Unit test for Azure Blob Storage integration with chat logging.
Tests both connection and actual chat log upload functionality.
"""

import os
import sys
import json
import tempfile
from datetime import datetime
from uuid import uuid4

# Ensure dependencies
try:
    from azure.storage.blob import BlobServiceClient, BlobClient
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "azure-storage-blob>=12.19.0"])
    from azure.storage.blob import BlobServiceClient, BlobClient

try:
    from dotenv import load_dotenv
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "python-dotenv>=1.0.0"])
    from dotenv import load_dotenv

# Load environment
load_dotenv(dotenv_path=".env", override=True)

def get_env(*names):
    """Get environment variable by trying multiple names."""
    for name in names:
        value = os.environ.get(name)
        if value is not None:
            value = value.strip().strip('"').strip("'")
            if value:
                return value
    return None

def test_azure_connection():
    """Test Azure Blob Storage connection."""
    print("=== Testing Azure Connection ===")
    
    # Get connection details
    conn_str = get_env("BLOB_CONNSTR", "Azure_blob", "AZURE_BLOB_CONNSTR", "AZURE_STORAGE_CONNECTION_STRING")
    account_name = get_env("BLOB_ACCOUNT_NAME", "BLOB_ACCOUNT", "AZURE_STORAGE_ACCOUNT", "AZURE_ACCOUNT_NAME")
    account_key = get_env("BLOB_KEY", "AZURE_BLOB_KEY", "AZURE_STORAGE_KEY", "STORAGE_ACCOUNT_KEY")
    
    if not conn_str and not (account_name and account_key):
        print("❌ No Azure credentials found. Set BLOB_CONNSTR or BLOB_ACCOUNT_NAME + BLOB_KEY")
        return False
    
    try:
        if conn_str:
            print("✓ Using connection string")
            service = BlobServiceClient.from_connection_string(conn_str)
        else:
            print("✓ Using account name + key")
            account_url = f"https://{account_name}.blob.core.windows.net"
            service = BlobServiceClient(account_url=account_url, credential=account_key)
        
        # Test container access
        container_name = get_env("CHAT_BLOB_CONTAINER") or "chatlogs"
        container_client = service.get_container_client(container_name)
        
        # Ensure container exists
        try:
            container_client.create_container()
            print(f"✓ Created container: {container_name}")
        except Exception:
            print(f"✓ Container already exists: {container_name}")
        
        # Test basic blob operation
        test_blob_name = f"test/connection-test-{uuid4()}.txt"
        test_content = f"Connection test at {datetime.utcnow().isoformat()}"
        
        blob_client = container_client.get_blob_client(test_blob_name)
        blob_client.upload_blob(test_content.encode(), overwrite=True)
        print(f"✓ Uploaded test blob: {test_blob_name}")
        
        # Verify download
        downloaded = blob_client.download_blob().readall().decode()
        if downloaded == test_content:
            print("✓ Round-trip verification successful")
        else:
            print("❌ Round-trip verification failed")
            return False
        
        # Clean up test blob
        blob_client.delete_blob()
        print("✓ Cleaned up test blob")
        
        return True
        
    except Exception as e:
        print(f"❌ Azure connection failed: {e}")
        return False

def test_chat_log_upload():
    """Test uploading a sample chat log in the same format as the app."""
    print("\n=== Testing Chat Log Upload ===")
    
    # Get connection details (same as app logic)
    conn_str = get_env("BLOB_CONNSTR", "Azure_blob", "AZURE_BLOB_CONNSTR", "AZURE_STORAGE_CONNECTION_STRING")
    account_name = get_env("BLOB_ACCOUNT_NAME", "BLOB_ACCOUNT", "AZURE_STORAGE_ACCOUNT", "AZURE_ACCOUNT_NAME")
    account_key = get_env("BLOB_KEY", "AZURE_BLOB_KEY", "AZURE_STORAGE_KEY", "STORAGE_ACCOUNT_KEY")
    
    container_name = get_env("CHAT_BLOB_CONTAINER") or "chatlogs"
    blob_prefix = get_env("CHAT_BLOB_PREFIX") or "interactions"
    test_session_id = f"test-{uuid4()}"
    blob_name = f"{blob_prefix}/{test_session_id}.jsonl"
    
    try:
        # Create blob client (using correct Azure SDK)
        if conn_str:
            print("✓ Using connection string for chat log test")
            service = BlobServiceClient.from_connection_string(conn_str)
        else:
            print("✓ Using account name + key for chat log test")
            account_url = f"https://{account_name}.blob.core.windows.net"
            service = BlobServiceClient(account_url=account_url, credential=account_key)
        
        # Ensure container exists
        container_client = service.get_container_client(container_name)
        try:
            container_client.create_container()
        except Exception:
            pass
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Create sample chat interaction records
        sample_records = [
            {
                "session_id": test_session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message_index": 1,
                "language": "en",
                "user_query": "What is climate change?",
                "assistant_response": "Climate change refers to long-term shifts in global temperatures and weather patterns...",
                "feedback": "none",
                "citations": ["source1.pdf", "source2.pdf"]
            },
            {
                "session_id": test_session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message_index": 3,
                "language": "en",
                "user_query": "How can I help?",
                "assistant_response": "There are many ways to help combat climate change...",
                "feedback": "up",
                "citations": ["source3.pdf"]
            }
        ]
        
        # For JSONL append functionality, we'll read existing content, append new records, then upload
        existing_content = ""
        try:
            existing_content = blob_client.download_blob().readall().decode()
        except Exception:
            # Blob doesn't exist yet, that's fine
            pass
        
        # Create the full content with new records
        all_content = existing_content
        for i, record in enumerate(sample_records):
            record_str = json.dumps(record, ensure_ascii=False)
            all_content += record_str + "\n"
            print(f"✓ Prepared record {i+1}")
        
        # Upload the complete content
        blob_client.upload_blob(all_content.encode("utf-8"), overwrite=True)
        print(f"✓ Uploaded complete JSONL to: {blob_name}")
        
        # Verify upload by downloading
        downloaded_data = blob_client.download_blob().readall().decode()
        lines = downloaded_data.strip().split('\n')
        
        if len(lines) == len(sample_records):
            print(f"✓ Successfully uploaded {len(lines)} chat log records")
            
            # Verify content
            for i, line in enumerate(lines):
                parsed = json.loads(line)
                expected = sample_records[i]
                if parsed["session_id"] == expected["session_id"] and parsed["message_index"] == expected["message_index"]:
                    print(f"✓ Record {i+1} verification passed")
                else:
                    print(f"❌ Record {i+1} verification failed")
                    return False
            
            print(f"✓ Chat log test successful! Blob: {container_name}/{blob_name}")
            print(f"Session ID: {test_session_id}")
            return True
        else:
            print(f"❌ Expected {len(sample_records)} records, got {len(lines)}")
            return False
            
    except Exception as e:
        print(f"❌ Chat log upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_blob_function():
    """Test the actual blob function from app_nova.py"""
    print("\n=== Testing App Blob Function ===")
    
    try:
        # Import the function from app_nova.py
        sys.path.insert(0, 'src/webui')
        from app_nova import _persist_record_to_blob
        
        # Create a test record
        test_record = {
            "session_id": f"app-test-{uuid4()}",
            "timestamp": datetime.utcnow().isoformat(),
            "message_index": 1,
            "language": "en",
            "user_query": "Test from app function",
            "assistant_response": "This is a test response",
            "feedback": "none",
            "citations": []
        }
        
        record_str = json.dumps(test_record, ensure_ascii=False)
        
        # Test the function
        _persist_record_to_blob(record_str)
        print("✓ App blob function executed without errors")
        
        # Verify the record was uploaded
        container_name = get_env("CHAT_BLOB_CONTAINER") or "chatlogs"
        blob_prefix = get_env("CHAT_BLOB_PREFIX") or "interactions"
        session_id = test_record["session_id"]
        blob_name = f"{blob_prefix}/{session_id}.jsonl"
        
        conn_str = get_env("BLOB_CONNSTR", "Azure_blob", "AZURE_BLOB_CONNSTR", "AZURE_STORAGE_CONNECTION_STRING")
        if conn_str:
            service = BlobServiceClient.from_connection_string(conn_str)
        else:
            account_name = get_env("BLOB_ACCOUNT_NAME", "BLOB_ACCOUNT", "AZURE_STORAGE_ACCOUNT", "AZURE_ACCOUNT_NAME")
            account_key = get_env("BLOB_KEY", "AZURE_BLOB_KEY", "AZURE_STORAGE_KEY", "STORAGE_ACCOUNT_KEY")
            account_url = f"https://{account_name}.blob.core.windows.net"
            service = BlobServiceClient(account_url=account_url, credential=account_key)
        
        container_client = service.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        # Download and verify
        downloaded = blob_client.download_blob().readall().decode()
        if test_record["user_query"] in downloaded:
            print(f"✓ App function test record found in blob: {blob_name}")
            return True
        else:
            print(f"❌ App function test record not found in blob")
            return False
            
    except Exception as e:
        print(f"❌ App blob function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Azure Blob Storage Integration Test")
    print("=" * 50)
    
    # Run all tests
    connection_ok = test_azure_connection()
    upload_ok = test_chat_log_upload()
    app_function_ok = test_app_blob_function()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Connection Test: {'✓ PASS' if connection_ok else '❌ FAIL'}")
    print(f"Chat Log Upload: {'✓ PASS' if upload_ok else '❌ FAIL'}")
    print(f"App Function Test: {'✓ PASS' if app_function_ok else '❌ FAIL'}")
    
    if all([connection_ok, upload_ok, app_function_ok]):
        print("\n🎉 All tests PASSED! Azure integration is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests FAILED. Check the output above for details.")
        sys.exit(1)
