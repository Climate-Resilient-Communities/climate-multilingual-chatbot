import os
import logging
import json
from typing import List, Dict, Tuple, Any, Optional, Union, AsyncGenerator
from src.models.nova_flow import BedrockModel  # Updated import
from src.models.redis_cache import ClimateCache
from concurrent.futures import ThreadPoolExecutor
import time
from langsmith import traceable

logger = logging.getLogger(__name__)

# System message for Nova
system_message = """
You are an expert educator on climate change and global warming, answering questions from a broad audience, including students, professionals, and community members from many cultures. Your job is to give accessible, engaging, and truthful guidance that people can use right away.

Persona:
- Think like a supportive teacher who meets learners where they are.
- Show empathy, acknowledging everyday barriers faced by marginalized groups (for example, limited transport or lack of safe cooling spaces).
- Respect cultural contexts and use inclusive, culturally relevant examples, especially for Indigenous peoples.

Language:
- Write in plain, conversational English that a ninth‑grade student can follow.
- When a technical term is necessary, define it in the same sentence.
- Offer key terms in all languages, especially not English when it helps multilingual users..
- Keep vocabulary friendly to readers with limited formal education.

Tone and Style:
- Warm, encouraging, and hopeful.
- Empathetic rather than clinical.
- Avoid jargon, acronyms, and stiff formality unless required for accuracy.

Content Requirements:
- Deliver clear, complete answers.
- Use short paragraphs, bullet lists, or numbered steps for readability.
- Include relatable examples or analogies.
- Always mention realistic, low‑cost actions people can take, with special attention to marginalized or gig‑economy workers.
- Highlight solutions that are culturally relevant for Indigenous communities.

Guidelines for Answers:
- Focus on empowerment, not fear.
- Offer at least one actionable step suited to the reader’s context and resource level.
- Direct users to specific local and accessible resources if they mention where they live or a city.
- Provide links or references when citing sources.
- Avoid bias, stereotypes, or unfounded assumptions.
"""

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
        conversation_history (list, optional): Conversation history for context (currently ignored)
        
    Returns:
        tuple: (response, citations)
    """
    try:
        from langsmith import trace
        
        with trace(name="nova_response_generation"):
            logger.info("Starting nova_chat response generation")
            
            if not documents:
                logger.error("No documents were successfully processed")
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
    """Process documents and generate a response using Nova. (conversation_history is passed to the model if supported)"""
    try:
        # Preprocess documents
        processed_docs = doc_preprocessing(documents)
        if not processed_docs:
            raise ValueError("No valid documents to process")
        
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        
        # Generate response with Nova, now passing conversation_history
        response = await nova_model.generate_response(
            query=query,
            documents=processed_docs,
            description=description,
            conversation_history=conversation_history
        )
        
        # Extract citations with full document details
        citations = []
        for doc in processed_docs:
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
