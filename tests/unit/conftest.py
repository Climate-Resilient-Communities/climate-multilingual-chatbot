"""
Unit test conftest — ensures LangSmith trace() works without a live API key
and provides shared helpers for LLM-eval tests.

When LANGSMITH_API_KEY is not set, langsmith.trace() may return None,
which crashes any `with trace(name=...):` block.  This autouse fixture
patches it globally for every unit test so the code under test never
hits the NoneType context-manager error.
"""

import json
import re
import pytest
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def _noop_trace(*args, **kwargs):
    """No-op context manager that replaces langsmith.trace when unconfigured."""
    yield


@pytest.fixture(autouse=True)
def _patch_langsmith_trace():
    """Auto-patch langsmith.trace for all unit tests."""
    with patch("langsmith.trace", _noop_trace):
        yield


def parse_llm_json(text: str) -> dict:
    """Parse JSON from LLM output, stripping markdown code fences if present.

    LLMs often return JSON wrapped in ```json ... ``` blocks.
    This helper strips that wrapper before parsing.
    """
    cleaned = text.strip()
    # Strip ```json ... ``` or ``` ... ```
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned)
    return json.loads(cleaned)
