"""
Cohere Flow Module for handling generation and translation with Cohere API
"""
import os
import sys
import cohere
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.env_loader import load_environment
from src.models.system_messages import CLIMATE_SYSTEM_MESSAGE

logger = logging.getLogger(__name__)

class CohereModel:
    """Cohere Generation model using Cohere API."""
    
    def __init__(self, model_id="command-a-03-2025"):
        """Initialize CohereModel with client."""
        try:
            # Load environment variables
            load_environment()
            
            # Initialize synchronous cohere client to avoid event loop issues in Streamlit
            self.client = cohere.Client(os.getenv("COHERE_API_KEY"))
            self.model_id = model_id
            logger.info("✓ Cohere client initialized")
        except Exception as e:
            logger.error(f"Cohere client initialization failed: {str(e)}")
            raise

    async def classify(self, prompt: str, system_message: Optional[str] = None, options: Optional[List[str]] = None) -> str:
        """
        Perform classification using Cohere model.
        
        Args:
            prompt (str): The input prompt for classification
            system_message (str, optional): System message to guide the classification
            options (List[str], optional): List of classification options
            
        Returns:
            str: The classification result
        """
        try:
            if not prompt:
                return ""
                
            # Prepare system instruction
            if not system_message:
                system_message = "You are a helpful assistant that classifies text."
                
            # Prepare options instruction
            options_instruction = ""
            if options and len(options) > 0:
                options_str = ", ".join(options)
                options_instruction = f"Choose exactly one option from: {options_str}."
            
            user_message = f"""{prompt}
{options_instruction}
Answer with ONLY the classification result, no explanations or additional text."""

            loop = asyncio.get_event_loop()
            def _call():
                return self.client.chat(
                    model=self.model_id,
                    message=user_message,
                    temperature=0.1,
                )
            response = await loop.run_in_executor(None, _call)
            result = (response.text or "").strip()
            
            # If options were provided, ensure the result is one of the options
            if options and result not in options:
                # Try to extract one of the options from the result
                for option in options:
                    if option.lower() in result.lower():
                        return option
                # If no match found, return the first option as a fallback
                logger.warning(f"Classification result '{result}' not in options {options}, falling back to first option")
                return options[0]
                
            return result
        except Exception as e:
            logger.error(f"Classification error: {str(e)}")
            # Return safe fallback if options provided, otherwise empty string
            return options[0] if options and len(options) > 0 else ""
            
    async def content_generation(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Generate content using Cohere model with a specific purpose.
        
        Args:
            prompt (str): The input prompt for generation
            system_message (str, optional): System message to guide the generation
            
        Returns:
            str: The generated content
        """
        try:
            if not prompt:
                return ""
                
            # Default system message if none provided
            if not system_message:
                system_message = "You are a helpful assistant that provides accurate and concise information."

            loop = asyncio.get_event_loop()
            def _call():
                return self.client.chat(
                    model=self.model_id,
                    message=prompt,
                    temperature=0.1,
                )
            response = await loop.run_in_executor(None, _call)
            return (response.text or "").strip()
        except Exception as e:
            logger.error(f"Content generation error: {str(e)}")
            return ""

    async def query_normalizer(self, query: str, language: str) -> str:
        """Normalize and simplify query using Cohere model."""
        try:
            user_message = f"""Rephrase the following query to its simplest, most basic form:
                                    1. Remove any personal information.
                                    2. Convert the query into simple, direct questions or statements.
                                    3. If the query contains multiple parts, preserve them separately but make them basic.
                                    4. If the query is already simple, leave it unchanged.
                                    Respond with ONLY the rephrased query in {language}.
                                    Query: {query}"""

            loop = asyncio.get_event_loop()
            def _call():
                return self.client.chat(
                    model=self.model_id,
                    message=user_message,
                    temperature=0.1,
                )
            response = await loop.run_in_executor(None, _call)
            return response.text

        except Exception as e:
            logger.error(f"Query normalization error: {str(e)}")
            return query.lower().strip()

    async def translate(self, text: str, source_lang: Optional[str] = None, target_lang: Optional[str] = None) -> str:
        """
        Translate text using Cohere model.
        """
        try:
            if not text or source_lang == target_lang:
                return text

            user_message = f"""You are a professional translator.
Translate the following English text to {target_lang}.
Style: Formal
Tone: Informative

English text to translate: "{text}"
Translation:"""
            
            response = await self.client.chat(
                model=self.model_id,
                message=user_message,
                temperature=0.1,
            )
            return response.text

        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return text

    async def cohere_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Cohere translation method for compatibility with existing codebase.
        This is an alias for the translate method with the expected signature.
        """
        return await self.translate(text, source_lang, target_lang)

    async def cohere_classification(self, prompt: str, system_message: Optional[str] = None, options: Optional[List[str]] = None) -> str:
        """
        Cohere classification method for compatibility with existing codebase.
        This is an alias for the classify method.
        """
        return await self.classify(prompt, system_message, options)

    async def cohere_content_generation(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Cohere content generation method for compatibility with existing codebase.
        This is an alias for the content_generation method.
        """
        return await self.content_generation(prompt, system_message)

    async def generate_response(
        self,
        query: str,
        documents: List[dict],
        description: Optional[str] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """Generate a response using Cohere."""
        try:
            # Format prompt with context and query
            formatted_docs = "\n\n".join([
                f"Document {i+1}:\n{doc.get('content', '')}"
                for i, doc in enumerate(documents)
            ])
            
            # Use system message from system_messages.py
            custom_instructions = description if description else "Provide a clear, accurate response based on the given context."
            
            user_message = f"""Based on the following documents and any relevant conversation history, provide a direct answer to this question: {query}

Documents for context:
{formatted_docs}

Additional Instructions:
1. {custom_instructions}
2. Use proper markdown formatting with headers (e.g., # Main Title, ## Subtitle) for structure
3. Use clear and readable headings that summarize the content, not just repeating the question
4. Write in plain, conversational English
5. Include relatable examples or analogies when appropriate
6. Suggest realistic, low-cost actions people can take when relevant
7. Ensure headers are properly formatted with a space after # symbols (e.g., "# Title" not "#Title")
8. Start with a clear main header (# Title) that summarizes the topic, not just repeating the question
9. DO NOT start your response by repeating the user's question in the header"""
            
            # Format conversation history for Cohere API
            chat_history = []
            if conversation_history:
                for msg in conversation_history:
                    # Handle different conversation history formats
                    if "user" in msg and "assistant" in msg:
                        # Format: {"user": "query", "assistant": "response"}
                        chat_history.append({"role": "USER", "message": str(msg["user"]) if msg["user"] else "No message"})
                        chat_history.append({"role": "CHATBOT", "message": str(msg["assistant"]) if msg["assistant"] else "No response"})
                    elif msg.get("role") == "user":
                        # Format: {"role": "user", "content": "message"}
                        content = msg.get("content") or msg.get("message") or "No message"
                        chat_history.append({"role": "USER", "message": str(content)})
                    elif msg.get("role") == "assistant" or msg.get("role") == "chatbot":
                        # Format: {"role": "assistant", "content": "message"}
                        content = msg.get("content") or msg.get("message") or "No response"
                        chat_history.append({"role": "CHATBOT", "message": str(content)})
                    
                # Ensure all messages have content
                chat_history = [msg for msg in chat_history if msg.get("message") and str(msg["message"]).strip()]

            # Call Cohere
            loop = asyncio.get_event_loop()
            def _call():
                return self.client.chat(
                    model=self.model_id,
                    message=user_message,
                    chat_history=chat_history,
                    preamble=CLIMATE_SYSTEM_MESSAGE,
                    temperature=0.1,
                )
            response = await loop.run_in_executor(None, _call)
            
            # Extract response text
            response_text = response.text or ""
            
            # Process markdown headers to ensure they don't repeat the question
            response_text = self._ensure_proper_markdown(response_text)
            
            return response_text
                    
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}")
            raise
    
    def _ensure_proper_markdown(self, text: str) -> str:
        """Ensure markdown headers are properly formatted for rendering."""
        if not text:
            return text
            
        lines = text.split("\n")
        formatted_lines = []
        
        for line in lines:
            # Check for headers without proper spacing
            if line.strip().startswith('#'):
                # Find the position of the last # in the sequence
                pos = len(line) - len(line.lstrip('#'))
                
                # Get the header level
                header_level = pos
                
                # Check if there's no space after the #s
                if pos < len(line) and line[pos] != ' ':
                    line = line[:pos] + ' ' + line[pos:]
            
            formatted_lines.append(line)
                
        return "\n".join(formatted_lines)

async def main():
    # Load environment variables
    load_environment()
    
    # Initialize the CohereModel class
    model = CohereModel()

    # Test query normalization
    test_query = "what exactly is climate change and how does it affect us?"
    print("\nTesting query normalization:")
    print(f"Original query: {test_query}")
    try:
        normalized = await model.query_normalizer(test_query, "english")
        print(f"Normalized query: {normalized}")
    except Exception as e:
        print(f"Error normalizing query: {e}")

    # Test translation
    test_text = "Climate change is a serious issue that affects our planet."
    print("\nTesting translation:")
    print(f"Original text: {test_text}")
    try:
        translation = await model.cohere_translation(test_text, "english", "spanish")
        print(f"Spanish translation: {translation}")
    except Exception as e:
        print(f"Error in translation: {e}")
    
    # Test classification
    print("\nTesting classification:")
    test_classify = "Previous question: What is climate change? Current question: Tell me more about its effects."
    try:
        result = await model.cohere_classification(
            prompt=test_classify,
            system_message="Determine if this is a follow-up question.",
            options=["YES", "NO"]
        )
        print(f"Classification result: {result}")
    except Exception as e:
        print(f"Error in classification: {e}")
    
    # Test content generation
    print("\nTesting content generation:")
    test_gen = "Extract the main topics from: Climate change affects weather patterns, sea levels, and biodiversity."
    try:
        result = await model.cohere_content_generation(
            prompt=test_gen,
            system_message="Extract key topics concisely."
        )
        print(f"Content generation result: {result}")
    except Exception as e:
        print(f"Error in content generation: {e}")

if __name__ == "__main__":
    asyncio.run(main())
