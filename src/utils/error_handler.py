"""
Enhanced error handling with tracking and recovery mechanisms
"""
import logging
import traceback
import asyncio
from typing import Optional, Dict, Any, List, Type, Callable
from functools import wraps
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class ErrorTracker:
    """Track and analyze error patterns"""
    _instance = None
    _error_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    _error_counts: Dict[str, int] = defaultdict(int)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """Track an error occurrence with context"""
        error_type = error.__class__.__name__
        self._error_counts[error_type] += 1
        
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        
        self._error_history[error_type].append(error_info)
        # Keep only last 100 errors of each type
        if len(self._error_history[error_type]) > 100:
            self._error_history[error_type].pop(0)
            
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'counts': dict(self._error_counts),
            'recent_errors': {
                error_type: errors[-5:] 
                for error_type, errors in self._error_history.items()
            }
        }
    
    def check_error_threshold(self, error_type: str, threshold: int = 10) -> bool:
        """Check if error count exceeds threshold"""
        return self._error_counts[error_type] >= threshold

class ChatbotError(Exception):
    """Base exception class for chatbot errors"""
    def __init__(
        self, 
        message: str, 
        error_code: str, 
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.recoverable = recoverable
        self.timestamp = datetime.now()
        super().__init__(self.message)

class ModelError(ChatbotError):
    """Errors related to model operations"""
    pass

class DatabaseError(ChatbotError):
    """Errors related to database operations"""
    pass

class ValidationError(ChatbotError):
    """Errors related to input validation"""
    pass

class RecoveryStrategy:
    """Define recovery strategies for different error types"""
    
    @staticmethod
    async def model_timeout_recovery(error: ModelError, context: Dict[str, Any]) -> Any:
        """Recovery strategy for model timeout errors"""
        try:
            # Retry with reduced context
            if 'documents' in context:
                reduced_docs = context['documents'][:3]  # Use fewer documents
                retry_result = await context['model'].generate_response(
                    query=context['query'],
                    documents=reduced_docs
                )
                return retry_result
        except Exception as e:
            logger.error(f"Recovery strategy failed: {str(e)}")
            raise

    @staticmethod
    async def connection_error_recovery(error: DatabaseError, context: Dict[str, Any]) -> Any:
        """Recovery strategy for connection errors"""
        try:
            # Implement exponential backoff retry
            for i in range(3):
                try:
                    await asyncio.sleep(2 ** i)
                    if context.get('operation') == 'read':
                        return await context['client'].get(context['key'])
                    elif context.get('operation') == 'write':
                        return await context['client'].set(
                            context['key'], 
                            context['value']
                        )
                except Exception:
                    continue
            raise error
        except Exception as e:
            logger.error(f"Recovery strategy failed: {str(e)}")
            raise

def handle_errors(error_types: Optional[List[Type[Exception]]] = None):
    """Decorator for synchronous error handling"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _handle_error(e, error_types, func.__name__)
        return wrapper
    return decorator

def handle_async_errors(error_types: Optional[List[Type[Exception]]] = None):
    """Decorator for asynchronous error handling"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return await _handle_error_async(e, error_types, func.__name__, 
                                              {'args': args, 'kwargs': kwargs})
        return wrapper
    return decorator

async def _handle_error_async(
    error: Exception,
    error_types: Optional[List[Type[Exception]]],
    function_name: str,
    context: Dict[str, Any]
) -> Any:
    """Handle asynchronous errors with recovery attempts"""
    error_tracker = ErrorTracker()
    
    # Track error
    error_tracker.track_error(error, {
        'function': function_name,
        'context': context
    })
    
    # Check if error type should be handled
    if error_types and not any(isinstance(error, t) for t in error_types):
        raise error

    # Log error with context
    logger.error(
        f"Error in {function_name}: {str(error)}\n"
        f"Context: {context}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    # Apply recovery strategy if available
    if isinstance(error, ChatbotError) and error.recoverable:
        if isinstance(error, ModelError):
            try:
                return await RecoveryStrategy.model_timeout_recovery(error, context)
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {str(recovery_error)}")
                
        elif isinstance(error, DatabaseError):
            try:
                return await RecoveryStrategy.connection_error_recovery(error, context)
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {str(recovery_error)}")
    
    # If recovery failed or error is not recoverable, raise appropriate error
    if isinstance(error, ChatbotError):
        raise error
    else:
        raise ChatbotError(
            message=f"Unexpected error: {str(error)}",
            error_code="INTERNAL_ERROR",
            details={'original_error': str(error)},
            recoverable=False
        )