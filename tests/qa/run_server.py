"""Launch the real FastAPI app (serving the built frontend) with QA boundary fakes.

Usage:  python -m tests.qa.run_server [port]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault("COHERE_API_KEY", "qa-dummy")
os.environ.setdefault("PINECONE_API_KEY", "qa-dummy")
os.environ.setdefault("TAVILY_API_KEY", "qa-dummy")
os.environ.setdefault("HF_API_TOKEN", "qa-dummy")
os.environ.setdefault("HF_TOKEN", "qa-dummy")
os.environ.setdefault("DISABLE_RATE_LIMIT", "1")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")


def main():
    from tests.qa import boundary_fakes
    boundary_fakes.install()

    import uvicorn
    from src.webui.api.main import app

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
