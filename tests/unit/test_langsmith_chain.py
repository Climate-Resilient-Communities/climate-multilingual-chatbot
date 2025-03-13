import os
import sys
from pathlib import Path
import pytest
from typing import Dict, Any, List
from langchain.chains.base import Chain
from langchain.callbacks.manager import CallbackManagerForChainRun
from langsmith import Client
from langchain.callbacks.tracers import LangChainTracer
from langchain_core.tracers import ConsoleCallbackHandler

class SimpleQueryChain(Chain):
    """A simple chain for testing LangSmith integration."""
    
    @property
    def input_keys(self) -> List[str]:
        """Returns the input keys."""
        return ["query"]

    @property
    def output_keys(self) -> List[str]:
        """Returns the output keys."""
        return ["response"]

    def _call(self, inputs: Dict[str, Any], run_manager: CallbackManagerForChainRun = None) -> Dict[str, Any]:
        """Processes the inputs and returns a response."""
        if run_manager:
            run_manager.on_text("Processing query...")
        
        # Simple echo response for testing
        response = f"Processed: {inputs['query']}"
        
        return {"response": response}

@pytest.fixture
def langsmith_client():
    """Initialize LangSmith client."""
    return Client()

@pytest.fixture
def simple_chain():
    """Create a simple chain instance."""
    return SimpleQueryChain()

def test_chain_execution(langsmith_client, simple_chain):
    """Test executing the chain with LangSmith tracing."""
    # Set up callbacks
    tracer = LangChainTracer(
        project_name="test-climate-chat"
    )
    callbacks = [tracer, ConsoleCallbackHandler()]
    
    # Execute chain
    result = simple_chain(
        {"query": "test query"},
        callbacks=callbacks
    )
    
    # Verify the response
    assert "response" in result
    assert result["response"] == "Processed: test query"

def test_chain_async_execution(langsmith_client, simple_chain):
    """Test executing the chain asynchronously with LangSmith tracing."""
    import asyncio
    
    async def run_async_test():
        # Set up callbacks
        tracer = LangChainTracer(
            project_name="test-climate-chat"
        )
        callbacks = [tracer, ConsoleCallbackHandler()]
        
        # Execute chain
        result = await simple_chain.acall(
            {"query": "test query"},
            callbacks=callbacks
        )
        
        # Verify the response
        assert "response" in result
        assert result["response"] == "Processed: test query"
    
    # Run the async test
    asyncio.run(run_async_test())