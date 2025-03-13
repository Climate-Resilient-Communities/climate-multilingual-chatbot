"""
System resource monitoring and alerting
"""
import psutil
import logging
import asyncio
import time
from typing import Dict, Any
from datetime import datetime
from src.utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self, threshold_cpu=80.0, threshold_memory=85.0, threshold_disk=90.0):
        self.threshold_cpu = threshold_cpu
        self.threshold_memory = threshold_memory
        self.threshold_disk = threshold_disk
        self.metrics = MetricsCollector()
        
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Process information
            process = psutil.Process()
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "alert": cpu_percent > self.threshold_cpu
                },
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent": memory_percent,
                    "alert": memory_percent > self.threshold_memory
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "percent": disk_percent,
                    "alert": disk_percent > self.threshold_disk
                },
                "process": {
                    "memory_mb": process_memory,
                    "cpu_percent": process.cpu_percent(),
                    "threads": len(process.threads())
                }
            }
            
            # Add application metrics
            app_metrics = self.metrics.get_metrics()
            metrics["application"] = {
                "total_requests": sum(m.get('total_requests', 0) for m in app_metrics.values() if isinstance(m, dict)),
                "error_rates": {
                    op: data.get('error_rate', 0) 
                    for op, data in app_metrics.items() 
                    if isinstance(data, dict)
                },
                "cache_hit_rate": app_metrics.get('cache', {}).get('hit_rate', 0)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return {}

    def check_alerts(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """Check for any metric alerts"""
        alerts = {}
        
        if metrics.get("cpu", {}).get("alert"):
            alerts["cpu"] = f"High CPU usage: {metrics['cpu']['percent']}%"
            
        if metrics.get("memory", {}).get("alert"):
            alerts["memory"] = f"High memory usage: {metrics['memory']['percent']}%"
            
        if metrics.get("disk", {}).get("alert"):
            alerts["disk"] = f"High disk usage: {metrics['disk']['percent']}%"
            
        # Check application-specific metrics
        app_metrics = metrics.get("application", {})
        if app_metrics:
            error_rates = app_metrics.get("error_rates", {})
            for op, rate in error_rates.items():
                if rate > 0.05:  # Alert if error rate > 5%
                    alerts[f"{op}_errors"] = f"High error rate for {op}: {rate:.2%}"
                    
        return alerts

    async def monitor_loop(self, interval: int = 60):
        """Continuous monitoring loop"""
        while True:
            try:
                metrics = await self.get_system_metrics()
                alerts = self.check_alerts(metrics)
                
                if alerts:
                    logger.warning("System alerts detected:")
                    for alert_type, message in alerts.items():
                        logger.warning(f"- {alert_type}: {message}")
                        
                # Log metrics at debug level
                logger.debug(f"System metrics: {metrics}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(interval)  # Continue monitoring despite errors

async def start_monitoring(interval: int = 60):
    """Start system monitoring"""
    monitor = SystemMonitor()
    await monitor.monitor_loop(interval)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_monitoring())