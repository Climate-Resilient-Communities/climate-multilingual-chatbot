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
                    "maxTokens": 1000,
                    "temperature": 0.7
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
                    "maxTokens": 1000,
                    "temperature": 0.7
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
    ) -> str:
        """Generate a response using Nova."""
        try:
            from src.models.gen_response_nova import system_message
            
            # Format documents for context
            formatted_docs = "\n\n".join([
                f"Document {i+1}:\n{doc.get('content', '')}"
                for i, doc in enumerate(documents)
            ])
            
            # Create messages in the format Nova expects
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"text": system_message}
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"text": f"Context Documents:\n{formatted_docs}"}
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"text": f"Based on the provided documents, answer this question: {query}" + 
                                (f" {description}" if description else "")}
                    ]
                }
            ]
            
            # Create prompt payload
            prompt = {
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": 2000,
                    "temperature": 0.7,
                    "topP": 0.8,
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
                return response_json['output']['message']['content'][0]['text']
                    
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}")
            raise

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
