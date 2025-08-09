#!/usr/bin/env python3
import os
import sys


def _ensure_deps() -> None:
    try:
        import azure.storage.blob  # noqa: F401
    except Exception:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "azure-storage-blob>=12.19.0"])  # noqa: E501
    try:
        import dotenv  # noqa: F401
    except Exception:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "python-dotenv>=1.0.0"])  # noqa: E501


def _dequote(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1]
    return v


def main() -> int:
    _ensure_deps()
    from dotenv import load_dotenv
    from azure.storage.blob import BlobServiceClient

    load_dotenv(dotenv_path=".env", override=True)

    # Resolve credentials
    conn = _dequote(
        os.environ.get("BLOB_CONNSTR")
        or os.environ.get("Azure_blob")
        or os.environ.get("AZURE_BLOB_CONNSTR")
        or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    )
    container = _dequote(os.environ.get("CHAT_BLOB_CONTAINER")) or "chatlogs"
    prefix = _dequote(os.environ.get("CHAT_BLOB_PREFIX")) or "interactions"

    if not conn:
        print("ERROR: BLOB_CONNSTR (or equivalent) not found in env/.env")
        return 2

    svc = BlobServiceClient.from_connection_string(conn)
    cc = svc.get_container_client(container)

    # List available interaction blobs
    print(f"Listing blobs under {container}/{prefix}/ …")
    try:
        for blob in cc.list_blobs(name_starts_with=f"{prefix}/"):
            print(blob.name)
    except Exception as e:
        print("ERROR listing blobs:", e)

    # Determine session id to fetch
    session_id = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        session_id = sys.argv[1].strip()
    else:
        # Default to the last session we saw locally in earlier checks
        session_id = "e5b4c791-9507-447e-a524-2b440f05b7fb"

    blob_name = f"{prefix}/{session_id}.jsonl"
    print(f"\nDownloading: {container}/{blob_name}")
    try:
        data = cc.get_blob_client(blob_name).download_blob().readall().decode("utf-8")
        print("\n--- Blob Contents ---\n")
        print(data)
    except Exception as e:
        print("ERROR downloading blob:", e)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


