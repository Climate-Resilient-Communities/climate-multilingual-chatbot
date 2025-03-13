"""
Health check endpoint for monitoring application status
"""
import os
import redis
import pinecone
from typing import Dict, Any
import logging
from src.data.config.config import REDIS_CONFIG
from src.utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)

async def check_redis() -> Dict[str, Any]:
    """Check Redis connection status"""
    try:
        r = redis.Redis(
            host=REDIS_CONFIG["host"],
            port=REDIS_CONFIG["port"],
            db=REDIS_CONFIG["db"]
        )
        r.ping()
        metrics = MetricsCollector()
        redis_metrics = metrics.get_metrics().get('cache', {})
        return {
            "status": "healthy",
            "latency_ms": 0,
            "metrics": {
                "hit_rate": f"{redis_metrics.get('hit_rate', 0):.2%}",
                "total_requests": redis_metrics.get('total_requests', 0)
            }
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}

async def check_pinecone() -> Dict[str, Any]:
    """Check Pinecone connection status"""
    try:
        pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        # Just list indexes to verify connection
        pc.list_indexes()
        metrics = MetricsCollector()
        retrieval_metrics = metrics.get_metrics().get('retrieval', {})
        return {
            "status": "healthy",
            "latency_ms": 0,
            "metrics": {
                "avg_latency": f"{retrieval_metrics.get('average_latency', 0):.2f}s",
                "success_rate": f"{(1 - retrieval_metrics.get('error_rate', 0)):.2%}"
            }
        }
    except Exception as e:
        logger.error(f"Pinecone health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}

async def check_model() -> Dict[str, Any]:
    """Check model performance metrics"""
    try:
        metrics = MetricsCollector()
        model_metrics = metrics.get_metrics().get('generation', {})
        return {
            "status": "healthy",
            "metrics": {
                "avg_response_time": f"{model_metrics.get('average_latency', 0):.2f}s",
                "p95_latency": f"{model_metrics.get('p95_latency', 0):.2f}s",
                "error_rate": f"{model_metrics.get('error_rate', 0):.2%}",
                "total_requests": model_metrics.get('total_requests', 0)
            }
        }
    except Exception as e:
        logger.error(f"Model metrics check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}

async def health_check() -> Dict[str, Any]:
    """Comprehensive health check of all services"""
    redis_status = await check_redis()
    pinecone_status = await check_pinecone()
    model_status = await check_model()
    
    services_status = {
        "redis": redis_status,
        "pinecone": pinecone_status,
        "model": model_status
    }
    
    overall_status = (
        "healthy" 
        if all(s["status"] == "healthy" for s in services_status.values())
        else "degraded"
    )
    
    metrics = MetricsCollector()
    overall_metrics = metrics.get_metrics()
    
    return {
        "status": overall_status,
        "services": services_status,
        "system_metrics": {
            "total_requests": sum(m.get('total_requests', 0) for m in overall_metrics.values() if isinstance(m, dict)),
            "cache_hit_rate": overall_metrics.get('cache', {}).get('hit_rate', 0),
            "average_response_time": overall_metrics.get('generation', {}).get('average_latency', 0)
        }
    }