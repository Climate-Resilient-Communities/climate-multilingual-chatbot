#!/usr/bin/env python3
"""
Simple Azure Blob connectivity test.

Usage:
  - Ensure your .env or environment provides either:
      BLOB_CONNSTR (preferred)  OR  BLOB_ACCOUNT_NAME + BLOB_KEY
  - Optionally set CHAT_BLOB_CONTAINER (default: chatlogs)

This script will:
  1) Upload a small test blob to the container
  2) Download it back and print the content
"""
from __future__ import annotations

import os
import sys
from uuid import uuid4
from datetime import datetime


def _ensure_deps() -> None:
    try:
        import azure.storage.blob  # noqa: F401
    except Exception:
        print("Installing azure-storage-blob…", flush=True)
        import subprocess

        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "azure-storage-blob>=12.19.0",
        ])

    try:
        import dotenv  # noqa: F401
    except Exception:
        print("Installing python-dotenv…", flush=True)
        import subprocess

        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "python-dotenv>=1.0.0",
        ])


def _dequote(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1]
    return v


def _first_env(*names: str) -> str | None:
    for name in names:
        raw = os.environ.get(name)
        if raw is not None and raw.strip():
            return _dequote(raw)
    return None


def main() -> int:
    _ensure_deps()

    from dotenv import load_dotenv
    from azure.storage.blob import BlobServiceClient

    # Load .env from project root if present
    load_dotenv(dotenv_path=".env", override=True)

    conn_str = _first_env(
        "BLOB_CONNSTR",
        "Azure_blob",
        "AZURE_BLOB_CONNSTR",
        "AZURE_STORAGE_CONNECTION_STRING",
    )
    account_name = _first_env(
        "BLOB_ACCOUNT_NAME",
        "BLOB_ACCOUNT",
        "AZURE_STORAGE_ACCOUNT",
        "AZURE_ACCOUNT_NAME",
    )
    account_key = _first_env(
        "BLOB_KEY",
        "AZURE_BLOB_KEY",
        "AZURE_STORAGE_KEY",
        "STORAGE_ACCOUNT_KEY",
    )
    container_name = _first_env("CHAT_BLOB_CONTAINER") or "chatlogs"

    svc = None
    mode = None
    try:
        if conn_str:
            svc = BlobServiceClient.from_connection_string(conn_str)
            mode = "connection_string"
        elif account_name and account_key:
            svc = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=account_key,
            )
            mode = "account_key"
        else:
            print(
                "ERROR: No Azure credentials found. Set BLOB_CONNSTR (preferred) or "
                "BLOB_ACCOUNT_NAME + BLOB_KEY in .env or environment."
            )
            return 2

        cc = svc.get_container_client(container_name)
        try:
            cc.create_container()
        except Exception:
            pass

        blob_name = f"cli-test-{uuid4()}.txt"
        data = f"hello from test_blob at {datetime.utcnow().isoformat()} via {mode}"
        cc.upload_blob(blob_name, data.encode("utf-8"), overwrite=True)

        downloaded = cc.download_blob(blob_name).readall().decode("utf-8")
        print("OK: Uploaded and verified round-trip")
        print("container:", container_name)
        print("blob:", blob_name)
        print("content:", downloaded)
        return 0
    except Exception as e:
        print("ERROR:", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())


