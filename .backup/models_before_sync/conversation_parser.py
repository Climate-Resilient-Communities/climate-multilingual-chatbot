"""
Conversation history parser for the query rewriter.
Formats conversation history into a standardized format for proper language detection.
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConversationParser:
    """Parses and formats conversation history for the query rewriter."""
    
    def __init__(self):
        pass
    
    def parse_conversation_history(
        self, 
        conversation_history: Optional[List[Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Parse conversation history into a standardized format.
        
        Args:
            conversation_history: Raw conversation history from the app
            
        Returns:
            List of standardized message dictionaries with 'role' and 'content'
        """
        if not conversation_history:
            return []
        
        standardized_history = []
        
        for i, message in enumerate(conversation_history):
            try:
                parsed_message = self._parse_single_message(message, i)
                if parsed_message:
                    standardized_history.append(parsed_message)
            except Exception as e:
                logger.warning(f"Failed to parse message {i}: {e}")
                continue
        
        logger.info(f"Parsed {len(standardized_history)} messages from conversation history")
        return standardized_history
    
    def _parse_single_message(self, message: Any, index: int) -> Optional[Dict[str, str]]:
        """
        Parse a single message into standardized format.
        
        Args:
            message: Raw message in various possible formats
            index: Message index for debugging
            
        Returns:
            Standardized message dict or None if parsing fails
        """
        # Case 1: Already a dictionary with role and content
        if isinstance(message, dict):
            if 'role' in message and 'content' in message:
                return {
                    'role': str(message['role']).lower(),
                    'content': str(message['content'])
                }
            elif 'content' in message:
                # Guess role based on content or index
                role = 'user' if index % 2 == 0 else 'assistant'
                return {
                    'role': role,
                    'content': str(message['content'])
                }
            else:
                # Try to extract text from any key
                content = self._extract_text_from_dict(message)
                if content:
                    role = 'user' if index % 2 == 0 else 'assistant'
                    return {
                        'role': role,
                        'content': content
                    }
        
        # Case 2: Simple string
        elif isinstance(message, str):
            if message.strip():
                role = 'user' if index % 2 == 0 else 'assistant'
                return {
                    'role': role,
                    'content': message.strip()
                }
        
        # Case 3: List (flatten it)
        elif isinstance(message, list):
            content = ' '.join(str(item) for item in message if item)
            if content.strip():
                role = 'user' if index % 2 == 0 else 'assistant'
                return {
                    'role': role,
                    'content': content.strip()
                }
        
        # Case 4: Other types, convert to string
        else:
            content = str(message).strip()
            if content and content != 'None':
                role = 'user' if index % 2 == 0 else 'assistant'
                return {
                    'role': role,
                    'content': content
                }
        
        return None
    
    def _extract_text_from_dict(self, message_dict: Dict[str, Any]) -> Optional[str]:
        """Extract text content from a dictionary message."""
        # Common keys that might contain the message text
        text_keys = ['text', 'message', 'msg', 'content', 'body', 'data']
        
        for key in text_keys:
            if key in message_dict:
                content = str(message_dict[key]).strip()
                if content and content != 'None':
                    return content
        
        # If no common keys found, try to concatenate all string values
        text_parts = []
        for value in message_dict.values():
            if isinstance(value, str) and value.strip() and value.strip() != 'None':
                text_parts.append(value.strip())
        
        return ' '.join(text_parts) if text_parts else None
    
    def format_for_query_rewriter(
        self, 
        conversation_history: Optional[List[Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Format conversation history specifically for the query rewriter.
        This is the main method that should be used.
        
        Args:
            conversation_history: Raw conversation history
            
        Returns:
            Properly formatted conversation history for query rewriter
        """
        parsed_history = self.parse_conversation_history(conversation_history)
        
        # Log the formatted conversation for debugging
        if parsed_history:
            logger.info("Formatted conversation history for query rewriter:")
            for i, msg in enumerate(parsed_history, 1):
                logger.info(f"  Message {i} ({msg['role']}): {msg['content'][:100]}...")
        else:
            logger.info("No conversation history to format")
        
        return parsed_history


# Global instance for easy import
conversation_parser = ConversationParser()
