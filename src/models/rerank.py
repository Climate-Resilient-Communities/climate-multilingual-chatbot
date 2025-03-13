import logging
from typing import List, Dict
import cohere
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
            
        # Extract document texts
        docs = [doc.get('content', '') for doc in docs_to_rerank]
        
        # Call Cohere rerank
        rerank_results = cohere_client.rerank(
            query=query,
            documents=docs,
            top_n=top_k,
            model="rerank-english-v2.0"
        )
        
        # Process results
        reranked_docs = []
        for result in rerank_results.results:
            # Get original document
            original_doc = docs_to_rerank[result.index]
            
            # Create reranked document with original metadata and new score
            reranked_doc = {**original_doc}  # Copy original doc
            reranked_doc['score'] = result.relevance_score
            
            reranked_docs.append(reranked_doc)
            
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