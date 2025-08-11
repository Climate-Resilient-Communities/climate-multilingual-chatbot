from typing import Dict, Any, List, Optional
from langchain.chains.base import Chain
from langchain.callbacks.manager import CallbackManagerForChainRun
from langchain_core.callbacks.manager import AsyncCallbackManagerForChainRun
from pydantic import Field, BaseModel
import logging
import time

logger = logging.getLogger(__name__)

class ChatbotResponse(BaseModel):
    success: bool
    response: str
    citations: List[str] = []
    faithfulness_score: float = 0.0
    processing_time: float = 0.0

class QueryProcessingChain(Chain):
    """Processes climate-related queries with LangSmith tracing."""
    
    chatbot: Any = Field(description="The chatbot instance to process queries")

    class Config:
        arbitrary_types_allowed = True

    @property
    def input_keys(self) -> List[str]:
        return ["query", "language_name"]

    @property
    def output_keys(self) -> List[str]:
        return ["success", "response", "citations", "faithfulness_score", "processing_time"]

    def _call(self, inputs: Dict[str, Any], run_manager: Optional[CallbackManagerForChainRun] = None) -> Dict[str, Any]:
        """Synchronous processing is not supported."""
        raise NotImplementedError("This chain only supports async calls")

    async def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, Any]:
        """Process a query through the complete pipeline."""
        query = inputs.get("query", "")
        language_name = inputs.get("language_name", "english")
        
        if not query:
            return {
                "success": False,
                "response": "No query provided",
                "citations": [],
                "faithfulness_score": 0.0,
                "processing_time": 0.0
            }
            
        logger.info(f"Processing query: {query}...")
        
        try:
            result = await self.chatbot._process_query_internal(
                query=query,
                language_name=language_name,
                run_manager=run_manager
            )
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating response: {error_msg}")
            return {
                "success": False,
                "response": error_msg,
                "citations": [],
                "faithfulness_score": 0.0,
                "processing_time": 0.0
            }

    async def _acall(self, inputs: Dict[str, Any], run_manager: Optional[AsyncCallbackManagerForChainRun] = None) -> Dict[str, Any]:
        """Process the query asynchronously with tracing."""
        start_time = time.time()
        try:
            if run_manager:
                await run_manager.on_text(
                    "Starting ClimateChat Query Processing"
                )
            
            logger.info(f"Processing query: {inputs['query'][:100]}...")
            
            # Process query through the chatbot
            result = await self.chatbot._process_query_internal(
                inputs["query"], 
                inputs["language_name"],
                run_manager
            )
            
            logger.debug(f"Raw result: {result}")
            
            # Convert to ChatbotResponse model for validation
            try:
                response = ChatbotResponse(**result)
            except Exception as e:
                logger.error(f"Failed to validate response: {str(e)}")
                return ChatbotResponse(
                    success=False,
                    response=f"Error validating response: {str(e)}",
                    citations=[],
                    faithfulness_score=0.0,
                    processing_time=time.time() - start_time
                ).dict()
            
            # Only log successful results
            if response.success:
                if run_manager:
                    await run_manager.on_text(
                        f"Successfully generated response with faithfulness score: {response.faithfulness_score}"
                    )
                logger.info(f"Successfully processed query in {time.time() - start_time:.2f}s")
            else:
                error_msg = f"Error generating response: {response.response}"
                if run_manager:
                    await run_manager.on_text(error_msg)
                logger.error(error_msg)
            
            return response.dict()
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in query processing: {error_msg}", exc_info=True)
            if run_manager:
                await run_manager.on_text(f"Error in processing: {error_msg}")
            
            return ChatbotResponse(
                success=False,
                response=f"Error processing query: {error_msg}",
                citations=[],
                faithfulness_score=0.0,
                processing_time=time.time() - start_time
            ).dict()