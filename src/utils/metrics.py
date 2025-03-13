"""
Metrics collection and monitoring for the application
"""
import time
from typing import Dict, Any
import logging
from functools import wraps
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

class MetricsCollector:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        # Skip initialization if already initialized
        if hasattr(self, '_initialized'):
            return
            
        self.metrics = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'errors': 0,
            'last_error': None,
            'last_error_time': None
        })
        
        self.response_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0
        self._initialized = True
    
    def record_latency(self, operation: str, duration: float):
        """Record operation latency"""
        self.metrics[operation]['count'] += 1
        self.metrics[operation]['total_time'] += duration
        self.response_times[operation].append(duration)
        
        # Keep only last 1000 response times
        if len(self.response_times[operation]) > 1000:
            self.response_times[operation].pop(0)
    
    def record_error(self, operation: str, error: Exception):
        """Record operation error"""
        self.metrics[operation]['errors'] += 1
        self.metrics[operation]['last_error'] = str(error)
        self.metrics[operation]['last_error_time'] = datetime.now()
        self.error_counts[operation] += 1
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.cache_misses += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        metrics = {}
        for op, data in self.metrics.items():
            avg_time = data['total_time'] / data['count'] if data['count'] > 0 else 0
            metrics[op] = {
                'total_requests': data['count'],
                'average_latency': avg_time,
                'error_rate': (data['errors'] / data['count'] if data['count'] > 0 else 0),
                'last_error': data['last_error'],
                'last_error_time': data['last_error_time']
            }
            
            # Calculate percentiles if we have response times
            if op in self.response_times and self.response_times[op]:
                sorted_times = sorted(self.response_times[op])
                metrics[op].update({
                    'p50_latency': sorted_times[len(sorted_times) // 2],
                    'p95_latency': sorted_times[int(len(sorted_times) * 0.95)],
                    'p99_latency': sorted_times[int(len(sorted_times) * 0.99)]
                })
        
        # Add cache statistics
        total_cache_requests = self.cache_hits + self.cache_misses
        metrics['cache'] = {
            'hit_rate': self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0,
            'miss_rate': self.cache_misses / total_cache_requests if total_cache_requests > 0 else 0,
            'total_requests': total_cache_requests
        }
        
        return metrics

def track_metrics(operation: str):
    """Decorator to track operation metrics"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = MetricsCollector()
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                metrics.record_latency(operation, time.time() - start_time)
                return result
            except Exception as e:
                metrics.record_error(operation, e)
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = MetricsCollector()
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                metrics.record_latency(operation, time.time() - start_time)
                return result
            except Exception as e:
                metrics.record_error(operation, e)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator