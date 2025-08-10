#!/usr/bin/env python3
"""
Test just the blob persistence function from app_nova.py without importing the whole app.
"""

import os
import sys
import json
from datetime import datetime
from uuid import uuid4

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env", override=True)
except ImportError:
    pass

# Copy the blob function from app_nova.py to test it independently
def _env(*names):
    """Get environment variable by trying multiple names."""
    for name in names:
        value = os.environ.get(name)
        if value is not None:
            value = value.strip().strip('"').strip("'")
            if value:
                return value
    return None

def _persist_record_to_blob(record_str: str) -> None:
    """Append the record to an Azure Blob if connection is configured."""
    try:
        # Get Azure connection details
        conn_str = (
            _env("BLOB_CONNSTR")
            or _env("Azure_blob")
            or _env("AZURE_BLOB_CONNSTR")
            or _env("AZURE_STORAGE_CONNECTION_STRING")
        )
        container_name = _env("CHAT_BLOB_CONTAINER") or "chatlogs"
        blob_prefix = _env("CHAT_BLOB_PREFIX") or "interactions"
        session_id = "test-app-function-" + str(uuid4())
        blob_name = f"{blob_prefix}/{session_id}.jsonl"

        from azure.storage.blob import BlobClient, BlobServiceClient

        if conn_str:
            # Use connection string
            svc = BlobServiceClient.from_connection_string(conn_str)
        else:
            # Fall back to account name + key
            account_name = (
                _env("BLOB_ACCOUNT_NAME")
                or _env("BLOB_ACCOUNT")
                or _env("AZURE_STORAGE_ACCOUNT")
                or _env("AZURE_ACCOUNT_NAME")
            )
            account_key = (
                _env("BLOB_KEY")
                or _env("AZURE_BLOB_KEY")
                or _env("AZURE_STORAGE_KEY")
                or _env("STORAGE_ACCOUNT_KEY")
            )
            if not (account_name and account_key):
                return
            account_url = f"https://{account_name}.blob.core.windows.net"
            svc = BlobServiceClient(account_url=account_url, credential=account_key)

        # Ensure container exists
        try:
            cc = svc.get_container_client(container_name)
            cc.create_container()
        except Exception:
            pass

        # Get blob client
        blob_client = cc.get_blob_client(blob_name)

        # For JSONL append functionality: read existing, append new record, upload
        existing_content = ""
        try:
            existing_content = blob_client.download_blob().readall().decode()
        except Exception:
            # Blob doesn't exist yet, that's fine
            pass

        # Append the new record
        new_content = existing_content + record_str + "\n"
        blob_client.upload_blob(new_content.encode("utf-8"), overwrite=True)
        
        return session_id  # Return session ID for verification
        
    except Exception as e:
        print(f"[FEEDBACK] Blob persist failed: {e}")
        raise

if __name__ == "__main__":
    print("Testing app blob function independently...")
    
    # Create a test record
    test_record = {
        "session_id": "will-be-replaced",
        "timestamp": datetime.now().isoformat(),
        "message_index": 1,
        "language": "en",
        "user_query": "Independent test query",
        "assistant_response": "This is a test response from the app function",
        "feedback": "up",
        "citations": ["test.pdf"]
    }
    
    record_str = json.dumps(test_record, ensure_ascii=False)
    
    try:
        session_id = _persist_record_to_blob(record_str)
        print(f"✓ Successfully persisted record to blob")
        print(f"✓ Session ID: {session_id}")
        
        # Verify the record was uploaded
        from azure.storage.blob import BlobServiceClient
        
        conn_str = _env("BLOB_CONNSTR", "Azure_blob", "AZURE_BLOB_CONNSTR", "AZURE_STORAGE_CONNECTION_STRING")
        if conn_str:
            service = BlobServiceClient.from_connection_string(conn_str)
        else:
            account_name = _env("BLOB_ACCOUNT_NAME", "BLOB_ACCOUNT", "AZURE_STORAGE_ACCOUNT", "AZURE_ACCOUNT_NAME")
            account_key = _env("BLOB_KEY", "AZURE_BLOB_KEY", "AZURE_STORAGE_KEY", "STORAGE_ACCOUNT_KEY")
            account_url = f"https://{account_name}.blob.core.windows.net"
            service = BlobServiceClient(account_url=account_url, credential=account_key)
        
        container_name = _env("CHAT_BLOB_CONTAINER") or "chatlogs"
        blob_prefix = _env("CHAT_BLOB_PREFIX") or "interactions"
        blob_name = f"{blob_prefix}/{session_id}.jsonl"
        
        container_client = service.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        # Download and verify
        downloaded = blob_client.download_blob().readall().decode()
        if "Independent test query" in downloaded:
            print(f"✓ Verification successful! Found test record in blob: {blob_name}")
            print(f"✓ Content: {downloaded.strip()}")
            print("\n🎉 App blob function is working correctly!")
        else:
            print(f"❌ Verification failed: test record not found in blob")
            print(f"Downloaded content: {downloaded}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
