"""
Analytics module for tracking and analyzing application usage
"""
import logging
import time
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from src.utils.metrics import MetricsCollector
from src.utils.error_handler import handle_async_errors

logger = logging.getLogger(__name__)

class AnalyticsTracker:
    def __init__(self):
        self.metrics = MetricsCollector()
        self.usage_patterns = defaultdict(lambda: {
            'total_queries': 0,
            'unique_users': set(),
            'language_distribution': defaultdict(int),
            'query_times': [],
            'error_counts': defaultdict(int),
            'cache_usage': {'hits': 0, 'misses': 0}
        })
        
    def track_query(self, query_data: Dict[str, Any]):
        """Track a single query interaction"""
        timestamp = datetime.now()
        day_key = timestamp.strftime('%Y-%m-%d')
        
        # Update daily stats
        stats = self.usage_patterns[day_key]
        stats['total_queries'] += 1
        stats['unique_users'].add(query_data.get('user_id', 'anonymous'))
        stats['language_distribution'][query_data.get('language', 'en')] += 1
        stats['query_times'].append(query_data.get('processing_time', 0))
        
        # Track errors if any
        if 'error' in query_data:
            error_type = query_data['error'].get('code', 'unknown')
            stats['error_counts'][error_type] += 1
            
        # Track cache usage
        if query_data.get('cache_hit') is not None:
            if query_data['cache_hit']:
                stats['cache_usage']['hits'] += 1
            else:
                stats['cache_usage']['misses'] += 1
    
    def get_daily_analytics(self, date: str = None) -> Dict[str, Any]:
        """Get analytics for a specific day"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
            
        stats = self.usage_patterns[date]
        
        if not stats['total_queries']:
            return {}
            
        return {
            'total_queries': stats['total_queries'],
            'unique_users': len(stats['unique_users']),
            'queries_per_user': stats['total_queries'] / len(stats['unique_users']) if stats['unique_users'] else 0,
            'language_distribution': dict(stats['language_distribution']),
            'average_processing_time': sum(stats['query_times']) / len(stats['query_times']) if stats['query_times'] else 0,
            'error_rate': sum(stats['error_counts'].values()) / stats['total_queries'] if stats['total_queries'] else 0,
            'cache_hit_rate': (stats['cache_usage']['hits'] / 
                             (stats['cache_usage']['hits'] + stats['cache_usage']['misses']))
                             if (stats['cache_usage']['hits'] + stats['cache_usage']['misses']) > 0 else 0
        }
    
    def get_trending_topics(self, days: int = 7) -> List[Dict[str, Any]]:
        """Analyze trending topics over the specified number of days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        topic_counts = defaultdict(int)
        total_queries = 0
        
        for date, stats in self.usage_patterns.items():
            if datetime.strptime(date, '%Y-%m-%d') >= start_date:
                for query in stats.get('queries', []):
                    # Extract topics using simple keyword matching
                    # This could be enhanced with more sophisticated NLP
                    words = query.lower().split()
                    for word in words:
                        if len(word) > 3:  # Skip short words
                            topic_counts[word] += 1
                            total_queries += 1
        
        # Calculate trending topics
        if total_queries > 0:
            trending = [
                {
                    'topic': topic,
                    'count': count,
                    'percentage': (count / total_queries) * 100
                }
                for topic, count in sorted(
                    topic_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]  # Top 10 topics
            ]
            return trending
        return []
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Generate performance insights from collected metrics"""
        metrics = self.metrics.get_metrics()
        
        return {
            'response_times': {
                op: {
                    'avg_latency': data.get('average_latency', 0),
                    'p95_latency': data.get('p95_latency', 0),
                    'error_rate': data.get('error_rate', 0)
                }
                for op, data in metrics.items()
                if isinstance(data, dict)
            },
            'cache_efficiency': {
                'hit_rate': metrics.get('cache', {}).get('hit_rate', 0),
                'miss_rate': metrics.get('cache', {}).get('miss_rate', 0)
            },
            'overall_health': {
                'total_requests': sum(
                    data.get('total_requests', 0) 
                    for data in metrics.values() 
                    if isinstance(data, dict)
                ),
                'error_rate': sum(
                    data.get('error_rate', 0) 
                    for data in metrics.values() 
                    if isinstance(data, dict)
                ) / len(metrics) if metrics else 0
            }
        }
    
    async def generate_daily_report(self) -> Dict[str, Any]:
        """Generate comprehensive daily analytics report"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            daily_stats = self.get_daily_analytics(today)
            performance = self.get_performance_insights()
            trending = self.get_trending_topics(days=1)
            
            return {
                'date': today,
                'usage_statistics': daily_stats,
                'performance_metrics': performance,
                'trending_topics': trending,
                'recommendations': self._generate_recommendations(daily_stats, performance)
            }
        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}")
            return {}
    
    def _generate_recommendations(
        self, 
        stats: Dict[str, Any], 
        performance: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on analytics"""
        recommendations = []
        
        # Check cache efficiency
        cache_hit_rate = stats.get('cache_hit_rate', 0)
        if cache_hit_rate < 0.5:
            recommendations.append(
                "Consider adjusting cache strategy to improve hit rate"
            )
        
        # Check error rates
        error_rate = stats.get('error_rate', 0)
        if error_rate > 0.05:
            recommendations.append(
                f"High error rate ({error_rate:.2%}) detected. Review error patterns"
            )
        
        # Check processing times
        avg_time = stats.get('average_processing_time', 0)
        if avg_time > 2.0:
            recommendations.append(
                f"High average processing time ({avg_time:.2f}s). Consider optimization"
            )
        
        return recommendations