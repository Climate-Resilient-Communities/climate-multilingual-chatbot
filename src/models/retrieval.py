"""
Document Retrieval Module for Climate Chatbot
============================================

This module handles document retrieval using BGE-M3 embeddings and Pinecone vector search.

Performance Note - XLMRobertaTokenizerFast Warning:
--------------------------------------------------
The XLMRobertaTokenizerFast warning from BGE-M3 is suppressed for cleaner output.
This is a performance optimization suggestion that would need to be implemented
in the upstream FlagEmbedding library, not in our code.
"""

import warnings
# Suppress XLMRobertaTokenizerFast warnings for cleaner output
warnings.filterwarnings("ignore", message="You're using a XLMRobertaTokenizerFast tokenizer")
warnings.filterwarnings("ignore", message=".*XLMRobertaTokenizerFast.*", category=UserWarning)

import os
import hashlib
import time
import logging
import warnings
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import re
from urllib.parse import urlparse
from pinecone import Pinecone
from FlagEmbedding import BGEM3FlagModel
from src.models.rerank import rerank_fcn
from src.models.title_normalizer import normalize_title
from src.utils.env_loader import load_environment
from langsmith import traceable

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmbeddingCache:
    """A simple LRU cache for document embeddings keyed by stable ids."""
    def __init__(self, max_size: int = 5000):
        self.max_size = int(max_size)
        self._store: Dict[str, List[float]] = {}
        self._lru: List[str] = []

    def get(self, key: Optional[str]) -> Optional[List[float]]:
        if not key:
            return None
        vec = self._store.get(key)
        if vec is not None:
            try:
                self._lru.remove(key)
            except ValueError:
                pass
            self._lru.append(key)
        return vec

    def put(self, key: Optional[str], vector: Optional[List[float]]) -> None:
        if not key or vector is None:
            return
        if key not in self._store and len(self._store) >= self.max_size:
            # Evict oldest
            try:
                oldest = self._lru.pop(0)
                self._store.pop(oldest, None)
            except Exception:
                self._store.clear()
                self._lru.clear()
        self._store[key] = vector
        try:
            if key in self._lru:
                self._lru.remove(key)
        except ValueError:
            pass
        self._lru.append(key)

_EMB_CACHE = EmbeddingCache(max_size=int(os.getenv("EMBED_CACHE_MAX", "4000")))

def get_query_embeddings(query: str, embed_model) -> tuple:
    """
    Get dense and sparse embeddings for a query.

    Performance Note: The XLMRobertaTokenizerFast warning suggests using tokenizer.__call__()
    instead of encode()+pad() for better performance. This is an internal optimization
    in the BGE-M3 model that could improve speed by ~10-20%.

    To potentially reduce the warning frequency, we ensure optimal input format.
    """
    import time
    t_start = time.perf_counter()
    logger.info(f"Query embedding IN: query_len={len(query)} chars, query_repr='{query[:100]}...'")

    # Suppress XLMRobertaTokenizerFast warnings during embedding
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        warnings.filterwarnings("ignore", message=".*XLMRobertaTokenizerFast.*")
        warnings.filterwarnings("ignore", message=".*fast tokenizer.*")

        # Ensure query is properly formatted for optimal tokenization
        # Try multiple approaches to handle the array ambiguity bug in BGE-M3
        embeddings = None
        last_error = None

        try:
            if isinstance(query, str) and query.strip():
                # Use list format which is more efficient for batch processing
                embeddings = embed_model.encode(
                    [query.strip()],
                    return_dense=True,
                    return_sparse=True,
                    return_colbert_vecs=False
                )
            else:
                # Fallback for edge cases
                embeddings = embed_model.encode(
                    [query] if isinstance(query, str) else query,
                    return_dense=True,
                    return_sparse=True,
                    return_colbert_vecs=False
                )
        except Exception as e:
            last_error = e
            logger.warning(f"BGE-M3 encoding failed: {str(e)[:100]}")
            if "ambiguous" in str(e).lower():
                logger.warning(f"Detected array ambiguity error, attempting fallback encoding")
                # Try with different parameters as workaround
                try:
                    embeddings = embed_model.encode(
                        [str(query).strip()],  # Force string conversion
                        return_dense=True,
                        return_sparse=False,  # Disable sparse to avoid the bug
                        return_colbert_vecs=False
                    )
                    # Create empty sparse embeddings as fallback
                    if 'lexical_weights' not in embeddings:
                        embeddings['lexical_weights'] = [{}]
                    logger.info("Successfully used sparse-disabled fallback for BGE-M3")
                except Exception as e2:
                    logger.error(f"Both encoding attempts failed: {str(e)} -> {str(e2)}")
                    raise last_error
            else:
                raise

    elapsed_ms = int((time.perf_counter() - t_start) * 1000)

    # Safe extraction of dimensions without triggering array boolean evaluation
    dense_vecs = embeddings.get('dense_vecs')
    dense_dim = len(dense_vecs[0]) if dense_vecs is not None and len(dense_vecs) > 0 else 0

    # Fix lexical_weights access - it's a list of dicts, not dicts with 'indices'
    lw = embeddings.get('lexical_weights')
    if isinstance(lw, list) and lw and isinstance(lw[0], dict):
        sparse_tokens = len(lw[0])  # number of token ids in the first query
    else:
        sparse_tokens = 0

    logger.info(f"dep=query_embed op=encode ms={elapsed_ms} dense_dim={dense_dim} sparse_tokens={sparse_tokens}")

    query_dense_embeddings = embeddings['dense_vecs']
    query_sparse_embeddings_lst = embeddings['lexical_weights']

    query_sparse_embeddings = []
    for sparse_embedding in query_sparse_embeddings_lst:
        sparse_dict = {}
        sparse_dict['indices'] = [int(index) for index in list(sparse_embedding.keys())]
        sparse_dict['values'] = [float(v) for v in list(sparse_embedding.values())]
        query_sparse_embeddings.append(sparse_dict)

    if isinstance(query_dense_embeddings, np.ndarray):
        query_dense_embeddings = query_dense_embeddings.astype(float)

    return query_dense_embeddings, query_sparse_embeddings

def weight_by_alpha(sparse_embedding: Dict, dense_embedding: List[float], alpha: float) -> tuple:
    """Weight the sparse and dense embeddings."""
    if alpha < 0 or alpha > 1:
        raise ValueError("Alpha must be between 0 and 1")

    hsparse = {
        'indices': sparse_embedding['indices'],
        'values': [float(v * (1 - alpha)) for v in sparse_embedding['values']]
    }
    hdense = [float(v * alpha) for v in dense_embedding]
    return hsparse, hdense

def issue_hybrid_query(index, sparse_embedding: Dict, dense_embedding: List[float],
                      alpha: float, top_k: int, metadata_filter: Optional[Dict] = None):
    """Execute hybrid search query on Pinecone index."""
    scaled_sparse, scaled_dense = weight_by_alpha(sparse_embedding, dense_embedding, alpha)

    kwargs = {
        'vector': scaled_dense,
        'sparse_vector': scaled_sparse,
        'top_k': top_k,
        'include_metadata': True,
        'include_values': True,  # fetch stored dense vectors to avoid re-embedding for MMR
    }
    # Optional server-side metadata filter
    if metadata_filter:
        kwargs['filter'] = metadata_filter

    start = time.time()
    try:
        result = index.query(**kwargs)
        elapsed_ms = int((time.time() - start) * 1000)
        try:
            host = getattr(index, "host", None) or getattr(index, "_host", "unknown")
        except Exception:
            host = "unknown"
        logger.info(f"dep=pinecone host={host} op=query ms={elapsed_ms} status=OK")
        # Debug the actual match structure to verify values presence
        try:
            if getattr(result, 'matches', None):
                m = result.matches[0]
                logger.info(
                    f"pinecone.match type={type(m)} attrs_have_values={hasattr(m,'values')} "
                    f"has_values={(m.values is not None) if hasattr(m,'values') else False}"
                )
        except Exception:
            pass
        return result
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        try:
            host = getattr(index, "host", None) or getattr(index, "_host", "unknown")
        except Exception:
            host = "unknown"
        logger.warning(f"dep=pinecone host={host} op=query ms={elapsed_ms} status=ERR err={str(e)[:120]}")
        raise

def get_hybrid_results(index, query: str, embed_model, alpha: float, top_k: int, metadata_filter: Optional[Dict] = None):
    """Get hybrid search results."""
    import time
    t_total = time.perf_counter()

    query_dense_embeddings, query_sparse_embeddings = get_query_embeddings(query, embed_model)

    t_query = time.perf_counter()
    result = issue_hybrid_query(
        index,
        query_sparse_embeddings[0],
        query_dense_embeddings[0],
        alpha,
        top_k,
        metadata_filter=metadata_filter,
    )

    query_ms = int((time.perf_counter() - t_query) * 1000)
    total_ms = int((time.perf_counter() - t_total) * 1000)
    logger.info(f"dep=hybrid_search embed_ms={total_ms - query_ms} query_ms={query_ms} total_ms={total_ms}")

    return result


def issue_sparse_query(index, sparse_embedding: Dict, top_k: int, metadata_filter: Optional[Dict] = None):
    """Execute sparse-only (BM25-like) search on Pinecone index."""
    # Some indexes are dense-only; when they reject sparse-only queries,
    # include a tiny zero dense vector to satisfy schema.
    kwargs = {
        'sparse_vector': sparse_embedding,
        'top_k': int(top_k),
        'include_metadata': True,
        'include_values': True,  # fetch stored dense vectors when available
    }
    if metadata_filter:
        kwargs['filter'] = metadata_filter
    try:
        return index.query(**kwargs)
    except Exception as e:
        # Fallback: add a tiny zero dense vector with expected dimension if available
        try:
            dim = getattr(index.describe_index_stats(), 'dimension', None)
        except Exception:
            dim = None
        if dim and isinstance(dim, int) and dim > 0:
            kwargs['vector'] = [0.0] * dim
            return index.query(**kwargs)
        raise


def get_sparse_results(index, query: str, embed_model, top_k: int, metadata_filter: Optional[Dict] = None):
    """Get sparse-only results (BM25-like) using BGE-M3 lexical weights only."""
    query_dense_embeddings, query_sparse_embeddings = get_query_embeddings(query, embed_model)
    return issue_sparse_query(
        index,
        query_sparse_embeddings[0],
        int(top_k),
        metadata_filter=metadata_filter,
    )


def _extract_domain(url_value: Any) -> str:
    try:
        url_str = url_value[0] if isinstance(url_value, list) else url_value
        parsed = urlparse(str(url_str))
        host = parsed.netloc or ""
        # strip www.
        return host.lower().lstrip('www.')
    except Exception:
        return ""


def _apply_domain_boosts(docs: List[Dict], preferred_domains: List[str], weight: float) -> List[Dict]:
    if not preferred_domains or weight <= 0:
        return docs
    boosted = []
    for d in docs:
        domain = _extract_domain(d.get('url', []))
        score = float(d.get('score', 0.0))
        if any(pref in domain for pref in preferred_domains if isinstance(pref, str)):
            score += float(weight)
        d2 = {**d, 'score': score}
        boosted.append(d2)
    return boosted


def _apply_audience_blocklist(docs: List[Dict]) -> Tuple[List[Dict], int, int]:
    """Drop K-12/educational materials by regex on title/content and by domain guard."""
    try:
        # Prefer FILTERS_CONFIG when available
        from src.data.config.config import FILTERS_CONFIG
        cfg_blk = FILTERS_CONFIG.get("audience_blocklist_regex", [])
    except Exception:
        cfg_blk = []

    # Robust K–12 patterns
    grades = r'(?:K|Gr(?:ade)?s?)\s*(?:[-–]\s*)?(?:K|[0-9]{1,2})(?:\s*(?:[-–]\s*|to)\s*(?:K|[0-9]{1,2}))?'
    eduterms = r'(?:classroom|lesson\s*plan|curriculum|worksheet|teachers?|school|students?)'
    k12_core = rf'(?:{grades}\s*(?:{eduterms})|{eduterms}.*{grades})'
    block_re = re.compile(
        rf'(?i)\b(?:{k12_core}|K-?\s?12|K\s*[-–]\s*12|Kindergarten|project\s+of\s+learning|learning\s+for\s+a\s+sustainable\s+future)\b'
    )

    # Accept extra raw regex from config (already regexes)
    extra_regexes: List[re.Pattern] = []
    for pat in (cfg_blk or []):
        try:
            extra_regexes.append(re.compile(pat, re.IGNORECASE))
        except Exception:
            # treat as literal
            extra_regexes.append(re.compile(re.escape(str(pat)), re.IGNORECASE))

    # Lightweight domain block for known K–12 publishers
    k12_block_domains = {"lsf-lst.ca", "climatelearning.ca"}

    filtered: List[Dict] = []
    blocked = 0
    blocked_text_only = 0

    for d in docs:
        title_l = (d.get('title', '') or '').lower()
        content_l_short = ((d.get('content', '') or '')[:512]).lower()
        domain = _extract_domain(d.get('url', []))

        title_hit = bool(block_re.search(title_l)) or any(rx.search(title_l) for rx in extra_regexes)
        content_hit = bool(block_re.search(content_l_short)) or any(rx.search(content_l_short) for rx in extra_regexes)
        domain_hit = any(dom in domain for dom in k12_block_domains) if domain else False

        if title_hit or content_hit or domain_hit:
            blocked += 1
            if (not title_hit) and content_hit:
                blocked_text_only += 1
            continue
        filtered.append(d)

    return filtered, blocked, blocked_text_only


HOWTO_QUERY_REGEX = re.compile(r"(how to|tips|at home|safety|cost|guide|checklist|prepare|kit)", re.I)

def _is_howto_query(query: str) -> bool:
    return bool(HOWTO_QUERY_REGEX.search(query or ""))


def _apply_soft_boosts(query: str, docs: List[Dict], boost_doc_type: float = 0.05, boost_topic: float = 0.03) -> List[Dict]:
    """Apply tiny boosts to doc score for how-to doc types and topic keywords to influence gating mix."""
    if not docs:
        return docs
    # Try to import topic/doc-type hints
    try:
        from src.data.config.config import FILTERS_CONFIG, BOOSTS_CONFIG
        doc_type_hints = FILTERS_CONFIG.get("doc_type_preferences", {}).get("howto", [])
        topic_keywords_cfg = BOOSTS_CONFIG.get("topic_keywords", {})
        ev_hints = topic_keywords_cfg.get("ev", [])
        weatherize_hints = topic_keywords_cfg.get("weatherize", [])
        heat_aqi_hints = topic_keywords_cfg.get("heat_aqi", [])
    except Exception:
        doc_type_hints = ["factsheet", "guideline", "advisory", "toolkit", "checklist"]
        ev_hints = ["EVSE", "Level 2", "240V", "charger", "amperage", "NEMA", "CSA", "breaker", "circuit"]
        weatherize_hints = ["caulk", "weatherstrip", "R-value", "insulation", "window film", "storm window"]
        heat_aqi_hints = ["AQI", "PM2.5", "N95", "cooling centre", "hydration"]

    ql = (query or "").lower()
    topic_keywords: List[str] = []
    if any(k in ql for k in ["ev", "charger", "charging"]):
        topic_keywords = ev_hints
    elif any(k in ql for k in ["weather", "window", "insulat", "draft", "caulk", "weatherstrip"]):
        topic_keywords = weatherize_hints
    elif any(k in ql for k in ["heat", "air quality", "aqi", "smoke", "wildfire"]):
        topic_keywords = heat_aqi_hints

    boosted: List[Dict] = []
    for d in docs:
        t = (d.get('title', '') or '').lower()
        u = d.get('url', '')
        if isinstance(u, list):
            u = (u[0] if u else '')
        u = str(u).lower()
        c = (d.get('content', '') or '').lower()
        s = float(d.get('score', 0.0))

        if _is_howto_query(query) and any(h in t or h in u for h in doc_type_hints):
            s += float(boost_doc_type)
        if topic_keywords and any(re.search(k, c, flags=re.IGNORECASE) for k in topic_keywords):
            s += float(boost_topic)
        boosted.append({**d, 'score': s})
    return boosted


def _dedup_by_title_url(docs: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for d in docs:
        key = (d.get('title', '').strip().lower(), str(d.get('url', [None])[0]).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def _cosine_sim_np(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    denom = norm_a * norm_b
    # Use np.isclose for safer zero comparison with floats
    if np.isclose(denom, 0.0):
        return 0.0
    return float(np.dot(a, b) / denom)


def _mmr_select_indices(query_vec: np.ndarray, doc_vecs: np.ndarray, lambda_param: float, k: int) -> List[int]:
    n = doc_vecs.shape[0]
    if n <= k:
        return list(range(n))
    q_sims = np.array([_cosine_sim_np(query_vec, doc_vecs[i]) for i in range(n)])
    d_sims = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            s = _cosine_sim_np(doc_vecs[i], doc_vecs[j])
            d_sims[i, j] = s
            d_sims[j, i] = s
    selected = []
    candidates = set(range(n))
    first = int(np.argmax(q_sims))
    selected.append(first)
    candidates.remove(first)
    while len(selected) < k and candidates:
        best_idx = None
        best_score = -1e9
        for i in candidates:
            max_sim_to_selected = max(d_sims[i, j] for j in selected) if selected else 0.0
            score = lambda_param * q_sims[i] - (1.0 - lambda_param) * max_sim_to_selected
            if score > best_score:
                best_score = score
                best_idx = i
        selected.append(best_idx)
        candidates.remove(best_idx)
    return selected

async def get_documents(query, index, embed_model, cohere_client, alpha=0.5, top_k=8):
    """
    Get documents with optimized query embedding caching to avoid redundant encode() calls.

    Production Issue: Previously made 5+ separate embedding calls per query due to:
    - Initial hybrid search
    - Fallback without metadata filter
    - Refill operations
    - Secondary hybrid searches

    Fix: Cache query embeddings at the start and reuse throughout the function.
    """
    try:
        # ⚡ PERFORMANCE FIX: Pre-compute query embeddings once and reuse
        # This prevents 5+ redundant embedding calls seen in production
        logger.info(f"🔄 Pre-computing query embeddings to avoid redundant encode() calls")
        query_dense_embeddings, query_sparse_embeddings = get_query_embeddings(query, embed_model)

        def get_hybrid_results_cached(index, alpha: float, top_k: int, metadata_filter: Optional[Dict] = None):
            """Use cached query embeddings instead of re-encoding."""
            import time
            t_total = time.perf_counter()

            t_query = time.perf_counter()
            result = issue_hybrid_query(
                index,
                query_sparse_embeddings[0],
                query_dense_embeddings[0],
                alpha,
                top_k,
                metadata_filter
            )

            query_ms = int((time.perf_counter() - t_query) * 1000)
            total_ms = int((time.perf_counter() - t_total) * 1000)
            logger.info(f"dep=hybrid_search embed_ms=0 query_ms={query_ms} total_ms={total_ms}")  # embed_ms=0 since cached

            return result
        from langsmith import trace

        # Main retrieval trace
        with trace(name="hybrid_search"):
            logger.debug(f"Starting hybrid search for query: {query}")
            from src.data.config.config import RETRIEVAL_CONFIG
            FILTERS_CONFIG = RETRIEVAL_CONFIG.get("filters", {})
            BOOSTS_CONFIG = RETRIEVAL_CONFIG.get("boosts", {})
            # Build optional metadata filter
            meta_filter: Optional[Dict] = None
            try:
                lang_filter = FILTERS_CONFIG.get("lang")
                if lang_filter:
                    # Only apply if index has 'lang' metadata; otherwise the server ignores
                    meta_filter = {"lang": {"$eq": lang_filter}}
            except Exception:
                meta_filter = None

            overfetch = int(RETRIEVAL_CONFIG.get("overfetch", max(top_k, 8)))
            hybrid_results = get_hybrid_results_cached(
                index,
                alpha=alpha,
                top_k=int(overfetch),
                metadata_filter=meta_filter,
            )
            logger.debug(f"Retrieved {len(hybrid_results.matches)} matches from hybrid search")

            # Process search results into document format
            docs = process_search_results(hybrid_results)

            # Fallback: if server-side lang filter returned 0 docs, retry without filter
            filter_fallback_used = False
            if not docs and meta_filter:
                hybrid_results = get_hybrid_results_cached(
                    index,
                    alpha=alpha,
                    top_k=int(overfetch),
                    metadata_filter=None,
                )
                docs = process_search_results(hybrid_results)
                filter_fallback_used = True
            if not docs:
                logger.warning("No documents with content found")
                return []

            # Apply domain boosts and soft boosts before gating (small positive nudges)
            try:
                docs = _apply_domain_boosts(
                    docs,
                    BOOSTS_CONFIG.get("preferred_domains", []),
                    float(BOOSTS_CONFIG.get("domain_boost_weight", 0.0)),
                )
            except Exception:
                pass
            docs = _apply_soft_boosts(query, docs, BOOSTS_CONFIG.get("doc_type_boost_weight", 0.05), BOOSTS_CONFIG.get("topic_boost_weight", 0.03))

            # Audience blocklist (title + first 512 chars + domain)
            docs, blocked_base, blocked_text_only_base = _apply_audience_blocklist(docs)

            logger.debug(f"Processed {len(docs)} documents")

        # Optional pre-filter by Pinecone score (if configured)
        try:
            min_pinecone_score = RETRIEVAL_CONFIG.get("min_pinecone_score")
            max_before_rerank = int(RETRIEVAL_CONFIG.get("max_docs_before_rerank", 8))
            final_max_docs = int(RETRIEVAL_CONFIG.get("top_k_rerank", RETRIEVAL_CONFIG.get("final_max_docs", 5)))
            log_diag = bool(RETRIEVAL_CONFIG.get("log_retrieval_diagnostics", True))
            # New knobs
            base_t = float(RETRIEVAL_CONFIG.get("similarity_base", 0.55))
            fallback_t = float(RETRIEVAL_CONFIG.get("similarity_fallback", 0.55))
            adaptive_cfg_val = RETRIEVAL_CONFIG.get("adaptive_margin", {"enabled": True, "min": 0.04, "max": 0.10})
            # Backward compatibility: allow float adaptive_margin
            if isinstance(adaptive_cfg_val, dict):
                adaptive_cfg = adaptive_cfg_val
            else:
                try:
                    val = float(adaptive_cfg_val)
                except Exception:
                    val = 0.10
                adaptive_cfg = {"enabled": True, "min": val, "max": val}
            min_kept = int(RETRIEVAL_CONFIG.get("min_kept", 3))
            refill_enabled = bool(RETRIEVAL_CONFIG.get("refill_enabled", False))
            refill_overfetch = int(RETRIEVAL_CONFIG.get("refill_overfetch", 6))
            mmr_enabled = bool(RETRIEVAL_CONFIG.get("mmr_enabled", True))
            mmr_lambda = float(RETRIEVAL_CONFIG.get("mmr_lambda", 0.30))
            mmr_overfetch = int(RETRIEVAL_CONFIG.get("mmr_overfetch", 12))
        except Exception:
            min_pinecone_score = None
            max_before_rerank = 10
            final_max_docs = 5
            log_diag = True
            base_t = 0.65
            fallback_t = 0.55
            adaptive_cfg = {"enabled": True, "min": 0.04, "max": 0.10}
            min_kept = 3
            refill_enabled = True
            refill_overfetch = 10
            mmr_enabled = True
            mmr_lambda = 0.30
            mmr_overfetch = 12

        if min_pinecone_score is not None:
            before = len(docs)
            docs = [d for d in docs if isinstance(d.get('score'), (int, float)) and d['score'] >= float(min_pinecone_score)]
            if log_diag:
                logger.info(f"Filter by Pinecone score ≥ {min_pinecone_score}: {before} -> {len(docs)}")

        # 2) Similarity gating (base threshold + adaptive margin on pinecone_score)
        sims = [float(d.get('pinecone_score', d.get('score', 0.0))) for d in docs]
        max_s = max(sims) if sims else 0.0
        topN = sorted(sims, reverse=True)[:max(20, len(sims))]
        def _perc(a, p):
            if not a:
                return 0.0
            idx = max(0, min(len(a)-1, int(round(p * (len(a)-1)))))
            return a[idx]
        max_sim_pre = max(topN) if topN else 0.0
        p50_sim_pre = _perc(sorted(topN), 0.50)
        p95_sim_pre = _perc(sorted(topN), 0.95)
        if bool(adaptive_cfg.get("enabled", True)):
            delta = 0.5 * max(0.0, (p95_sim_pre - p50_sim_pre))
            delta = min(float(adaptive_cfg.get("max", 0.10)), max(float(adaptive_cfg.get("min", 0.04)), float(delta)))
        else:
            delta = float(adaptive_cfg.get("max", 0.10))

        if max_s < base_t:
            kept_pre = [d for d in docs if float(d.get('pinecone_score', d.get('score', 0.0))) >= (max_sim_pre - float(delta))]
        else:
            kept_pre = [d for d in docs if (
                float(d.get('pinecone_score', d.get('score', 0.0))) >= base_t and
                float(d.get('pinecone_score', d.get('score', 0.0))) >= (max_sim_pre - float(delta))
            )]
        kept_pre = kept_pre[:max(final_max_docs, 10)]
        kept_after_gate_pre = len(kept_pre)

        pool = kept_pre
        refill_count = 0
        refill_triggered = False
        if refill_enabled and len(kept_pre) < min_kept:
            # Re-query hybrid with overfetch for refill
            refill_results = get_hybrid_results_cached(
                index,
                alpha=alpha,
                top_k=int(overfetch) + int(refill_overfetch),
                metadata_filter=meta_filter,
            )
            refill_docs = process_search_results(refill_results)
            if not refill_docs and meta_filter:
                # fallback without filter
                refill_results = get_hybrid_results_cached(
                    index,
                    alpha=alpha,
                    top_k=int(overfetch) + int(refill_overfetch),
                    metadata_filter=None,
                )
                refill_docs = process_search_results(refill_results)
            # apply same boosts to refill docs
            try:
                refill_docs = _apply_domain_boosts(
                    refill_docs,
                    BOOSTS_CONFIG.get("preferred_domains", []),
                    float(BOOSTS_CONFIG.get("domain_boost_weight", 0.0)),
                )
            except Exception:
                pass
            # soft boosts and audience blocklist
            refill_docs = _apply_soft_boosts(query, refill_docs, BOOSTS_CONFIG.get("doc_type_boost_weight", 0.05), BOOSTS_CONFIG.get("topic_boost_weight", 0.03))
            refill_docs, blocked_refill, blocked_text_only_refill = _apply_audience_blocklist(refill_docs)
            pool = _dedup_by_title_url(docs + refill_docs)
            pool.sort(key=lambda x: float(x.get('score', 0.0)), reverse=True)
            pool = [d for d in pool if float(d.get('score', 0.0)) >= fallback_t]
            refill_count = max(0, len(pool) - kept_after_gate_pre)
            refill_triggered = True
            # If still short, top up ignoring threshold to reach at least max_before_rerank
            if len(pool) < max_before_rerank:
                for d in docs:
                    if d not in pool:
                        pool.append(d)
                        if len(pool) >= max_before_rerank:
                            break

        if not pool:
            pool = docs

        # Loosen pre-gate for how-to intents to give reranker material
        if _is_howto_query(query) and len(pool) < 8:
            by_sim = sorted(docs, key=lambda x: float(x.get('pinecone_score', x.get('score', 0.0))), reverse=True)[:8]
            pool = _dedup_by_title_url(pool + by_sim)

        # 3) MMR diversification on overfetch pool
        mmr_pool = pool[:max(mmr_overfetch, len(pool))]
        if mmr_enabled and len(mmr_pool) > 1:
            # Prefer index-returned vectors or cached embeddings to avoid re-embedding
            t_mmr = time.perf_counter()
            doc_vecs_list: List[List[float]] = [None] * len(mmr_pool)
            used_index = used_cache = 0
            to_embed_indices: List[int] = []
            for i, d in enumerate(mmr_pool):
                v = d.get('values') or d.get('vector') or d.get('dense')
                if isinstance(v, list) and v and isinstance(v[0], (int, float)):
                    doc_vecs_list[i] = v; used_index += 1; continue
                key = d.get('segment_id') or d.get('id')
                if not key:
                    try:
                        key = hashlib.sha1((d.get('content') or '').encode('utf-8')).hexdigest()
                    except Exception:
                        key = None
                cached = _EMB_CACHE.get(key)
                if cached is not None:
                    doc_vecs_list[i] = cached; used_cache += 1
                else:
                    to_embed_indices.append(i)
            if to_embed_indices:
                texts = [(mmr_pool[i].get('content') or '') for i in to_embed_indices]
                try:
                    emb_out = embed_model.encode(texts, return_dense=True, return_sparse=False, return_colbert_vecs=False)
                    dense_list = emb_out['dense_vecs']
                    for idx, vec in zip(to_embed_indices, dense_list):
                        doc_vecs_list[idx] = vec
                        k = mmr_pool[idx].get('segment_id') or mmr_pool[idx].get('id')
                        if not k:
                            try:
                                k = hashlib.sha1((mmr_pool[idx].get('content') or '').encode('utf-8')).hexdigest()
                            except Exception:
                                k = None
                        _EMB_CACHE.put(k, vec)
                except Exception as e:
                    logger.warning(f"MMR document embedding failed (will skip these docs): {str(e)[:120]}")
                    # Leave corresponding doc_vecs_list entries as None - they'll be filtered out
            # Filter out None values before creating numpy array
            valid_vecs = [v for v in doc_vecs_list if v is not None]
            if not valid_vecs:
                logger.warning(f"MMR: No valid vectors found for {len(mmr_pool)} documents, skipping MMR")
                pool = mmr_pool[:int(max_before_rerank)]
            else:
                doc_vecs = np.array(valid_vecs, dtype=float)
                # Map back to original pool indices for valid vectors only
                valid_indices = [i for i, v in enumerate(doc_vecs_list) if v is not None]
                mmr_pool_valid = [mmr_pool[i] for i in valid_indices]
                # Query embedding (dense) - reuse pre-computed embeddings
                t_q = time.perf_counter()
                q_dense = query_dense_embeddings  # Use cached embeddings
                q_embed_ms = int((time.perf_counter()-t_q)*1000)  # Should be ~0ms since cached
                mmr_ms = int((time.perf_counter() - t_mmr) * 1000)
                logger.info(
                    f"dep=mmr_embed used_index={used_index} used_cache={used_cache} embedded={len(to_embed_indices)} ms={mmr_ms} n_docs={len(mmr_pool)} valid_vecs={len(valid_vecs)} q_embed_ms={q_embed_ms}"
                )
                q_vec = np.array(q_dense[0], dtype=float)
                sel_idx = _mmr_select_indices(q_vec, doc_vecs, float(mmr_lambda), int(max_before_rerank))
                # Map selected indices back to original mmr_pool
                pool = [mmr_pool_valid[i] for i in sel_idx]

        # Trim pool size before rerank to reduce latency
        pre_final = pool[:max_before_rerank]

        # 4) Cross-encoder rerank
        with trace(name="document_reranking"):
            loop = asyncio.get_event_loop()
            reranked_docs = await loop.run_in_executor(
                None,
                rerank_fcn,
                query,
                pre_final,
                min(len(pre_final), max(final_max_docs, 10)),
                cohere_client,
            )

            if not reranked_docs:
                logger.warning("No documents after reranking")
                return []

            # Percentile-based floor per query (clamped) with quota and guaranteed backfill
            scored = [(d, float(d.get('score', 0.0))) for d in reranked_docs]
            scores_arr = np.array([s for _, s in scored], dtype=float)
            p20 = float(np.quantile(scores_arr, 0.20)) if scores_arr.size else 0.0
            HARD_FLOOR = float(RETRIEVAL_CONFIG.get('hard_floor', 0.60))
            floor_used = max(HARD_FLOOR, p20)
            floor_used = min(floor_used, 0.95)
            MIN_ABOVE = 3
            keepers = [(d, s) for d, s in scored if s >= floor_used]
            if len(keepers) < MIN_ABOVE and scores_arr.size:
                soft_floor = max(HARD_FLOOR, float(np.quantile(scores_arr, 0.10)))
                floor_used = min(floor_used, soft_floor)
                keepers = [(d, s) for d, s in scored if s >= floor_used]

            final_docs = [d for d, _ in keepers][:final_max_docs]
            final_before = len(final_docs)
            if len(final_docs) < final_max_docs:
                final_docs += [d for d, _ in scored if d not in final_docs][:final_max_docs - len(final_docs)]

            # Ensure-K: if still short, run a secondary hybrid refill (wider) and rerank again
            final_after = len(final_docs)
            hybrid_refill = 0
            if len(final_docs) < final_max_docs:
                # 2a) Sparse-only (BM25-like) fallback
                sec_results_sparse = get_sparse_results(
                    index,
                    query,
                    embed_model,
                    top_k=int(overfetch) + int(refill_overfetch) + 50,
                    metadata_filter=None,
                )
                sec_docs_sparse = process_search_results(sec_results_sparse)
                # 2b) Hybrid widened as additional supplement
                sec_results_hybrid = get_hybrid_results_cached(
                    index,
                    alpha=alpha,
                    top_k=int(overfetch) + int(refill_overfetch) + 20,
                    metadata_filter=None,
                )
                sec_docs_hybrid = process_search_results(sec_results_hybrid)
                sec_docs = sec_docs_sparse + sec_docs_hybrid
                try:
                    sec_docs = _apply_domain_boosts(
                        sec_docs,
                        BOOSTS_CONFIG.get("preferred_domains", []),
                        float(BOOSTS_CONFIG.get("domain_boost_weight", 0.0)),
                    )
                except Exception:
                    pass
                sec_docs = _apply_soft_boosts(query, sec_docs, BOOSTS_CONFIG.get("doc_type_boost_weight", 0.05), BOOSTS_CONFIG.get("topic_boost_weight", 0.03))
                sec_docs, _, _ = _apply_audience_blocklist(sec_docs)

                merged = _dedup_by_title_url(pre_final + [d for d, _ in scored] + sec_docs)
                # Re-rerank merged
                rescored = await loop.run_in_executor(
                    None,
                    rerank_fcn,
                    query,
                    merged,
                    min(len(merged), max(final_max_docs, 10)),
                    cohere_client,
                )
                rescored_scored = [(d, float(d.get('score', 0.0))) for d in rescored]
                resc_scores_arr = np.array([s for _, s in rescored_scored], dtype=float)
                # Reuse same floor logic
                p20b = float(np.quantile(resc_scores_arr, 0.20)) if resc_scores_arr.size else 0.0
                floor_b = max(HARD_FLOOR, p20b)
                floor_b = min(floor_b, 0.95)
                keepers_b = [(d, s) for d, s in rescored_scored if s >= floor_b]
                if len(keepers_b) < MIN_ABOVE and resc_scores_arr.size:
                    soft_b = max(HARD_FLOOR, float(np.quantile(resc_scores_arr, 0.10)))
                    floor_b = min(floor_b, soft_b)
                    keepers_b = [(d, s) for d, s in rescored_scored if s >= floor_b]
                # Keep what we already had if present
                keep_existing = [d for d in final_docs if d in [d2 for d2, _ in rescored_scored]]
                rest = [d for d, _ in rescored_scored if d not in keep_existing]
                final_docs = (keep_existing + rest)[:final_max_docs]
                hybrid_refill = max(0, final_max_docs - final_before)

            logger.debug(f"Final document count: {len(final_docs)}")

            if log_diag:
                try:
                    # Top dropped under the floor (for debugging)
                    dropped_candidates = sorted([(d, s) for d, s in scored if s < floor_used], key=lambda x: x[1], reverse=True)[:2]
                    dropped_top2 = [
                        {
                            'segment_id': d.get('segment_id', ''),
                            'title': d.get('title', '')[:80],
                            'score': float(s),
                        }
                        for d, s in dropped_candidates
                    ]
                    preview = [
                        {
                            'title': d.get('title', '')[:80],
                            'pinecone_score': d.get('pinecone_score', d.get('score')),
                            'rerank_score': d.get('score'),
                            'has_values': bool(d.get('values') or d.get('vector') or d.get('dense')),
                        }
                        for d in final_docs
                    ]
                    logger.info(f"Retained docs preview: {preview}")
                    # Additional one-line metrics
                    logger.info(
                        f"q='{query[:60]}', base={len(docs)}, kept_pre={kept_after_gate_pre}, refill={refill_count}, final_before={final_before}, final_after={len(final_docs)}, hybrid_refill={hybrid_refill}, floor={floor_used:.2f}, delta={delta:.3f}, max_sim_pre={max_sim_pre:.3f}, p50_sim_pre={p50_sim_pre:.3f}, p95_sim_pre={p95_sim_pre:.3f}, blocked_base={locals().get('blocked_base',0)}, dropped_top2={dropped_top2}"
                    )

                    # Optional JSONL export of diagnostics (off by default; enable with ENABLE_LOCAL_CHAT_LOGS)
                    try:
                        if str(os.environ.get("ENABLE_LOCAL_CHAT_LOGS", "")).strip().lower() in ("1", "true", "yes"):
                            export_dir = os.path.join(os.getcwd(), "logs")
                            os.makedirs(export_dir, exist_ok=True)
                            export_path = os.path.join(export_dir, "retrieval_app_debug.jsonl")
                            rec = {
                            "query": query,
                            "base_docs": len(docs),
                            "kept_pre": kept_after_gate_pre,
                            "refill_count": refill_count,
                            "final_before": final_before,
                            "final_after": len(final_docs),
                            "hybrid_refill": hybrid_refill,
                            "floor_used": float(floor_used),
                            "delta": float(delta),
                            "max_sim_pre": float(max_sim_pre),
                            "p50_sim_pre": float(p50_sim_pre),
                            "p95_sim_pre": float(p95_sim_pre),
                            "retained": [
                                {
                                    "title": d.get('title', ''),
                                    "pinecone_score": float(d.get('pinecone_score', d.get('score', 0.0))),
                                    "rerank_score": float(d.get('score', 0.0)),
                                    "url": d.get('url', []),
                                }
                                for d in final_docs
                            ],
                            "dropped_top2": dropped_top2,
                        }
                            import json
                            with open(export_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    except Exception:
                        pass
                except Exception:
                    pass

        return final_docs

    except Exception as e:
        logger.error(f"Error in get_documents: {str(e)}")
        raise

def clean_markdown_content(content: str) -> str:
    """Clean markdown formatting from content."""
    import re

    # Remove markdown table header and separator rows
    content = re.sub(r'\|[- |]+\|', '', content)

    # Extract meaningful text from table rows
    table_texts = []
    for line in content.split('\n'):
        if line.strip().startswith('|'):
            # Extract text between pipes, remove leading/trailing whitespace
            cells = [cell.strip() for cell in line.split('|')]
            # Filter out empty cells and join meaningful text
            meaningful_cells = [cell for cell in cells if cell and not cell.isspace()]
            if meaningful_cells:
                table_texts.append(' '.join(meaningful_cells))

    # If we found table text, join it together
    if table_texts:
        content = ' '.join(table_texts)

    # Remove multiple newlines and spaces
    content = re.sub(r'\n+', ' ', content)
    content = re.sub(r'\s+', ' ', content)

    # Clean up specific characters
    content = (content.replace('\\n', ' ')
              .replace('\\"', '"')
              .replace('\\\'', "'")
              .replace('\\_{', '_')
              .replace('\\', '')  # Remove remaining backslashes
              .strip())

    return content

def process_search_results(search_results) -> List[Dict]:
    """
    Process search results into a standardized format with deduplication and content cleaning.
    """
    processed_docs = []
    seen_titles = set()  # For deduplication

    for match in search_results.matches:
        try:
            # Extract metadata
            title = match.metadata.get('title', 'No Title')

            # Skip if we've seen this title
            if title in seen_titles:
                continue

            # Get and clean content
            content = match.metadata.get('chunk_text', '')
            if not content:
                logger.warning(f"No content found for document: {title}")
                continue

            # Clean content
            content = clean_markdown_content(content)

            # Skip if content is too short after cleaning
            if len(content.strip()) < 10:
                logger.warning(f"Content too short after cleaning for document: {title}")
                continue

            # Normalize title
            norm_title = normalize_title(title, match.metadata.get('section_title', '').strip(), match.metadata.get('url', []))

            # Create document
            doc = {
                'title': norm_title,
                'content': content,
                # Keep raw Pinecone score, also alias to 'score' for backward compatibility
                'pinecone_score': float(match.score),
                'score': float(match.score),
                'section_title': match.metadata.get('section_title', '').strip(),
                'segment_id': match.metadata.get('segment_id', ''),
                'id': getattr(match, 'id', ''),
                'doc_keywords': match.metadata.get('doc_keywords', []),
                'segment_keywords': match.metadata.get('segment_keywords', []),
                'url': match.metadata.get('url', [])
            }
            # Attach vector values if returned
            try:
                # Try multiple ways to access vectors from Pinecone response
                vals = None
                if hasattr(match, '_data_store') and isinstance(match._data_store, dict):
                    vals = match._data_store.get('values')
                if not vals:
                    vals = getattr(match, 'values', None)

                if isinstance(vals, list) and vals and isinstance(vals[0], (int, float)):
                    doc['values'] = vals
                    logger.debug(f"Vector attached: len={len(vals)}")
                else:
                    logger.debug(f"No valid vector found: type={type(vals)}, len={len(vals) if vals else 0}")
            except Exception as e:
                logger.debug(f"Vector extraction error: {e}")
                pass

            processed_docs.append(doc)
            seen_titles.add(title)
            logger.debug(f"Successfully processed document: {title}")

        except Exception as e:
            logger.warning(f"Error processing match: {str(e)}")
            continue

    return processed_docs

def format_document_output(doc: Dict) -> str:
    """Format document for display with better content preview."""
    output = [
        f"\nDocument:",
        f"Title: {doc['title']}",
        f"Score: {doc['score']:.3f}",
        f"Section: {doc['section_title']}",
    ]

    # Add keywords if available
    if doc['doc_keywords']:
        output.append(f"Keywords: {', '.join(doc['doc_keywords'][:5])}...")

    # Add clean content preview with better truncation
    content = doc['content']
    if len(content) > 300:
        # Try to break at a sentence or punctuation
        breakpoints = ['. ', '? ', '! ', '; ', ', ']
        truncated = False
        for point in breakpoints:
            last_point = content[:300].rfind(point)
            if last_point > 0:
                content = content[:last_point + 1]
                truncated = True
                break
        if not truncated:
            # If no good breakpoint found, break at word boundary
            content = content[:300].rsplit(' ', 1)[0]
        content += "..."

    output.append(f"\nContent preview: {content}")

    # Add source if available
    if doc['url'] and doc['url'][0]:
        output.append(f"Source: {doc['url'][0]}")

    return "\n".join(output)

async def test_retrieval():
    """Test the document retrieval process"""
    try:
        # Initialize
        print("\n=== Testing Document Retrieval ===")
        load_environment()

        PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
        COHERE_API_KEY = os.getenv('COHERE_API_KEY')
        if not PINECONE_API_KEY or not COHERE_API_KEY:
            raise ValueError("Missing required API keys in environment")

        # Setup
        print("\nInitializing components...")
        pc = Pinecone(api_key=PINECONE_API_KEY)
        # Reuse Pinecone Index; log the host once
        index_name = os.getenv("PINECONE_INDEX_NAME", "climate-change-adaptation-index-10-24-prod")
        index = pc.Index(index_name)
        try:
            host = getattr(index, "host", None) or getattr(index, "_host", "unknown")
            logger.info(f"dep=pinecone host={host} op=init status=OK")
        except Exception:
            pass
        import cohere
        cohere_client = cohere.Client(COHERE_API_KEY)

        # Initialize embedding model
        embed_model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=False)

        # Test query
        query = "What is climate change?"
        print(f"\nProcessing query: {query}")

        # Get results using async function
        start_time = time.time()
        docs = await get_documents(query, index, embed_model, cohere_client)
        search_time = time.time() - start_time

        # Display results
        print(f"\nRetrieved and processed {len(docs)} documents in {search_time:.2f} seconds:")

        for doc in docs:
            print(format_document_output(doc))
            print("-" * 80)

        return docs

    except Exception as e:
        logger.error(f"Error in test_retrieval: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(test_retrieval())
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
    finally:
        print("\nScript execution completed")