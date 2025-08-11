import logging
from typing import List, Dict
import cohere
import asyncio
import time
from typing import Optional
from src.utils.env_loader import load_environment

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def prepare_docs_for_rerank(docs_to_rerank: List[Dict]) -> List[Dict]:
    """Prepare documents for reranking."""
    prepared_docs = []
    
    for doc in docs_to_rerank:
        try:
            # Get content from either content or chunk_text field
            content = doc.get('content', doc.get('chunk_text', ''))
            if not content.strip():
                logger.warning("Empty content found, skipping document")
                continue
                
            # Clean the content
            content = content.replace('\\n', ' ').replace('\\"', '"').strip()
            
            # Create the document for reranking
            prepared_doc = {
                'text': content,
                'title': doc.get('title', 'No Title'),
                'url': doc.get('url', [''])[0] if isinstance(doc.get('url', []), list) else doc.get('url', '')
            }
            
            # Store original document structure
            prepared_doc['original'] = doc
            
            prepared_docs.append(prepared_doc)
            
        except Exception as e:
            logger.error(f"Error preparing document for rerank: {str(e)}")
            continue
            
    return prepared_docs

MAX_CHARS = 1500  # clip per doc to control payload size (~300-400 tokens)

def _clip_text(text: str, limit: int = MAX_CHARS) -> str:
    try:
        return (text or "")[: int(limit)]
    except Exception:
        return text or ""

def rerank_fcn(query: str, docs_to_rerank: List[Dict], top_k: int, cohere_client) -> List[Dict]:
    """
    Rerank documents using Cohere's rerank endpoint.
    
    Args:
        query (str): The query to rerank against
        docs_to_rerank (List[Dict]): List of documents to rerank
        top_k (int): Number of documents to return
        cohere_client: Initialized Cohere client
        
    Returns:
        List[Dict]: Reranked documents
    """
    try:
        logger.debug(f"Reranking {len(docs_to_rerank)} documents")
        
        if not docs_to_rerank:
            return []
            
        # Log sample document structure for debugging
        if docs_to_rerank:
            logger.debug(f"Sample document structure: {docs_to_rerank[0]}")
            
        # Extract and clip document texts
        docs = [_clip_text(doc.get('content', '')) for doc in docs_to_rerank]
        total_chars = sum(len(d or "") for d in docs)
        logger.info(f"dep=cohere_rerank payload_chars={total_chars} n_docs={len(docs)}")
        
        # Call Cohere rerank with hard timeout and timing
        t0 = time.perf_counter()
        rerank_results = None
        try:
            # Cohere SDK is sync; run it in a thread and enforce timeout using wait_for on the outer future
            async def _call():
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: cohere_client.rerank(
                        query=query,
                        documents=docs,
                        top_n=top_k,
                        model="rerank-english-v3.0",
                        return_documents=True,
                    ),
                )

            rerank_results = asyncio.run(asyncio.wait_for(_call(), timeout=10))
            ms = (time.perf_counter() - t0) * 1000
            logger.info(f"dep=cohere_rerank host=api.cohere.com op=rerank ms={ms:.1f} status=OK")
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            logger.warning(f"dep=cohere_rerank host=api.cohere.com op=rerank ms={ms:.1f} status=FALLBACK err={type(e).__name__}: {e}")
            rerank_results = None
        
        # Process results
        reranked_docs = []
        if rerank_results and getattr(rerank_results, 'results', None):
            for result in rerank_results.results:
                original_doc = docs_to_rerank[result.index]
                reranked_doc = {**original_doc}
                reranked_doc['score'] = result.relevance_score
                reranked_docs.append(reranked_doc)
        else:
            # Graceful fallback: keep Pinecone order
            return docs_to_rerank[:top_k] if docs_to_rerank else []
            
        return reranked_docs
            
    except Exception as e:
        logger.error(f"Error in reranking: {str(e)}", exc_info=True)
        # Return original docs on error
        return docs_to_rerank[:top_k] if docs_to_rerank else []

if __name__ == "__main__":
    # Test code
    import os
    
    load_environment()
    COHERE_API_KEY = os.getenv('COHERE_API_KEY')
    
    if not COHERE_API_KEY:
        raise ValueError("COHERE_API_KEY not found in environment variables")
        
    cohere_client = cohere.Client(COHERE_API_KEY)
    
    test_docs = [
        {
            'title': 'Test Document 1',
            'content': 'This is some test content about climate change.',
            'url': ['http://example.com/1']
        },
        {
            'title': 'Test Document 2',
            'content': 'More test content about global warming.',
            'url': ['http://example.com/2']
        }
    ]
    
    try:
        result = rerank_fcn("climate change effects", test_docs, 2, cohere_client)
        print("Reranking successful!")
        print(f"Number of reranked documents: {len(result)}")
        if result:
            print(f"First document score: {result[0]['score']}")
    except Exception as e:
        print(f"Test failed: {str(e)}")