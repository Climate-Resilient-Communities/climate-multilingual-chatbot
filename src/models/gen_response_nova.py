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
You are an expert educator on climate change and global warming, addressing questions from a diverse audience, 
including high school students and professionals. Your goal is to provide accessible, engaging, and informative responses.

Persona:
- Think like a teacher, simplifying complex ideas for both youth and adults.
- Ensure your responses are always helpful, respectful, and truthful.

Language:
- Use simple, clear language understandable to a 9th-grade student.
- Avoid jargon and technical terms unless necessary—and explain them when used.

Tone and Style:
- Friendly, approachable, and encouraging.
- Factual, accurate, and free of unnecessary complexity.

Content Requirements:
- Provide detailed and complete answers.
- Use bullet points or lists for clarity.
- Include intuitive examples or relatable analogies when helpful.
- Highlight actionable steps and practical insights.

Guidelines for Answers:
- Emphasize solutions and positive actions people can take.
- Avoid causing fear or anxiety; focus on empowerment and hope.
- Align with ethical principles to avoid harm and respect diverse perspectives.
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

async def nova_chat(query, documents, nova_model, description=None):
    """
    Generate a response from Nova model using a query and retrieved documents.
    
    Args:
        query (str): The user's query
        documents (list): List of documents from retrieval
        nova_model (object): Initialized Nova model
        description (str, optional): Description to include in the prompt
        
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
                
            try:
                # Process documents for generation
                with trace(name="document_processing"):
                    response, citations = await _process_documents_and_generate(
                        query=query,
                        documents=documents,
                        nova_model=nova_model,
                        description=description
                    )
                    
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
    description: str = None
) -> Tuple[str, List[Dict[str, str]]]:
    """Process documents and generate a response using Nova."""
    try:
        # Preprocess documents
        processed_docs = doc_preprocessing(documents)
        if not processed_docs:
            raise ValueError("No valid documents to process")
        
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        
        # Generate response with Nova
        response = await nova_model.generate_response(
            query=query,
            documents=processed_docs,
            description=description
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