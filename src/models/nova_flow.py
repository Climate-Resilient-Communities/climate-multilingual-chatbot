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
    
    def __init__(self, model_id="amazon.nova-micro-v1:0"):
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
            self.sync_bedrock = self.sync_session.client(
                service_name='bedrock-runtime',
                region_name='us-east-1',
                config=Config(read_timeout=300, connect_timeout=300)
            )
            self.model_id = model_id
            logger.info("✓ Bedrock client initialized")
        except Exception as e:
            logger.error(f"Bedrock client initialization failed: {str(e)}")
            raise

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

            async with self.session.client(
                service_name='bedrock-runtime',
                region_name='us-east-1',
                config=Config(read_timeout=300, connect_timeout=300)
            ) as bedrock:
                response = await bedrock.invoke_model(
                    body=json.dumps(payload),
                    modelId=self.model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                response_body = await response['body'].read()
                response_json = json.loads(response_body)
                return response_json['output']['message']['content'][0]['text']

        except Exception as e:
            logger.error(f"Query normalization error: {str(e)}")
            return query.lower().strip()

    async def nova_translation(self, text: str, source_lang: str = None, target_lang: str = None) -> str:
        """
        Translate text using Nova model.
        """
        try:
            if not text or source_lang == target_lang:
                return text

            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": f"Provide ONLY a direct translation of {text} from {source_lang} to {target_lang}"}
                        ]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 10000,
                    "temperature": 0.1
                }
            }

            async with self.session.client(
                service_name='bedrock-runtime',
                region_name='us-east-1',
                config=Config(read_timeout=300, connect_timeout=300)
            ) as bedrock:
                response = await bedrock.invoke_model(
                    body=json.dumps(payload),
                    modelId=self.model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                response_body = await response['body'].read()
                response_json = json.loads(response_body)
                return response_json['output']['message']['content'][0]['text']

        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return text

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
                
                # Check if current query is likely a follow-up
                follow_up_indicators = ['else', 'more', 'another', 'they', 'their', 'that', 'this', 'those', 
                                       'these', 'it', 'them', 'why', 'how', 'what about', 'explain']
                
                is_follow_up = any(indicator in query.lower() for indicator in follow_up_indicators)
                
                # For follow-up questions, create an enhanced query that includes previous context
                if is_follow_up and last_context:
                    # Extract topic name from previous context if available
                    topic_match = None
                    location_keywords = ['Rexdale', 'Toronto', 'Vancouver', 'Montreal', 'city', 'neighborhood', 
                                        'community', 'region', 'area']
                    
                    # Look for location names in the previous context
                    for keyword in location_keywords:
                        if keyword.lower() in last_context.lower():
                            topic_match = keyword
                            break
                    
                    # Create an enhanced query with the topic/context
                    if topic_match:
                        enhanced_query = f"{query} about {topic_match}"
                        logger.info(f"Enhanced follow-up query with context: '{enhanced_query}'")
            
            # Use system message from system_messages.py
            custom_instructions = description if description else "Provide a clear, accurate response based on the given context."
            
            prompt = {
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"text": f"""[SYSTEM INSTRUCTION]: {CLIMATE_SYSTEM_MESSAGE}

Based on the following documents and any relevant conversation history, provide a direct answer to this question: {enhanced_query}

Documents for context:
{formatted_docs}
{conversation_context}

Additional Instructions:
1. {custom_instructions}
2. Use proper markdown formatting with headers (e.g., # Main Title, ## Subtitle) for structure
3. Use clear and readable headings that summarize the content, not just repeating the question
4. Write in plain, conversational English
5. Include relatable examples or analogies when appropriate
6. Suggest realistic, low-cost actions people can take when relevant
7. Ensure headers are properly formatted with a space after # symbols (e.g., "# Title" not "#Title")
8. Start with a clear main header (# Title) that summarizes the topic, not just repeating the question
9. DO NOT start your response by repeating the user's question in the header"""}
                        ]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 10000,
                    "temperature": 0.1,
                    "topP": 0.9,
                    "stopSequences": []
                }
            }
            
            # Call Bedrock
            async with self.session.client(
                service_name='bedrock-runtime',
                region_name='us-east-1',
                config=Config(read_timeout=300, connect_timeout=300)
            ) as bedrock:
                response = await bedrock.invoke_model(
                    body=json.dumps(prompt),
                    modelId=self.model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                response_body = await response['body'].read()
                response_json = json.loads(response_body)
                
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
