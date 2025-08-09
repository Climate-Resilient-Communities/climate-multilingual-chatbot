import os
import logging
import json
from typing import List, Dict, Tuple, Any, Optional, Union
from src.models.nova_flow import BedrockModel
from src.models.cohere_flow import CohereModel
from src.models.redis_cache import ClimateCache
from src.models.system_messages import CLIMATE_SYSTEM_MESSAGE
import time
from langsmith import traceable
from src.models.title_normalizer import normalize_title

logger = logging.getLogger(__name__)

class UnifiedResponseGenerator:
    """Unified interface for generating responses using either Nova or Cohere models."""
    
    def __init__(self):
        """Initialize both model clients."""
        self.nova_model = BedrockModel()
        self.cohere_model = CohereModel()
        logger.info("✓ Unified Response Generator initialized")

    def _doc_preprocessing(self, docs: List[Dict]) -> List[Dict]:
        """Prepare documents for processing (unified for both models)."""
        documents = []
        logger.debug(f"Processing {len(docs)} documents")
        
        for doc in docs:
            try:
                # Extract required fields
                title = normalize_title(doc.get('title', ''), doc.get('section_title', ''), doc.get('url', []))
                content = doc.get('content', '')  # Primary content field
                if not content:
                    content = doc.get('chunk_text', '')  # Fallback content field
                    
                # Get URL(s)
                url = doc.get('url', [])
                if isinstance(url, list) and url:
                    url = url[0]
                elif isinstance(url, str):
                    url = url
                else:
                    url = ''
                    
                # Validation
                if not title or not content:
                    logger.warning(f"Missing required fields - Title: {bool(title)}, Content: {bool(content)}")
                    continue
                    
                # Clean content
                content = content.replace('\\n', ' ').replace('\\"', '"').strip()
                if len(content) < 10:
                    logger.warning(f"Content too short for document: {title}")
                    continue
                    
                # Format document (unified format for both models)
                document = {
                    'title': title,
                    'url': url,
                    'content': content,
                    'snippet': content[:200] + '...' if len(content) > 200 else content
                }
                
                logger.debug(f"Processed document - Title: {title}")
                documents.append(document)
                
            except Exception as e:
                logger.error(f"Error processing document: {str(e)}")
                continue
        
        if documents:
            logger.info(f"Successfully processed {len(documents)} documents")
        else:
            logger.error("No documents were successfully processed")
            
        return documents

    def _generate_cache_key(self, query: str, docs: List[Dict], model_type: str, language_code: str = "en") -> str:
        """Generate a unique cache key including model type."""
        doc_identifiers = sorted([
            f"{d.get('title', '')}:{d.get('url', '')}"
            for d in docs
        ])
        doc_key = hash(tuple(doc_identifiers))
        query_key = hash(query.lower().strip())
        return f"{language_code}:{model_type}_response:{query_key}:{doc_key}"

    async def generate_response(
        self,
        query: str,
        documents: List[Dict],
        model_type: str,
        language_code: str = "en",
        description: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Generate response using the specified model type.
        
        Args:
            query (str): The user's query
            documents (List[Dict]): Retrieved documents
            model_type (str): Either 'nova' or 'cohere'
            description (str, optional): Additional context
            conversation_history (List[Dict], optional): Previous conversation
            
        Returns:
            Tuple[str, List[Dict]]: (response, citations)
        """
        try:
            from langsmith import trace
            
            with trace(name=f"{model_type}_response_generation"):
                logger.info(f"Starting {model_type} response generation")
                
                # Validate model type
                if model_type not in ['nova', 'cohere']:
                    raise ValueError(f"Invalid model_type: {model_type}. Must be 'nova' or 'cohere'")
                
                # Select the appropriate model
                model = self.nova_model if model_type == 'nova' else self.cohere_model
                
                # Handle empty documents
                if not documents:
                    logger.warning("No documents provided for processing")
                    if conversation_history:
                        logger.info("Attempting to generate response using conversation history")
                        documents = [{
                            'title': 'Conversation Context',
                            'content': 'This response is based on previous conversation context.',
                            'url': ''
                        }]
                    else:
                        logger.error("No documents and no conversation history available")
                        raise ValueError("No valid documents to process")

                # Generate cache key
                cache_key = self._generate_cache_key(query, documents, model_type, language_code)
                
                # Try cache first
                cache = ClimateCache()
                if cache.redis_client:
                    try:
                        cached_result = await cache.get(cache_key)
                        if cached_result:
                            logger.info(f"Cache hit for {model_type} - returning cached response")
                            return cached_result.get('response'), cached_result.get('citations', [])
                    except Exception as e:
                        logger.error(f"Error retrieving from cache: {str(e)}")
                
                # Process documents and generate response
                with trace(name="document_processing_and_generation"):
                    response, citations = await self._process_and_generate(
                        query=query,
                        documents=documents,
                        model=model,
                        model_type=model_type,
                        description=description,
                        conversation_history=conversation_history
                    )
                    
                # Cache the result
                if cache.redis_client:
                    try:
                        cache_data = {
                            'response': response,
                            'citations': citations
                        }
                        await cache.set(cache_key, cache_data)
                        logger.info(f"{model_type} response cached successfully")
                    except Exception as e:
                        logger.error(f"Error caching response: {str(e)}")
                
                logger.info(f"{model_type} response generation complete")
                return response, citations
                
        except Exception as e:
            logger.error(f"Error in {model_type} response generation: {str(e)}")
            raise

    async def _process_and_generate(
        self,
        query: str,
        documents: List[Dict],
        model,
        model_type: str,
        description: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Process documents and generate response with the selected model."""
        try:
            # Preprocess documents
            processed_docs = self._doc_preprocessing(documents)
            if not processed_docs:
                logger.warning("Document preprocessing returned no valid documents")
                if conversation_history:
                    logger.info("Creating minimal document for conversation-based response")
                    processed_docs = [{
                        'title': 'Conversation Context',
                        'content': 'Response based on previous conversation.',
                        'url': '',
                        'snippet': 'Response based on previous conversation.'
                    }]
                else:
                    raise ValueError("No valid documents to process")
            
            logger.info(f"Successfully processed {len(processed_docs)} documents for {model_type}")
            
            # Optimize conversation history if needed (same logic as before)
            if conversation_history and len(conversation_history) >= 4:
                try:
                    context_prompt = f"""Based on this conversation history and current query, determine which parts
                    of the conversation are most relevant to answering the current query.
                    
                    Current query: {query}
                    
                    For each conversation turn, rate its relevance to the current query on a scale of 1-5,
                    where 5 is "highly relevant" and 1 is "not relevant at all".
                    
                    Return ONLY the list of relevance scores, separated by commas, with no explanation.
                    Example: 2,4,5,1,3
                    """
                    
                    # Use the appropriate model for relevance scoring
                    if model_type == 'nova':
                        relevance_result = await model.content_generation(
                            prompt=context_prompt,
                            system_message="Rate the relevance of conversation turns to the current query"
                        )
                    else:  # cohere
                        relevance_result = await model.generate(
                            prompt=context_prompt,
                            system_message="Rate the relevance of conversation turns to the current query"
                        )
                    
                    # Process relevance scores (same logic as before)
                    if relevance_result:
                        try:
                            # Sanitize tokens like "[SYSTEM OUTPUT]: 1"
                            tokens = [t.strip() for t in relevance_result.replace('\n', ',').split(',') if t.strip()]
                            cleaned = []
                            for t in tokens:
                                # Extract trailing integer if present
                                import re
                                m = re.search(r"(-?\d+)$", t)
                                if m:
                                    cleaned.append(int(m.group(1)))
                            scores = cleaned
                            if len(scores) >= len(conversation_history) // 2:
                                relevant_turns = []
                                for i in range(min(len(scores), len(conversation_history) // 2)):
                                    if scores[i] >= 3:
                                        user_idx = i * 2
                                        asst_idx = user_idx + 1
                                        if asst_idx < len(conversation_history):
                                            relevant_turns.append(conversation_history[user_idx])
                                            relevant_turns.append(conversation_history[asst_idx])
                                
                                if len(relevant_turns) < 2 and len(conversation_history) >= 2:
                                    relevant_turns = conversation_history[-2:]
                                
                                if relevant_turns:
                                    conversation_history = relevant_turns
                                    logger.info(f"Optimized conversation history for {model_type}")
                        except Exception as parse_err:
                            logger.warning(f"Error parsing relevance scores: {str(parse_err)}")
                            
                except Exception as ctx_err:
                    logger.warning(f"Error optimizing conversation context: {str(ctx_err)}")
            
            # Generate response using the appropriate model
            if model_type == 'nova':
                response = await model.generate_response(
                    query=query,
                    documents=processed_docs,
                    description=description,
                    conversation_history=conversation_history
                )
            else:  # cohere
                response = await model.generate_response(
                    query=query,
                    documents=processed_docs,
                    description=description,
                    conversation_history=conversation_history
                )
            
            # Extract citations (unified format)
            citations = []
            for doc in processed_docs:
                # Skip synthetic conversation context docs
                if doc.get('title') != 'Conversation Context' or doc.get('url'):
                    citation = {
                        'title': str(doc.get('title', 'Untitled Source')),
                        'url': str(doc.get('url', '')),
                        'content': str(doc.get('content', '')),
                        'snippet': str(doc.get('snippet', doc.get('content', '')[:200] + '...' if doc.get('content') else ''))
                    }
                    citations.append(citation)
            
            return response, citations
            
        except Exception as e:
            logger.error(f"Error processing documents for {model_type}: {str(e)}")
            raise

# Legacy compatibility functions
async def generate_chat_response(query, documents, model, description=None, conversation_history=None):
    """
    Legacy compatibility function - determines model type and calls unified generator.
    """
    try:
        # Determine model type based on the model instance
        if hasattr(model, 'model_id') and 'nova' in model.model_id.lower():
            model_type = 'nova'
        elif hasattr(model, 'model_id') and 'command' in model.model_id.lower():
            model_type = 'cohere'
        else:
            # Default fallback - check model class name
            model_type = 'nova' if 'Bedrock' in str(type(model)) else 'cohere'
        
        logger.info(f"Legacy call detected - routing to {model_type}")
        
        generator = UnifiedResponseGenerator()
        return await generator.generate_response(
            query=query,
            documents=documents,
            model_type=model_type,
            description=description,
            conversation_history=conversation_history
        )
        
    except Exception as e:
        logger.error(f"Error in legacy generate_chat_response: {str(e)}")
        raise
