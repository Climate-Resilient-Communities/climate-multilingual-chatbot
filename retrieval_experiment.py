#!/usr/bin/env python3
"""
Experimental retrieval flow test:
  1) Vector/hybrid search (BGE-M3 dense + sparse to Pinecone)
  2) Similarity gating with base threshold and adaptive margin
  3) Hybrid refill if < MIN_KEPT
  4) MMR diversification (overfetch then select K)
  5) Cross-encoder rerank (Cohere) and finalize (drop low rerank, backfill)

This script does NOT modify app logic; it's a test harness to evaluate the flow.
"""

import os
import sys
import math
import time
import asyncio
from typing import List, Dict, Any, Tuple, Optional
import re

import numpy as np

# Local imports (reuse app initialization paths)
from src.utils.env_loader import load_environment
from src.data.config.config import RETRIEVAL_CONFIG
from src.models.climate_pipeline import ClimateQueryPipeline
from src.models.retrieval import (
    get_hybrid_results,
    process_search_results,
    get_query_embeddings,
)
from src.models.rerank import rerank_fcn


# Config knobs (can be moved to RETRIEVAL_CONFIG if promoted later)
K = 5
BASE_T = float(os.getenv("EXPT_BASE_T", "0.55"))
FALLBACK_T = float(os.getenv("EXPT_FALLBACK_T", "0.55"))
ADAPTIVE_MARGIN = float(os.getenv("EXPT_ADAPTIVE_MARGIN", "0.10"))
MIN_KEPT = int(os.getenv("EXPT_MIN_KEPT", "3"))
ALPHA_PRIMARY = float(os.getenv("EXPT_ALPHA_PRIMARY", "0.5"))  # hybrid dense/sparse weight
REFILL_OVERFETCH = int(os.getenv("EXPT_REFILL_OVERFETCH", "10"))
MMR_LAMBDA = float(os.getenv("EXPT_MMR_LAMBDA", "0.30"))
MMR_OVERFETCH = int(os.getenv("EXPT_MMR_OVERFETCH", "20"))
MIN_RERANK = float(os.getenv("EXPT_MIN_RERANK", "0.60"))


def _dedup_by_title_url(docs: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for d in docs:
        key = (d.get("title", "").strip().lower(), str(d.get("url", [None])[0]).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def mmr_select(docs: List[Dict], query_emb: np.ndarray, doc_embs: np.ndarray, lambda_param: float, k: int) -> List[int]:
    """Return indices of selected docs using MMR.
    docs: list of docs (len N)
    query_emb: (D,)
    doc_embs: (N, D)
    """
    n = len(docs)
    if n <= k:
        return list(range(n))

    # Precompute sims
    q_sims = np.array([_cosine_sim(query_emb, doc_embs[i]) for i in range(n)])
    d_sims = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            s = _cosine_sim(doc_embs[i], doc_embs[j])
            d_sims[i, j] = s
            d_sims[j, i] = s

    selected = []
    candidates = set(range(n))
    # Pick the best by query sim first
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


def _extract_domain(url_value: Any) -> str:
    try:
        url_str = url_value[0] if isinstance(url_value, list) else url_value
        from urllib.parse import urlparse
        parsed = urlparse(str(url_str))
        host = parsed.netloc or ""
        return host.lower().lstrip('www.')
    except Exception:
        return ""


def _apply_domain_boosts(docs: List[Dict], preferred_domains: List[str], weight: float) -> List[Dict]:
    if not preferred_domains or weight <= 0:
        return docs
    boosted = []
    for d in docs:
        dom = _extract_domain(d.get('url', []))
        score = float(d.get('score', 0.0))
        if any(pref in dom for pref in preferred_domains if isinstance(pref, str)):
            score += float(weight)
        boosted.append({**d, 'score': score})
    return boosted


def _apply_audience_blocklist(docs: List[Dict]) -> Tuple[List[Dict], int, int]:
    """Drop K-12/educational materials by regex on title/content and by domain guard."""
    try:
        cfg_blk = RETRIEVAL_CONFIG.get("filters", {}).get("audience_blocklist", [])
    except Exception:
        cfg_blk = []

    # Robust K–12 patterns
    grades = r'(?:K|Gr(?:ade)?s?)\s*(?:[-–]\s*)?(?:K|[0-9]{1,2})(?:\s*(?:[-–]\s*|to)\s*(?:K|[0-9]{1,2}))?'
    eduterms = r'(?:classroom|lesson\s*plan|curriculum|worksheet|teachers?|school|students?|grade\s*9|grade\s*nine|lesson\s*plans?)'
    k12_core = rf'(?:{grades}\s*(?:{eduterms})|{eduterms}.*{grades})'
    block_re = re.compile(
        rf'(?i)\b(?:{k12_core}|K-?\s?12|K\s*[-–]\s*12|Kindergarten|project\s+of\s+learning|learning\s+for\s+a\s+sustainable\s+future)\b'
    )

    # Accept extra raw substrings from config (case-insensitive)
    extra_substrings = [s.lower() for s in (cfg_blk or [])]

    # Lightweight domain block for known K–12 publishers
    k12_block_domains = {"lsf-lst.ca", "climatelearning.ca", "peelregion.ca"}

    filtered: List[Dict] = []
    blocked = 0
    blocked_text_only = 0

    for d in docs:
        title_l = (d.get("title", "") or "").lower()
        content_l_short = ((d.get("content", "") or "")[:512]).lower()
        url_val = d.get("url", [])
        domain = _extract_domain(url_val)

        title_hit = bool(block_re.search(title_l)) or any(x in title_l for x in extra_substrings)
        content_hit = bool(block_re.search(content_l_short)) or any(x in content_l_short for x in extra_substrings)
        domain_hit = any(dom in domain for dom in k12_block_domains) if domain else False

        if title_hit or content_hit or domain_hit:
            blocked += 1
            if (not title_hit) and content_hit:
                blocked_text_only += 1
            continue

        filtered.append(d)

    return filtered, blocked, blocked_text_only


HOWTO_QUERY_REGEX = re.compile(r"(how to|tips|at home|safety|cost|guide|checklist|prepare|kit)", re.I)
DOC_TYPE_HINTS = ["factsheet", "fact sheet", "guideline", "advisory", "toolkit", "checklist"]
EV_HINTS = ["evse", "level 2", "240v", "charger", "amperage", "nema", "csa", "breaker", "circuit"]
WEATHERIZE_HINTS = ["caulk", "weatherstrip", "r-value", "insulation", "window film", "storm window"]
HEAT_AQI_HINTS = ["aqi", "pm2.5", "n95", "cooling centre", "cooling center", "mist", "hydration"]


def _is_howto_query(query: str) -> bool:
    return bool(HOWTO_QUERY_REGEX.search(query))


def _apply_howto_constraint(query: str, docs: List[Dict]) -> Tuple[List[Dict], bool]:
    if not _is_howto_query(query):
        return docs, False
    query_l = query.lower()
    topic_keywords = []
    if any(k in query_l for k in ["ev", "charger", "charging"]):
        topic_keywords = EV_HINTS
    elif any(k in query_l for k in ["weather", "window", "insulat", "draft", "caulk", "weatherstrip"]):
        topic_keywords = WEATHERIZE_HINTS
    elif any(k in query_l for k in ["heat", "air quality", "aqi", "smoke", "wildfire"]):
        topic_keywords = HEAT_AQI_HINTS

    constrained = []
    for d in docs:
        t = (d.get("title", "") or "").lower()
        u = d.get("url", "")
        if isinstance(u, list):
            u = (u[0] if u else "")
        u = str(u).lower()
        c = (d.get("content", "") or "").lower()
        doc_type_match = any(h in t or h in u for h in DOC_TYPE_HINTS)
        topic_match = any(k.lower() in c for k in topic_keywords) if topic_keywords else False
        if doc_type_match or topic_match:
            constrained.append(d)
    if len(constrained) < 3:
        return docs, False
    return constrained[:max(K, 10)], True


def _apply_soft_boosts(query: str, docs: List[Dict], boost_doc_type: float = 0.05, boost_topic: float = 0.03) -> List[Dict]:
    if not docs:
        return docs
    ql = (query or "").lower()
    topic_keywords: List[str] = []
    if any(k in ql for k in ["ev", "charger", "charging"]):
        topic_keywords = EV_HINTS
    elif any(k in ql for k in ["weather", "window", "insulat", "draft", "caulk", "weatherstrip"]):
        topic_keywords = WEATHERIZE_HINTS
    elif any(k in ql for k in ["heat", "air quality", "aqi", "smoke", "wildfire"]):
        topic_keywords = HEAT_AQI_HINTS
    boosted: List[Dict] = []
    for d in docs:
        t = (d.get("title", "") or "").lower()
        u = d.get("url", "")
        if isinstance(u, list):
            u = (u[0] if u else "")
        u = str(u).lower()
        c = (d.get("content", "") or "").lower()
        s = float(d.get("score", 0.0))
        if _is_howto_query(query) and any(h in t or h in u for h in DOC_TYPE_HINTS):
            s += boost_doc_type
        if topic_keywords and any(k in c for k in topic_keywords):
            s += boost_topic
        boosted.append({**d, "score": s})
    return boosted


def finalize_with_floor_and_backfill(query: str, reranked: List[Dict], K: int, *, MIN_RERANK: float = 0.60, MIN_ABOVE: int = 3) -> Tuple[List[Dict], float, int, float, float, float]:
    """Apply clamped percentile floor + quota; always backfill to K from rerank order.
    Returns: (final_docs, floor_used, above_floor, p20, p10, p95)
    """
    import numpy as np

    scores = np.array([float(d.get("score", 0.0)) for d in reranked], dtype=float)
    if scores.size == 0:
        return [], float(MIN_RERANK), 0, 0.0, 0.0, 0.0

    p20 = float(np.quantile(scores, 0.20))
    p10 = float(np.quantile(scores, 0.10))
    p95 = float(np.quantile(scores, 0.95))
    floor_used = min(0.95, max(MIN_RERANK, p20))

    keepers = [d for d in reranked if float(d.get("score", 0.0)) >= floor_used]

    # Quota: ensure at least MIN_ABOVE above the floor; if not, soften to max(MIN_RERANK, p10)
    if len(keepers) < MIN_ABOVE:
        floor_used = min(floor_used, max(MIN_RERANK, p10))
        keepers = [d for d in reranked if float(d.get("score", 0.0)) >= floor_used]

    # Take top-K of keepers, then ALWAYS backfill to K from reranked order
    final_docs = keepers[:K]
    if len(final_docs) < K:
        final_docs += [d for d in reranked if d not in final_docs][:K - len(final_docs)]

    return final_docs, float(floor_used), int(len(keepers)), float(p20), float(p10), float(p95)


async def run_experiment_for_query(query: str) -> Dict[str, Any]:
    load_environment()
    index_name = os.getenv("PINECONE_INDEX", RETRIEVAL_CONFIG.get("pinecone_index", None))
    pipeline = ClimateQueryPipeline(index_name=index_name)
    index = pipeline.index
    embed_model = pipeline.embed_model
    cohere_client = pipeline.cohere_client

    # Optional metadata filter and boosts to match app config
    meta_filter: Optional[Dict] = None
    try:
        cfg_filters = RETRIEVAL_CONFIG.get("filters", {})
        lang_filter = cfg_filters.get("lang")
        if lang_filter:
            meta_filter = {"lang": {"$eq": lang_filter}}
    except Exception:
        meta_filter = None
    boosts = RETRIEVAL_CONFIG.get("boosts", {})

    # 1) primary hybrid search (overfetch)
    raw = get_hybrid_results(index, query, embed_model, alpha=ALPHA_PRIMARY, top_k=max(30, K), metadata_filter=meta_filter)
    base_docs = process_search_results(raw)
    filter_fallback_used = False
    if not base_docs and meta_filter:
        # Fallback: rerun without server-side filter if it returned 0
        raw = get_hybrid_results(index, query, embed_model, alpha=ALPHA_PRIMARY, top_k=max(30, K), metadata_filter=None)
        base_docs = process_search_results(raw)
        filter_fallback_used = True
    if not base_docs:
        return {"query": query, "stage": "no_docs", "final": []}

    # Optional domain boosts and audience blocklist
    if boosts:
        base_docs = _apply_domain_boosts(
            base_docs,
            boosts.get("preferred_domains", []),
            float(boosts.get("domain_boost_weight", 0.0)),
        )
    # Soft boosts for how-to/topic relevance prior to gating
    base_docs = _apply_soft_boosts(query, base_docs)
    # Audience blocklist (by title/content + domain)
    base_docs, blocked_base, blocked_text_only_base = _apply_audience_blocklist(base_docs)

    # 2) similarity gating (distribution-driven margin) with diagnostics
    sims = [float(d.get("pinecone_score", d.get("score", 0.0))) for d in base_docs]
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
    delta_raw = 0.5 * max(0.0, (p95_sim_pre - p50_sim_pre))
    delta = min(0.10, max(0.04, delta_raw))
    if max_s < BASE_T:
        kept = [d for d in base_docs if float(d.get("pinecone_score", d.get("score", 0.0))) >= (max_sim_pre - delta)]
    else:
        kept = [d for d in base_docs if (
            float(d.get("pinecone_score", d.get("score", 0.0))) >= BASE_T and
            float(d.get("pinecone_score", d.get("score", 0.0))) >= (max_sim_pre - delta)
        )]
    kept = kept[:max(K, 10)]
    kept_after_gate_pre = len(kept)

    # Loosen pre-gate for how-to intents to give reranker material
    howto_min_pre_applied = False
    MIN_PRE_HOWTO = 8
    if _is_howto_query(query) and len(kept) < MIN_PRE_HOWTO:
        by_sim = sorted(base_docs, key=lambda x: float(x.get("pinecone_score", x.get("score", 0.0))), reverse=True)[:MIN_PRE_HOWTO]
        # Union and dedup
        kept = _dedup_by_title_url(kept + by_sim)
        howto_min_pre_applied = True
    kept_pre_after_loosen = len(kept)

    # 3) hybrid refill if needed
    refill_count = 0
    refill_triggered = False
    if len(kept) < MIN_KEPT:
        refill_raw = get_hybrid_results(index, query, embed_model, alpha=ALPHA_PRIMARY, top_k=max(30, K) + REFILL_OVERFETCH, metadata_filter=meta_filter)
        refill_docs = process_search_results(refill_raw)
        if not refill_docs and meta_filter:
            refill_raw = get_hybrid_results(index, query, embed_model, alpha=ALPHA_PRIMARY, top_k=max(30, K) + REFILL_OVERFETCH, metadata_filter=None)
            refill_docs = process_search_results(refill_raw)
        if boosts:
            refill_docs = _apply_domain_boosts(
                refill_docs,
                boosts.get("preferred_domains", []),
                float(boosts.get("domain_boost_weight", 0.0)),
            )
        # Soft boosts for how-to/topic relevance prior to pool merge
        refill_docs = _apply_soft_boosts(query, refill_docs)
        # Apply blocklist to refill docs
        refill_docs, blocked_refill, blocked_text_only_refill = _apply_audience_blocklist(refill_docs)
        pool = _dedup_by_title_url(base_docs + refill_docs)
        pool = sorted(pool, key=lambda x: float(x.get("score", 0.0)), reverse=True)
        kept = [d for d in pool if float(d.get("score", 0.0)) >= FALLBACK_T][:max(K, len(kept))]
        refill_count = max(0, len(kept) - kept_after_gate_pre)
        refill_triggered = True
        if len(kept) < K:
            # if still short, top up ignoring threshold to reach K
            for d in pool:
                if d not in kept:
                    kept.append(d)
                    if len(kept) >= K:
                        break
    kept_after_gate_post = len(kept)

    # 4) MMR diversification on an overfetch pool
    pool_for_mmr = kept[:MMR_OVERFETCH] or base_docs[:MMR_OVERFETCH]
    q_norm = None
    doc_norm_med = None
    doc_norm_min = None
    doc_norm_max = None
    if len(pool_for_mmr) >= 2:
        doc_texts = [d.get("content", "") for d in pool_for_mmr]
        emb_out = embed_model.encode(doc_texts, return_dense=True, return_sparse=False, return_colbert_vecs=False)
        doc_vecs = emb_out["dense_vecs"]
        q_dense, _ = get_query_embeddings(query, embed_model)
        q_vec = np.array(q_dense[0], dtype=float)
        doc_embs = np.array(doc_vecs, dtype=float)
        # Norm diagnostics
        try:
            q_norm = float(np.linalg.norm(q_vec))
            norms = np.linalg.norm(doc_embs, axis=1)
            doc_norm_min = float(np.min(norms)) if norms.size else None
            doc_norm_max = float(np.max(norms)) if norms.size else None
            doc_norm_med = float(np.median(norms)) if norms.size else None
        except Exception:
            pass
        mmr_idx = mmr_select(pool_for_mmr, q_vec, doc_embs, MMR_LAMBDA, max(K, 10))
        mmr_docs = [pool_for_mmr[i] for i in mmr_idx]
    else:
        mmr_docs = pool_for_mmr
    # Diversity metric: avg pairwise cosine among MMR docs
    avg_pairwise_sim = 0.0
    if len(mmr_idx) > 1:
        pairs = 0
        sim_sum = 0.0
        for i in range(len(mmr_idx)):
            for j in range(i + 1, len(mmr_idx)):
                sim_sum += _cosine_sim(q_vec * 0 + doc_embs[mmr_idx[i]], q_vec * 0 + doc_embs[mmr_idx[j]])
                pairs += 1
        if pairs:
            avg_pairwise_sim = sim_sum / pairs

    # 5) Cross-encoder rerank and finalize
    # Combine kept + mmr (dedup), then rerank
    combined_pool = _dedup_by_title_url(kept + mmr_docs)
    # Apply audience blocklist once more and how-to constraint
    combined, blocked_prerank, blocked_text_only_prerank = _apply_audience_blocklist(combined_pool)
    constrained, constraint_applied = _apply_howto_constraint(query, combined)
    if constraint_applied and constrained:
        combined = constrained
    before_rerank = len(combined)
    rerank_model = "rerank-english-v3.0"
    reranked = rerank_fcn(query, combined, min(len(combined), max(K, 10)), cohere_client)
    # Use helper for clamp + quota + backfill
    final_docs, floor_used, above_floor, p20_rerank, p10_rerank, p95_rerank = finalize_with_floor_and_backfill(
        query, reranked, K, MIN_RERANK=MIN_RERANK, MIN_ABOVE=3
    )
    dropped_by_rerank = before_rerank - above_floor
    final_docs_before_count = min(K, above_floor)
    backfilled = max(0, K - final_docs_before_count)

    # 2nd pass: if still < K, do a hybrid refill → rerank → same finalize
    used_second_pass = False
    if len(final_docs) < K:
        refill_raw2 = get_hybrid_results(index, query, embed_model, alpha=ALPHA_PRIMARY, top_k=max(30, K) + REFILL_OVERFETCH, metadata_filter=meta_filter)
        refill_docs2 = process_search_results(refill_raw2)
        if not refill_docs2 and meta_filter:
            refill_raw2 = get_hybrid_results(index, query, embed_model, alpha=ALPHA_PRIMARY, top_k=max(30, K) + REFILL_OVERFETCH, metadata_filter=None)
            refill_docs2 = process_search_results(refill_raw2)
        if boosts:
            refill_docs2 = _apply_domain_boosts(
                refill_docs2,
                boosts.get("preferred_domains", []),
                float(boosts.get("domain_boost_weight", 0.0)),
            )
        refill_docs2 = _apply_soft_boosts(query, refill_docs2)
        refill_docs2, blocked_refill2, blocked_text_only_refill2 = _apply_audience_blocklist(refill_docs2)

        merged_pool = _dedup_by_title_url(combined + refill_docs2)
        reranked2 = rerank_fcn(query, merged_pool, min(len(merged_pool), max(K, 10)), cohere_client)
        final_docs2, floor_used2, above_floor2, p20_rerank2, p10_rerank2, p95_rerank2 = finalize_with_floor_and_backfill(
            query, reranked2, K, MIN_RERANK=MIN_RERANK, MIN_ABOVE=3
        )
        final_docs = final_docs2
        floor_used = floor_used2
        above_floor = above_floor2
        p20_rerank = p20_rerank2
        p10_rerank = p10_rerank2
        p95_rerank = p95_rerank2
        used_second_pass = True

    # Diagnostics: dropped top-2 (by score) under the floor
    scored = [(d, float(d.get("score", 0.0))) for d in reranked]
    dropped_candidates = sorted([(d, s) for d, s in scored if s < floor_used], key=lambda x: x[1], reverse=True)[:2]
    dropped_top2 = [
        {
            "segment_id": d.get("segment_id", ""),
            "title": d.get("title", "")[:120],
            "score": float(s),
        }
        for d, s in dropped_candidates
    ]

    # Quality-of-life: final_lt_k and stage
    final_lt_k = int(len(final_docs) < K)
    stage_final_lt_k = "post-rerank" if final_lt_k else ""

    # Summarize
    return {
        "query": query,
        "base_docs": len(base_docs),
        "kept_after_gate_pre": kept_after_gate_pre,
        "kept_pre_after_loosen": kept_pre_after_loosen,
        "howto_min_pre_applied": howto_min_pre_applied,
        "refill_count": refill_count,
        "kept_after_gate_post": kept_after_gate_post,
        "final_docs": len(final_docs),
        "final_before": final_docs_before_count,
        "final_titles": [d.get("title", "") for d in final_docs],
        "final_rerank_scores": [float(d.get("score", 0.0)) for d in final_docs],
        "dropped_by_rerank": dropped_by_rerank,
        "dropped_top2": dropped_top2,
        "avg_mmr_pairwise_sim": avg_pairwise_sim,
        "filter_fallback_used": filter_fallback_used,
        "max_sim_pre": max_sim_pre,
        "p50_sim_pre": p50_sim_pre,
        "p95_sim_pre": p95_sim_pre,
        "refill_triggered": refill_triggered,
        "reranker_model": rerank_model,
        "rerank_range": [float(min([s for _, s in scored], default=0.0)), float(max([s for _, s in scored], default=0.0))],
        "q_norm": q_norm,
        "doc_norm_med": doc_norm_med,
        "doc_norm_range": [doc_norm_min, doc_norm_max],
        "delta": delta,
        "p20_rerank": p20_rerank,
        "floor_used": floor_used,
        "above_floor": above_floor,
        "backfilled": backfilled,
        "used_second_pass": used_second_pass,
        "final_lt_k": final_lt_k,
        "stage_final_lt_k": stage_final_lt_k,
        "blocked_by_audience": {
            "base": int(locals().get('blocked_base', 0)),
            "refill": int(locals().get('blocked_refill', 0)),
            "prerank": int(locals().get('blocked_prerank', 0)),
            "text_only": {
                "base": int(locals().get('blocked_text_only_base', 0)),
                "refill": int(locals().get('blocked_text_only_refill', 0)),
                "prerank": int(locals().get('blocked_text_only_prerank', 0)),
            }
        },
    }


async def main():
    # Allow passing a file of queries (>= 30) via --queries=path.txt; else use a 32-query default set
    queries_file = None
    for arg in sys.argv[1:]:
        if arg.startswith("--queries="):
            queries_file = arg.split("=", 1)[1].strip()
            break
    sample_queries: List[str] = []
    if queries_file and os.path.exists(queries_file):
        with open(queries_file, "r", encoding="utf-8") as f:
            sample_queries = [ln.strip() for ln in f if ln.strip()]
    else:
        sample_queries = [
            "What is climate change?",
            "How can I reduce my carbon footprint?",
            "Impact of climate change on flooding",
            "Are glaciers really melting?",
            "Heatwave adaptation tips for seniors",
            "Toronto climate action plan key points",
            "Wildfire smoke health effects and precautions",
            "Sea level rise projections for coastal cities",
            "Renewable energy options for homes",
            "Benefits of urban tree canopy for heat mitigation",
            "How does climate change affect mental health?",
            "Best practices for flood resilient buildings",
            "What are the main greenhouse gases?",
            "Explain carbon pricing in Canada",
            "How to prepare an emergency kit for extreme weather",
            "Impacts of climate change on agriculture in Ontario",
            "EV charging at home: safety and cost tips",
            "How to reduce food waste at home",
            "Public transit vs car emissions comparison",
            "What is a heat dome and how to stay safe?",
            "Air quality index during wildfires: guidance",
            "Coastal erosion adaptation strategies",
            "Green roofs benefits and limitations",
            "What is net-zero by 2050?",
            "Wind vs solar tradeoffs for communities",
            "Climate change and vector-borne diseases",
            "Water conservation tips during droughts",
            "How to weatherize windows in winter",
            "Is nuclear energy low carbon?",
            "How to choose energy-efficient appliances",
            "Home insulation types and climate benefits",
            "Permeable pavements and stormwater management",
        ]

    t0 = time.time()
    results: List[Dict[str, Any]] = []
    os.makedirs(os.path.join(os.getcwd(), "logs"), exist_ok=True)
    jsonl_path = os.path.join(os.getcwd(), "logs", "retrieval_experiment.jsonl")
    fallback_used = 0
    total_dropped = 0
    rerank_scores_all: List[float] = []

    for q in sample_queries:
        try:
            r = await run_experiment_for_query(q)
            results.append(r)
            # Persist JSONL per-query
            with open(jsonl_path, "a", encoding="utf-8") as f:
                import json
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

            # One-line summary for dashboarding
            print(f"\nq: {q[:60]} | base={r.get('base_docs', 0)} kept_pre={r.get('kept_after_gate_pre', 0)} refill={r.get('refill_count', 0)} kept_post={r.get('kept_after_gate_post', 0)} final={r.get('final_docs', 0)} drop_rerank={r.get('dropped_by_rerank', 0)} avg_mmr_sim={r.get('avg_mmr_pairwise_sim', 0.0):.3f} filter_fb={int(bool(r.get('filter_fallback_used', False)))} refill_trg={int(bool(r.get('refill_triggered', False)))} max_sim_pre={r.get('max_sim_pre', 0.0):.3f} p50_sim_pre={r.get('p50_sim_pre', 0.0):.3f} p95_sim_pre={r.get('p95_sim_pre', 0.0):.3f} delta={r.get('delta', 0.0):.3f} p20_rerank={r.get('p20_rerank', 0.0):.3f} floor={r.get('floor_used', 0.0):.2f} above_floor={len([s for s in r.get('final_rerank_scores', []) if s >= r.get('floor_used', 0.0)])} model={r.get('reranker_model')} range={r.get('rerank_range')} blocked={r.get('blocked_by_audience')}")
            for idx, title in enumerate(r.get("final_titles", []), 1):
                print(f"    {idx}. {title[:90]}")
            print(f"  rerank_scores: {r.get('final_rerank_scores', [])}")

            if r.get('refill_count', 0) > 0:
                fallback_used += 1
            total_dropped += int(r.get('dropped_by_rerank', 0))
            rerank_scores_all.extend(r.get('final_rerank_scores', []))
        except Exception as e:
            print(f"\nQuery failed: {q}: {e}")

    # Aggregate
    n = len(results)
    avg_final = sum(r.get("final_docs", 0) for r in results) / n if n else 0.0
    pct_ge3 = sum(1 for r in results if r.get("final_docs", 0) >= 3) / n * 100 if n else 0.0
    # Aggregate diagnostics
    pct_fallback_used = (fallback_used / n * 100) if n else 0.0
    kept_tot = sum(r.get('kept_after_gate_post', 0) for r in results)
    pct_rerank_dropped = (total_dropped / max(1, kept_tot)) * 100
    # Rerank score percentiles
    p5 = p50 = p95 = 0.0
    if rerank_scores_all:
        arr = sorted(rerank_scores_all)
        def perc(a, p):
            if not a:
                return 0.0
            idx = max(0, min(len(a)-1, int(round(p * (len(a)-1)))))
            return a[idx]
        p5 = perc(arr, 0.05)
        p50 = perc(arr, 0.50)
        p95 = perc(arr, 0.95)

    print("\n=== Aggregate (experimental flow) ===")
    print(f"Avg final docs: {avg_final:.2f}")
    print(f"Queries with >=3 final docs: {pct_ge3:.0f}%")
    print(f"Fallback used: {pct_fallback_used:.0f}% of queries")
    print(f"Dropped by rerank: {pct_rerank_dropped:.0f}% of kept")
    print(f"Rerank score p5={p5:.3f}, p50={p50:.3f}, p95={p95:.3f}")
    print(f"Elapsed: {time.time() - t0:.2f}s for {n} queries")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)


