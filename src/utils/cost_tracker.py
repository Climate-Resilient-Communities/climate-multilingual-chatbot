"""
Cost tracking module for monitoring AI model usage and calculating expenses.
Tracks Cohere Command-A, AWS Bedrock Nova, and Pinecone operations.
Includes persistent storage via Google Sheets for long-term analytics.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Enumeration of supported AI models for cost tracking."""
    COHERE_COMMAND_A = "cohere_command_a"
    AWS_NOVA_LITE = "aws_nova_lite"
    PINECONE_OPERATIONS = "pinecone_operations"

@dataclass
class ModelPricing:
    """Pricing structure for different AI models."""
    # Cohere Command-A pricing (approximate)
    cohere_input_per_1m_tokens: float = 5.00  # $5 per 1M input tokens
    cohere_output_per_1m_tokens: float = 15.00  # $15 per 1M output tokens
    
    # AWS Bedrock Nova Lite pricing (approximate)
    nova_input_per_1m_tokens: float = 0.60  # $0.60 per 1M input tokens
    nova_output_per_1m_tokens: float = 2.40  # $2.40 per 1M output tokens
    
    # Pinecone pricing (approximate)
    pinecone_per_1m_vectors: float = 0.20  # $0.20 per 1M vector operations

@dataclass
class UsageMetrics:
    """Usage metrics for a single model interaction."""
    model_type: str
    timestamp: float
    input_tokens: int = 0
    output_tokens: int = 0
    vector_operations: int = 0
    processing_time_ms: float = 0.0
    query_id: Optional[str] = None
    language_code: Optional[str] = None
    cache_hit: bool = False
    session_id: Optional[str] = None
    query_type: Optional[str] = None  # "on-topic", "off-topic", "harmful", etc.

@dataclass 
class CostSummary:
    """Summary of costs for a time period."""
    total_cost: float
    cohere_cost: float
    nova_cost: float
    pinecone_cost: float
    total_interactions: int
    cohere_interactions: int
    nova_interactions: int
    pinecone_operations: int
    time_period: str
    interaction_breakdown: Dict[str, int] = None  # on-topic, off-topic, etc.
    language_breakdown: Dict[str, int] = None

class CostTracker:
    """Main cost tracking class for monitoring AI model usage."""
    
    def __init__(self, redis_client=None):
        """Initialize cost tracker with optional Redis backend and Google Sheets."""
        self.redis_client = redis_client
        self.pricing = ModelPricing()
        self.local_usage_cache = []  # Fallback if Redis not available
        
        # Initialize Google Sheets
        self.sheets_client = self._init_google_sheets()
        self.analytics_sheet = None
        self._init_analytics_sheet()
        
    def _init_google_sheets(self):
        """Initialize Google Sheets client"""
        try:
            credentials_path = "credentials.json"
            if not os.path.exists(credentials_path):
                logger.error("Google Sheets credentials not found")
                return None
            
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            return None
    
    def _init_analytics_sheet(self):
        """Initialize or create analytics worksheet"""
        if not self.sheets_client:
            return
        
        try:
            sheets_id = os.getenv("GOOGLE_SHEETS_ID")
            if not sheets_id:
                logger.error("GOOGLE_SHEETS_ID not found in environment")
                return
            
            spreadsheet = self.sheets_client.open_by_key(sheets_id)
            
            # Try to open existing analytics sheet
            try:
                self.analytics_sheet = spreadsheet.worksheet("Analytics")
                logger.info("Found existing Analytics worksheet")
            except gspread.WorksheetNotFound:
                # Create new analytics sheet
                self.analytics_sheet = spreadsheet.add_worksheet(
                    title="Analytics", 
                    rows="5000", 
                    cols="15"
                )
                self._setup_analytics_headers()
                logger.info("Created new Analytics worksheet")
                
        except Exception as e:
            logger.error(f"Failed to initialize analytics sheet: {e}")
    
    def _setup_analytics_headers(self):
        """Set up headers for analytics sheet"""
        if not self.analytics_sheet:
            return
        
        headers = [
            "Timestamp", "Date", "Time", "Session_ID", "Model_Used", 
            "Input_Tokens", "Output_Tokens", "Vector_Ops", "Cost_USD", 
            "Language", "Query_Type", "Processing_MS", "Cache_Hit", "Query_ID"
        ]
        
        try:
            self.analytics_sheet.append_row(headers)
            logger.info("Set up analytics sheet headers")
        except Exception as e:
            logger.error(f"Failed to set up headers: {e}")
        
    async def track_model_usage(
        self,
        model_type: ModelType,
        input_tokens: int = 0,
        output_tokens: int = 0,
        vector_operations: int = 0,
        processing_time_ms: float = 0.0,
        query_id: Optional[str] = None,
        language_code: Optional[str] = None,
        cache_hit: bool = False,
        session_id: Optional[str] = None,
        query_type: Optional[str] = None
    ) -> None:
        """Track usage for a specific model interaction."""
        try:
            usage = UsageMetrics(
                model_type=model_type.value,
                timestamp=time.time(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                vector_operations=vector_operations,
                processing_time_ms=processing_time_ms,
                query_id=query_id,
                language_code=language_code,
                cache_hit=cache_hit,
                session_id=session_id,
                query_type=query_type
            )
            
            # Store in Google Sheets for persistence
            if self.analytics_sheet:
                await self._store_usage_in_sheets(usage)
            
            # Store in Redis if available
            if self.redis_client:
                await self._store_usage_in_redis(usage)
            else:
                # Fallback to local cache
                self.local_usage_cache.append(usage)
                
            logger.debug(f"💰 Tracked {model_type.value} usage: {input_tokens}+{output_tokens} tokens, {vector_operations} vectors")
            
        except Exception as e:
            logger.error(f"Failed to track model usage: {str(e)}")
    
    async def _store_usage_in_sheets(self, usage: UsageMetrics) -> None:
        """Store usage metrics in Google Sheets for persistence"""
        try:
            dt = datetime.fromtimestamp(usage.timestamp)
            cost = self.calculate_cost(usage)
            
            row_data = [
                dt.isoformat(),  # Timestamp
                dt.strftime("%Y-%m-%d"),  # Date
                dt.strftime("%H:%M:%S"),  # Time
                usage.session_id or "",  # Session_ID
                usage.model_type,  # Model_Used
                usage.input_tokens,  # Input_Tokens
                usage.output_tokens,  # Output_Tokens
                usage.vector_operations,  # Vector_Ops
                round(cost, 6),  # Cost_USD
                usage.language_code or "",  # Language
                usage.query_type or "",  # Query_Type
                round(usage.processing_time_ms, 2),  # Processing_MS
                "Yes" if usage.cache_hit else "No",  # Cache_Hit
                usage.query_id or ""  # Query_ID
            ]
            
            self.analytics_sheet.append_row(row_data)
            logger.debug(f"Stored usage in Analytics sheet: {usage.model_type}")
            
        except Exception as e:
            logger.error(f"Failed to store usage in sheets: {e}")
    
    async def _store_usage_in_redis(self, usage: UsageMetrics) -> None:
        """Store usage metrics in Redis with daily aggregation."""
        try:
            date_key = datetime.fromtimestamp(usage.timestamp).strftime('%Y-%m-%d')
            
            # Store detailed usage record
            usage_key = f"usage:detail:{date_key}:{usage.model_type}:{int(usage.timestamp)}"
            await self.redis_client.set(usage_key, json.dumps(asdict(usage)), ex=86400 * 7)  # Keep for 7 days
            
            # Update daily aggregates
            daily_key = f"usage:daily:{date_key}"
            
            # Get existing daily data
            existing_data = await self.redis_client.get(daily_key)
            if existing_data:
                daily_data = json.loads(existing_data)
            else:
                daily_data = {
                    "date": date_key,
                    "total_interactions": 0,
                    "models": {
                        "cohere_command_a": {"interactions": 0, "input_tokens": 0, "output_tokens": 0},
                        "aws_nova_lite": {"interactions": 0, "input_tokens": 0, "output_tokens": 0},
                        "pinecone_operations": {"operations": 0, "vector_operations": 0}
                    }
                }
            
            # Update aggregates
            daily_data["total_interactions"] += 1
            
            if usage.model_type in daily_data["models"]:
                model_data = daily_data["models"][usage.model_type]
                model_data["interactions"] = model_data.get("interactions", 0) + 1
                
                if usage.model_type in ["cohere_command_a", "aws_nova_lite"]:
                    model_data["input_tokens"] = model_data.get("input_tokens", 0) + usage.input_tokens
                    model_data["output_tokens"] = model_data.get("output_tokens", 0) + usage.output_tokens
                elif usage.model_type == "pinecone_operations":
                    model_data["operations"] = model_data.get("operations", 0) + 1
                    model_data["vector_operations"] = model_data.get("vector_operations", 0) + usage.vector_operations
            
            # Store updated daily data
            await self.redis_client.set(daily_key, json.dumps(daily_data), ex=86400 * 30)  # Keep for 30 days
            
        except Exception as e:
            logger.error(f"Failed to store usage in Redis: {str(e)}")
    
    def calculate_cost(self, usage: UsageMetrics) -> float:
        """Calculate cost for a single usage metric."""
        try:
            if usage.model_type == ModelType.COHERE_COMMAND_A.value:
                input_cost = (usage.input_tokens / 1_000_000) * self.pricing.cohere_input_per_1m_tokens
                output_cost = (usage.output_tokens / 1_000_000) * self.pricing.cohere_output_per_1m_tokens
                return input_cost + output_cost
                
            elif usage.model_type == ModelType.AWS_NOVA_LITE.value:
                input_cost = (usage.input_tokens / 1_000_000) * self.pricing.nova_input_per_1m_tokens
                output_cost = (usage.output_tokens / 1_000_000) * self.pricing.nova_output_per_1m_tokens
                return input_cost + output_cost
                
            elif usage.model_type == ModelType.PINECONE_OPERATIONS.value:
                return (usage.vector_operations / 1_000_000) * self.pricing.pinecone_per_1m_vectors
                
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate cost: {str(e)}")
            return 0.0
    
    async def get_daily_costs(self, date: Optional[str] = None) -> CostSummary:
        """Get cost summary for a specific day."""
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            if self.redis_client:
                return await self._get_daily_costs_from_redis(date)
            else:
                return self._get_daily_costs_from_cache(date)
                
        except Exception as e:
            logger.error(f"Failed to get daily costs: {str(e)}")
            return CostSummary(0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, date)
    
    async def _get_daily_costs_from_redis(self, date: str) -> CostSummary:
        """Calculate costs from Redis daily aggregates."""
        try:
            daily_key = f"usage:daily:{date}"
            daily_data = await self.redis_client.get(daily_key)
            
            if not daily_data:
                return CostSummary(0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, date)
            
            data = json.loads(daily_data)
            
            # Calculate costs for each model
            cohere_data = data["models"].get("cohere_command_a", {})
            nova_data = data["models"].get("aws_nova_lite", {})
            pinecone_data = data["models"].get("pinecone_operations", {})
            
            # Cohere costs
            cohere_input_cost = (cohere_data.get("input_tokens", 0) / 1_000_000) * self.pricing.cohere_input_per_1m_tokens
            cohere_output_cost = (cohere_data.get("output_tokens", 0) / 1_000_000) * self.pricing.cohere_output_per_1m_tokens
            cohere_cost = cohere_input_cost + cohere_output_cost
            
            # Nova costs
            nova_input_cost = (nova_data.get("input_tokens", 0) / 1_000_000) * self.pricing.nova_input_per_1m_tokens
            nova_output_cost = (nova_data.get("output_tokens", 0) / 1_000_000) * self.pricing.nova_output_per_1m_tokens
            nova_cost = nova_input_cost + nova_output_cost
            
            # Pinecone costs
            pinecone_cost = (pinecone_data.get("vector_operations", 0) / 1_000_000) * self.pricing.pinecone_per_1m_vectors
            
            return CostSummary(
                total_cost=cohere_cost + nova_cost + pinecone_cost,
                cohere_cost=cohere_cost,
                nova_cost=nova_cost,
                pinecone_cost=pinecone_cost,
                total_interactions=data.get("total_interactions", 0),
                cohere_interactions=cohere_data.get("interactions", 0),
                nova_interactions=nova_data.get("interactions", 0),
                pinecone_operations=pinecone_data.get("operations", 0),
                time_period=date
            )
            
        except Exception as e:
            logger.error(f"Failed to get costs from Redis: {str(e)}")
            return CostSummary(0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, date)
    
    def _get_daily_costs_from_cache(self, date: str) -> CostSummary:
        """Calculate costs from local cache (fallback)."""
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            total_cost = 0.0
            cohere_cost = 0.0
            nova_cost = 0.0
            pinecone_cost = 0.0
            total_interactions = 0
            cohere_interactions = 0
            nova_interactions = 0
            pinecone_operations = 0
            
            for usage in self.local_usage_cache:
                usage_date = datetime.fromtimestamp(usage.timestamp).date()
                if usage_date == target_date:
                    cost = self.calculate_cost(usage)
                    total_cost += cost
                    total_interactions += 1
                    
                    if usage.model_type == ModelType.COHERE_COMMAND_A.value:
                        cohere_cost += cost
                        cohere_interactions += 1
                    elif usage.model_type == ModelType.AWS_NOVA_LITE.value:
                        nova_cost += cost
                        nova_interactions += 1
                    elif usage.model_type == ModelType.PINECONE_OPERATIONS.value:
                        pinecone_cost += cost
                        pinecone_operations += 1
            
            return CostSummary(
                total_cost=total_cost,
                cohere_cost=cohere_cost,
                nova_cost=nova_cost,
                pinecone_cost=pinecone_cost,
                total_interactions=total_interactions,
                cohere_interactions=cohere_interactions,
                nova_interactions=nova_interactions,
                pinecone_operations=pinecone_operations,
                time_period=date
            )
            
        except Exception as e:
            logger.error(f"Failed to get costs from cache: {str(e)}")
            return CostSummary(0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, date)
    
    async def get_cost_trends(self, days: int = 7) -> List[CostSummary]:
        """Get cost trends over the last N days."""
        try:
            trends = []
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                daily_costs = await self.get_daily_costs(date)
                trends.append(daily_costs)
            
            return list(reversed(trends))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Failed to get cost trends: {str(e)}")
            return []
    
    def estimate_token_count(self, text: str) -> int:
        """Rough estimation of token count for cost calculation."""
        try:
            # Simple approximation: ~4 characters per token
            return max(1, len(text) // 4)
        except Exception:
            return 1
    
    def get_analytics_from_sheets(self) -> Dict[str, Any]:
        """Get comprehensive analytics from Google Sheets"""
        if not self.analytics_sheet:
            return {}
        
        try:
            records = self.analytics_sheet.get_all_records()
            if not records:
                return {}
            
            total_cost = sum(float(r.get("Cost_USD", 0)) for r in records)
            total_interactions = len(records)
            
            # Model breakdown
            model_breakdown = {}
            for record in records:
                model = record.get("Model_Used", "unknown")
                if model not in model_breakdown:
                    model_breakdown[model] = {
                        "interactions": 0,
                        "cost": 0.0,
                        "input_tokens": 0,
                        "output_tokens": 0
                    }
                
                model_breakdown[model]["interactions"] += 1
                model_breakdown[model]["cost"] += float(record.get("Cost_USD", 0))
                model_breakdown[model]["input_tokens"] += int(record.get("Input_Tokens", 0))
                model_breakdown[model]["output_tokens"] += int(record.get("Output_Tokens", 0))
            
            # Language breakdown
            language_breakdown = {}
            for record in records:
                lang = record.get("Language", "unknown")
                if lang:
                    language_breakdown[lang] = language_breakdown.get(lang, 0) + 1
            
            # Query type breakdown (interaction breakdown)
            interaction_breakdown = {}
            for record in records:
                qtype = record.get("Query_Type", "unknown")
                if qtype:
                    interaction_breakdown[qtype] = interaction_breakdown.get(qtype, 0) + 1
            
            # Recent interactions for logs
            recent_interactions = []
            for record in reversed(records[-50:]):  # Last 50 interactions
                recent_interactions.append({
                    "timestamp": record.get("Timestamp", ""),
                    "session_id": record.get("Session_ID", ""),
                    "model": record.get("Model_Used", ""),
                    "language": record.get("Language", ""),
                    "query_type": record.get("Query_Type", ""),
                    "cost": float(record.get("Cost_USD", 0)),
                    "processing_time": float(record.get("Processing_MS", 0)),
                    "cache_hit": record.get("Cache_Hit", "") == "Yes"
                })
            
            # Daily costs for trends
            daily_costs = {}
            for record in records:
                date = record.get("Date", "")
                if date:
                    if date not in daily_costs:
                        daily_costs[date] = 0.0
                    daily_costs[date] += float(record.get("Cost_USD", 0))
            
            return {
                "total_cost": round(total_cost, 4),
                "total_interactions": total_interactions,
                "model_breakdown": model_breakdown,
                "language_breakdown": language_breakdown,
                "interaction_breakdown": interaction_breakdown,
                "recent_interactions": recent_interactions,
                "daily_costs": daily_costs,
                "cost_summary": {
                    "cohere_cost": sum(
                        float(r.get("Cost_USD", 0)) 
                        for r in records 
                        if r.get("Model_Used") == "cohere_command_a"
                    ),
                    "nova_cost": sum(
                        float(r.get("Cost_USD", 0)) 
                        for r in records 
                        if r.get("Model_Used") == "aws_nova_lite"
                    ),
                    "pinecone_cost": sum(
                        float(r.get("Cost_USD", 0)) 
                        for r in records 
                        if r.get("Model_Used") == "pinecone_operations"
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get analytics from sheets: {e}")
            return {}

# Global cost tracker instance
_global_cost_tracker = None

def get_cost_tracker(redis_client=None) -> CostTracker:
    """Get or create the global cost tracker instance."""
    global _global_cost_tracker
    if _global_cost_tracker is None:
        _global_cost_tracker = CostTracker(redis_client)
    elif redis_client and not _global_cost_tracker.redis_client:
        # Update with Redis client if it becomes available
        _global_cost_tracker.redis_client = redis_client
    return _global_cost_tracker