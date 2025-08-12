"""
Nova Flow Module for handling generation and translation with Bedrock API
"""
import os
import boto3
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from botocore.config import Config
import aioboto3
from src.utils.env_loader import load_environment
from src.models.system_messages import CLIMATE_SYSTEM_MESSAGE

logger = logging.getLogger(__name__)

class BedrockModel:
    """Nova Generation model using Bedrock API."""
    
    def __init__(self, model_id="amazon.nova-lite-v1:0"):
        """Initialize BedrockModel with session and client."""
        try:
            # Load environment variables
            load_environment()
            
            # Initialize boto3 session and client
            self.session = aioboto3.Session(
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name="us-east-1"
            )
            self.sync_session = boto3.Session(
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name="us-east-1"
            )
            # Reusable sync client (prefer sync client and call via threads to avoid event loop coupling)
            self.sync_bedrock = self.sync_session.client(
                service_name='bedrock-runtime',
                region_name='us-east-1',
                config=Config(
                    read_timeout=30,  # Reduced from 300s to prevent production hangs
                    connect_timeout=10,
                    retries={"max_attempts": 2, "mode": "adaptive"},  # Reduced retries
                ),
            )
            self.model_id = model_id
            self._aio_bedrock = None
            logger.info("✓ Bedrock client initialized")
        except Exception as e:
            logger.error(f"Bedrock client initialization failed: {str(e)}")
            raise

    async def _get_aio_client(self):
        """Deprecated in favor of sync client via threads. Kept for compatibility."""
        # We avoid using aio clients to prevent 'Event loop is closed' issues in Streamlit reruns.
        return None

    def _invoke_bedrock_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke Bedrock synchronously and return parsed JSON."""
        import time
        host = "bedrock.us-east-1.amazonaws.com"
        start = time.time()
        try:
            response = self.sync_bedrock.invoke_model(
                body=json.dumps(payload),
                modelId=self.model_id,
                accept="application/json",
                contentType="application/json",
            )
            elapsed_ms = int((time.time() - start) * 1000)
            # Try to log AWS request id if available
            req_id = None
            try:
                req_id = response.get('ResponseMetadata', {}).get('RequestId')
            except Exception:
                pass
            logger.info(
                f"dep=bedrock host={host} op=invoke_model ms={elapsed_ms} status=OK request_id={req_id}".rstrip()
            )
            # boto3 returns 'body' as StreamingBody
            body_bytes = response["body"].read()
            return json.loads(body_bytes)
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            logger.warning(f"dep=bedrock host={host} op=invoke_model ms={elapsed_ms} status=ERR err={str(e)[:120]}")
            # Attempt one client refresh on error
            try:
                self.sync_bedrock = self.sync_session.client(
                    service_name='bedrock-runtime',
                    region_name='us-east-1',
                    config=Config(
                        read_timeout=30,  # Reduced from 300s to prevent production hangs
                        connect_timeout=10,
                        retries={"max_attempts": 2, "mode": "adaptive"},  # Reduced retries
                    ),
                )
            except Exception:
                pass
            raise

    async def _invoke_with_timing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke Bedrock with timeout protection to prevent production hangs."""
        import time
        start = time.time()
        
        try:
            # Hard timeout wrapper to prevent 5+ minute hangs like in production
            timeout_seconds = 30  # Much shorter than 300s default
            result = await asyncio.wait_for(
                asyncio.to_thread(self._invoke_bedrock_sync, payload),
                timeout=timeout_seconds
            )
            return result
            
        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start) * 1000)
            logger.error(f"dep=bedrock op=invoke_model ms={elapsed_ms} status=TIMEOUT after {timeout_seconds}s - preventing production hang")
            raise Exception(f"Bedrock timeout after {timeout_seconds}s - preventing production hang")
            
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            logger.warning(f"dep=bedrock op=invoke_model ms={elapsed_ms} status=ERR err={str(e)[:120]}")
            raise

    async def close(self) -> None:
        """Close the long-lived async client when the app shuts down."""
        try:
            if self._aio_bedrock is not None:
                try:
                    await self._aio_bedrock.__aexit__(None, None, None)
                except RuntimeError as e:
                    # Handle "Event loop is closed" errors gracefully
                    if "event loop is closed" in str(e).lower():
                        logger.debug("Event loop already closed during BedrockModel cleanup")
                    else:
                        raise
                finally:
                    self._aio_bedrock = None
                logger.debug("✓ BedrockModel async client closed successfully")
        except Exception as e:
            logger.debug(f"BedrockModel cleanup warning: {str(e)}")
            # Ensure client is set to None even if cleanup fails
            self._aio_bedrock = None

    async def classify(self, prompt: str, system_message: str = None, options: List[str] = None) -> str:
        """
        Perform classification using Nova model.
        
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
                
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": f"""[SYSTEM INSTRUCTION]: {system_message}
{prompt}
{options_instruction}
Answer with ONLY the classification result, no explanations or additional text."""}
                        ]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 100,
                    "temperature": 0.1,
                    "topP": 0.9
                }
            }
            
            response_json = await self._invoke_with_timing(payload)
            result = response_json['output']['message']['content'][0]['text'].strip()

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
            
    async def content_generation(self, prompt: str, system_message: str = None, max_tokens: int = 800) -> str:
        """
        Generate content using Nova model with a specific purpose.
        
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
                
            payload = {
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"text": f"""[SYSTEM INSTRUCTION]: {system_message}
{prompt}"""}
                        ]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": 0.1,
                    "topP": 0.9
                }
            }
            
            response_json = await self._invoke_with_timing(payload)
            return response_json['output']['message']['content'][0]['text'].strip()
        except Exception as e:
            logger.error(f"Content generation error: {str(e)}")
            return ""

    async def query_normalizer(self, query: str, language: str) -> str:
        """Normalize and simplify query using Nova model."""
        try:
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": f"""Rephrase the following query to its simplest, most basic form:
                                    1. Remove any personal information.
                                    2. Convert the query into simple, direct questions or statements.
                                    3. If the query contains multiple parts, preserve them separately but make them basic.
                                    4. If the query is already simple, leave it unchanged.
                                    Respond with ONLY the rephrased query in {language}.
                                    Query: {query}"""
                            }
                        ]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 10000,
                    "temperature": 0.1
                }
            }

            response_json = await self._invoke_with_timing(payload)
            return response_json['output']['message']['content'][0]['text']

        except Exception as e:
            logger.error(f"Query normalization error: {str(e)}")
            return query.lower().strip()

    async def translate(self, text: str, source_lang: str = None, target_lang: str = None) -> str:
        """
        Translate text using Nova model.
        """
        try:
            if not text or source_lang == target_lang:
                return text

            # Domain-specific terminology guidance
            src = (source_lang or "source language").strip()
            tgt = (target_lang or "target language").strip()
            terminology_rules = (
                "When responding in a non-English language, always use professional, domain-specific climate terminology consistent with authoritative sources in that language (e.g., IPCC translations, national climate reports). "
                "Avoid over-simplified or generic translations of technical terms; preserve scientific accuracy while keeping explanations understandable. "
            )
            zh_rules = (
                "If the target language is Chinese, use standard climate-science terms from the China Meteorological Administration and IPCC: "
                "Example do not use this example for non Chinise: ‘全球气候变化’ when referring to the global phenomenon, ‘气候变化缓解’ for mitigation, and ‘极端气候事件’ for extreme events."
            )
            extra = zh_rules if tgt.lower() in {"zh", "zh-cn", "zh-tw", "chinese"} else ""

            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": (
                                "[SYSTEM INSTRUCTION]: You are a professional climate-science translator.\n"
                                f"{terminology_rules}{extra}\n"
                                f"Translate the following text from {src} to {tgt}. Style: Formal. Tone: Informative.\n"
                                "Provide ONLY the translation, with no preface or notes.\n\n"
                                "Text:\n" + text + "\n\nTranslation:"
                            )}
                        ]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 10000,
                    "temperature": 0.1
                }
            }

            # Use the same unified invocation path
            response_json = await self._invoke_with_timing(payload)
            return response_json['output']['message']['content'][0]['text']

        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return text

    async def nova_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Nova translation method for compatibility with existing codebase.
        This is an alias for the translate method with the expected signature.
        """
        return await self.translate(text, source_lang, target_lang)

    async def nova_classification(self, prompt: str, system_message: str = None, options: List[str] = None) -> str:
        """
        Nova classification method for compatibility with existing codebase.
        This is an alias for the classify method.
        """
        return await self.classify(prompt, system_message, options)

    async def generate_response(
        self,
        query: str,
        documents: List[dict],
        description: str = None,
        conversation_history: List[dict] = None,
    ) -> str:
        """Generate a response using Nova."""
        try:
            # Format prompt with context and query
            formatted_docs = "\n\n".join([
                f"Document {i+1}:\n{doc.get('content', '')}"
                for i, doc in enumerate(documents)
            ])
            
            # Format conversation history for context if provided
            conversation_context = ""
            enhanced_query = query  # Default to original query
            
            if conversation_history and len(conversation_history) > 0:
                # Format the conversation history for the prompt
                history_pairs = []
                last_context = ""
                
                for i in range(0, len(conversation_history), 2):
                    if i + 1 < len(conversation_history):
                        user_msg = conversation_history[i].get('content', '')
                        assistant_msg = conversation_history[i+1].get('content', '')
                        history_pairs.append(f"User: {user_msg}\nAssistant: {assistant_msg}")
                        
                        # Keep track of the last conversation - useful for context
                        last_context = f"{user_msg} {assistant_msg}"
                
                if history_pairs:
                    conversation_context = "Previous conversation:\n" + "\n\n".join(history_pairs)
                
                # Instead of using hardcoded follow-up indicators, we'll perform LLM-based classification
                # This happens in the input_guardrail module now, using the nova_classification method
            
            # Use system message from system_messages.py
            custom_instructions = description if description else "Provide a clear, accurate response based on the given context."
            
            text_content = (
                f"[SYSTEM INSTRUCTION]: {CLIMATE_SYSTEM_MESSAGE}\n\n"
                "Hard rule: If the selected language is English, do not include any non-English words, scripts, or parenthetical translations in the response. Only include another language if it is part of an official proper noun or a direct quote from a source; present it verbatim without added translations.\n\n"
                f"Based on the following documents and any relevant conversation history, provide a direct answer to this question: {enhanced_query}\n\n"
                "Documents for context:\n"
                f"{formatted_docs}\n"
                f"{conversation_context}\n\n"
                "Additional Instructions:\n"
                f"1. {custom_instructions}\n"
                "2. Use proper markdown formatting with headers (e.g., # Main Title, ## Subtitle) for structure\n"
                "3. Use clear and readable headings that summarize the content, not just repeating the question\n"
                "4. Write in plain, conversational English\n"
                "5. Include relatable examples or analogies when appropriate\n"
                "6. Suggest realistic, low-cost actions people can take when relevant\n"
                "7. Ensure headers are properly formatted with a space after # symbols (e.g., \"# Title\" not \"#Title\")\n"
                "8. Start with a clear main header (# Title) that summarizes the topic, not just repeating the question\n"
                "9. DO NOT start your response by repeating the user's question in the header"
            )

            prompt = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": text_content}
                        ]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 1500,
                    "temperature": 0.1,
                    "topP": 0.9,
                    "stopSequences": []
                }
            }
            
            # Call Bedrock
            response_json = await self._invoke_with_timing(prompt)

            # Extract response text
            response_text = response_json['output']['message']['content'][0]['text']

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

if __name__ == "__main__":
    # Load environment variables
    load_environment()
    
    # Initialize the BedrockModel class
    model = BedrockModel()

    # Test query normalization
    test_query = "what exactly is climate change and how does it affect us?"
    print("\nTesting query normalization:")
    print(f"Original query: {test_query}")
    try:
        normalized = asyncio.run(model.query_normalizer(test_query, "english"))
        print(f"Normalized query: {normalized}")
    except Exception as e:
        print(f"Error normalizing query: {e}")

    # Test translation
    test_text = "Climate change is a serious issue that affects our planet."
    print("\nTesting translation:")
    print(f"Original text: {test_text}")
    try:
        translation = asyncio.run(model.nova_translation(test_text, "english", "spanish"))
        print(f"Spanish translation: {translation}")
    except Exception as e:
        print(f"Error in translation: {e}")
    
    # Test classification
    print("\nTesting classification:")
    test_classify = "Previous question: What is climate change? Current question: Tell me more about its effects."
    try:
        result = asyncio.run(model.nova_classification(
            prompt=test_classify,
            system_message="Determine if this is a follow-up question.",
            options=["YES", "NO"]
        ))
        print(f"Classification result: {result}")
    except Exception as e:
        print(f"Error in classification: {e}")
    
    # Test content generation
    print("\nTesting content generation:")
    test_gen = "Extract the main topics from: Climate change affects weather patterns, sea levels, and biodiversity."
    try:
        result = asyncio.run(model.nova_content_generation(
            prompt=test_gen,
            system_message="Extract key topics concisely."
        ))
        print(f"Content generation result: {result}")
    except Exception as e:
        print(f"Error in content generation: {e}")
