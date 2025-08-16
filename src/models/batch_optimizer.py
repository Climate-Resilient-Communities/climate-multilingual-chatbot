"""
Batch processing optimizations for the climate chatbot pipeline.
Focuses on parallelizable operations while preserving quality.
"""

import asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from functools import lru_cache

class PipelineBatchOptimizer:
    """Optimizes batch operations in the climate pipeline"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def batch_embed_documents(self, embed_model, texts: List[str]) -> np.ndarray:
        """
        Batch embedding with optimal chunking for BGE-M3
        - Chunks large batches to avoid memory issues
        - Uses async execution to prevent blocking
        """
        if not texts:
            return np.array([])
        
        # BGE-M3 optimal batch size is 8-16
        chunk_size = 12
        chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]
        
        async def embed_chunk(chunk):
            loop = asyncio.get_event_loop()
            # Run in thread pool to avoid blocking
            return await loop.run_in_executor(
                self.executor, 
                embed_model.encode, 
                chunk
            )
        
        # Process chunks in parallel
        tasks = [embed_chunk(chunk) for chunk in chunks]
        chunk_results = await asyncio.gather(*tasks)
        
        # Combine results
        if chunk_results:
            return np.vstack([result['dense_vecs'] for result in chunk_results])
        return np.array([])
    
    async def parallel_citation_processing(self, sources: List[Dict]) -> List[Dict]:
        """
        Parallel processing of citation metadata
        - Favicon fetching
        - Domain validation
        - URL cleanup
        """
        async def process_source(source):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self._process_single_citation,
                source
            )
        
        tasks = [process_source(source) for source in sources]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _process_single_citation(self, source: Dict) -> Dict:
        """Process single citation with error handling"""
        try:
            # Add favicon, clean URL, validate domain
            url = source.get('url', '')
            source['favicon'] = f"https://www.google.com/s2/favicons?domain={url}&sz=32"
            source['domain'] = self._extract_domain(url)
            return source
        except Exception as e:
            source['processing_error'] = str(e)
            return source
    
    @lru_cache(maxsize=1000)
    def _extract_domain(self, url: str) -> str:
        """Cached domain extraction"""
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    async def batch_language_detection(self, texts: List[str], router) -> List[str]:
        """
        Batch language detection for conversation history
        - Only for non-critical path (not main query)
        - Used for analytics/logging
        """
        async def detect_single(text):
            try:
                result = await router.detect_language(text)
                return result.get('detected_language', 'unknown')
            except:
                return 'unknown'
        
        # Limit concurrent detections to avoid overwhelming APIs
        semaphore = asyncio.Semaphore(3)
        
        async def bounded_detect(text):
            async with semaphore:
                return await detect_single(text)
        
        tasks = [bounded_detect(text) for text in texts]
        return await asyncio.gather(*tasks, return_exceptions=True)

# Usage patterns for different pipeline stages

class OptimizedRetrieval:
    """Enhanced retrieval with batch optimizations"""
    
    def __init__(self, embed_model, optimizer: PipelineBatchOptimizer):
        self.embed_model = embed_model
        self.optimizer = optimizer
    
    async def get_documents_optimized(self, query: str, doc_candidates: List[str]):
        """
        Optimized document retrieval with batching
        """
        # 1. Single query embedding (can't batch this - needs individual context)
        query_embedding = await self._get_query_embedding(query)
        
        # 2. Batch candidate document embeddings (if not cached)
        candidate_embeddings = await self.optimizer.batch_embed_documents(
            self.embed_model, doc_candidates
        )
        
        # 3. Vectorized similarity computation (much faster than loops)
        similarities = np.dot(candidate_embeddings, query_embedding.T)
        
        # 4. Return top candidates
        top_indices = np.argsort(similarities.flatten())[-10:][::-1]
        return [doc_candidates[i] for i in top_indices]
    
    async def _get_query_embedding(self, query: str):
        """Single query embedding - can't batch without losing context"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self.embed_model.encode, [query]
        )
        return result['dense_vecs'][0]

# Integration example
async def optimized_pipeline_stage(pipeline, query: str, conversation_history: List[str]):
    """
    Example of how to integrate optimizations
    """
    optimizer = PipelineBatchOptimizer(max_workers=4)
    
    # Parallel non-critical operations
    citation_task = optimizer.parallel_citation_processing(pipeline.sources)
    history_lang_task = optimizer.batch_language_detection(conversation_history, pipeline.router)
    
    # Sequential critical path (quality-sensitive)
    main_result = await pipeline.process_query(query)
    
    # Collect parallel results
    enhanced_citations, conversation_languages = await asyncio.gather(
        citation_task, 
        history_lang_task
    )
    
    # Combine results
    main_result['enhanced_citations'] = enhanced_citations
    main_result['conversation_analytics'] = {
        'detected_languages': conversation_languages
    }
    
    return main_result
