import os
import logging
import json
from typing import List, Dict, Tuple, Any, Optional, Union, AsyncGenerator
from src.models.nova_flow import BedrockModel
from src.models.redis_cache import ClimateCache
from concurrent.futures import ThreadPoolExecutor
import time
from langsmith import traceable

logger = logging.getLogger(__name__)

# Import system message from the centralized file
from src.models.system_messages import CLIMATE_SYSTEM_MESSAGE

# Use the imported system message
system_message = CLIMATE_SYSTEM_MESSAGE

def doc_preprocessing(docs: List[Dict]) -> List[Dict]:
    """Prepare documents for processing."""
    documents = []
    logger.debug(f"Processing {len(docs)} documents")
    
    for doc in docs:
        try:
            # Extract required fields
            title = doc.get('title', '')
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
                
            # Format document
            document = {
                'title': title,
                'url': url,
                'content': content,
                'snippet': content[:200] + '...' if len(content) > 200 else content
            }
            
            logger.debug(f"Processed document - Title: {title}")
            logger.debug(f"Content length: {len(content)}")
            
            documents.append(document)
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            continue
    
    if documents:
        logger.info(f"Successfully processed {len(documents)} documents")
    else:
        logger.error("No documents were successfully processed")
        
    return documents

def generate_cache_key(query: str, docs: List[Dict]) -> str:
    """Generate a unique cache key."""
    doc_identifiers = sorted([
        f"{d.get('title', '')}:{d.get('url', '')}"
        for d in docs
    ])
    doc_key = hash(tuple(doc_identifiers))
    query_key = hash(query.lower().strip())
    return f"nova_response:{query_key}:{doc_key}"

async def nova_chat(query, documents, nova_model, description=None, conversation_history=None):
    """
    Generate a response from Nova model using a query and retrieved documents.
    
    Args:
        query (str): The user's query
        documents (list): List of documents from retrieval
        nova_model (object): Initialized Nova model
        description (str, optional): Description to include in the prompt
        conversation_history (list, optional): Conversation history for context
        
    Returns:
        tuple: (response, citations)
    """
    try:
        from langsmith import trace
        
        with trace(name="nova_response_generation"):
            logger.info("Starting nova_chat response generation")
            
            if not documents:
                logger.warning("No documents were provided for processing")
                # Instead of raising an error, let's try to generate a response based just on conversation history
                if conversation_history:
                    logger.info("Attempting to generate response using only conversation history")
                    # Create a minimal document with conversation summary
                    documents = [
                        {
                            'title': 'Conversation Context',
                            'content': 'This response is based on previous conversation context.',
                            'url': ''
                        }
                    ]
                else:
                    logger.error("No documents and no conversation history available")
                    raise ValueError("No valid documents to process")

            # Generate cache key based on query and documents
            cache_key = generate_cache_key(query, documents)
            
            # Try to get cached response
            cache = ClimateCache()
            if cache.redis_client:
                try:
                    cached_result = await cache.get(cache_key)
                    if cached_result:
                        logger.info("Cache hit - returning cached response")
                        return cached_result.get('response'), cached_result.get('citations', [])
                except Exception as e:
                    logger.error(f"Error retrieving from cache: {str(e)}")
            
            try:
                # Process documents for generation
                with trace(name="document_processing"):
                    response, citations = await _process_documents_and_generate(
                        query=query,
                        documents=documents,
                        nova_model=nova_model,
                        description=description,
                        conversation_history=conversation_history
                    )
                    
                # Cache the result if cache is available
                if cache.redis_client:
                    try:
                        cache_data = {
                            'response': response,
                            'citations': citations
                        }
                        await cache.set(cache_key, cache_data)
                        logger.info("Response cached successfully")
                    except Exception as e:
                        logger.error(f"Error caching response: {str(e)}")
                
                logger.info("Response generation complete")
                return response, citations
                
            except Exception as e:
                logger.error(f"Error in nova_chat: {str(e)}")
                raise
    except Exception as e:
        logger.error(f"Error in nova_chat: {str(e)}")
        raise

async def _process_documents_and_generate(
    query: str,
    documents: List[Dict[str, Any]],
    nova_model,
    description: str = None,
    conversation_history: list = None
) -> Tuple[str, List[Dict[str, str]]]:
    """Process documents and generate a response using Nova with improved multi-turn conversation handling."""
    try:
        # Preprocess documents
        processed_docs = doc_preprocessing(documents)
        if not processed_docs:
            logger.warning("Document preprocessing returned no valid documents")
            # If we have conversation history, create a synthetic document to avoid errors
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
        
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        
        # If we have conversation history, check if we should prioritize the most recent context
        if conversation_history and len(conversation_history) > 1:
            # Extract the most salient part of the conversation history
            try:
                # Only if we have at least 4 conversation turns (2 exchanges), try to optimize context
                if len(conversation_history) >= 4:
                    # Use Nova to identify which parts of the conversation are most relevant to current query
                    context_prompt = f"""Based on this conversation history and current query, determine which parts
                    of the conversation are most relevant to answering the current query.
                    
                    Current query: {query}
                    
                    For each conversation turn, rate its relevance to the current query on a scale of 1-5,
                    where 5 is "highly relevant" and 1 is "not relevant at all".
                    
                    Return ONLY the list of relevance scores, separated by commas, with no explanation.
                    Example: 2,4,5,1,3
                    """
                    
                    # The relevance scores will be used to optimize the conversation history
                    try:
                        relevance_result = await nova_model.nova_content_generation(
                            prompt=context_prompt,
                            system_message="Rate the relevance of conversation turns to the current query"
                        )
                        
                        logger.debug(f"Relevance scores for conversation history: {relevance_result}")
                        
                        # If we were able to get relevance scores, prioritize the most relevant parts
                        if relevance_result:
                            # Try to parse the relevance scores
                            try:
                                scores = [int(s.strip()) for s in relevance_result.split(',')]
                                if len(scores) >= len(conversation_history) // 2:  # We need at least one score per exchange
                                    # Keep conversation pairs with scores >= 3 (at least moderately relevant)
                                    relevant_turns = []
                                    for i in range(min(len(scores), len(conversation_history) // 2)):
                                        if scores[i] >= 3:
                                            user_idx = i * 2
                                            asst_idx = user_idx + 1
                                            if asst_idx < len(conversation_history):
                                                relevant_turns.append(conversation_history[user_idx])
                                                relevant_turns.append(conversation_history[asst_idx])
                                    
                                    logger.info(f"Identified {len(relevant_turns) // 2} relevant conversation exchanges")
                                    
                                    # Always include at least the most recent exchange
                                    if len(relevant_turns) < 2 and len(conversation_history) >= 2:
                                        relevant_turns = conversation_history[-2:]
                                    
                                    # Replace conversation history with optimized version if we found relevant turns
                                    if relevant_turns:
                                        conversation_history = relevant_turns
                                        logger.info("Successfully optimized conversation history for relevance")
                            except Exception as parse_err:
                                logger.warning(f"Error parsing relevance scores: {str(parse_err)}") 
                    except Exception as rel_err:
                        logger.warning(f"Error determining conversation relevance: {str(rel_err)}")
                
            except Exception as ctx_err:
                logger.warning(f"Error optimizing conversation context: {str(ctx_err)}")
                # Continue with the original conversation history
        
        # Generate response with Nova, now passing optimized conversation_history
        response = await nova_model.generate_response(
            query=query,
            documents=processed_docs,
            description=description,
            conversation_history=conversation_history
        )
        
        # Extract citations with full document details
        citations = []
        for doc in processed_docs:
            # Only include real citations (skip synthetic conversation context docs)
            if doc.get('title') != 'Conversation Context' or doc.get('url'):
                # Format citation with all required fields
                citation = {
                    'title': str(doc.get('title', 'Untitled Source')),
                    'url': str(doc.get('url', '')),
                    'content': str(doc.get('content', '')),
                    'snippet': str(doc.get('snippet', doc.get('content', '')[:200] + '...' if doc.get('content') else ''))
                }
                citations.append(citation)
        
        return response, citations
        
    except Exception as e:
        logger.error(f"Error processing documents: {str(e)}")
        raise

async def process_batch_queries(queries: List[str], documents: List[Dict], nova_client) -> List[str]:
    """Process multiple queries in parallel using asyncio.gather"""
    tasks = [nova_chat(query, documents, nova_client) for query in queries]
    results = await asyncio.gather(*tasks)
    return [response for response, _ in results]

if __name__ == "__main__":
    start_time = time.time()
    
    # Initialize Nova client
    nova_client = BedrockModel()  # Updated initialization
    
    # Test documents
    test_docs = [
        {
            'title': 'Climate Change Overview',
            'content': 'Climate change is a long-term shift in global weather patterns and temperatures.',
            'url': ['https://example.com/climate']
        },
        {
            'title': 'Impact Analysis',
            'content': 'Rising temperatures are causing more extreme weather events worldwide.',
            'url': ['https://example.com/impacts']
        }
    ]
    
    query = "What is climate change?"
    
    try:
        import asyncio
        response, citations = asyncio.run(nova_chat(query, test_docs, nova_client))
        print("\nResponse:", response)
        print("\nCitations:", citations)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        
    print('\nProcessing time:', time.time() - start_time)
