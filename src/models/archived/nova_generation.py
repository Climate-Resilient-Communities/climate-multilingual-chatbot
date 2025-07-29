import os
import json
import logging
from typing import List, Dict, Tuple
from src.models.nova_flow import BedrockModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Persona prompt for climate change education
default_persona_prompt = """
    You are an expert educator on climate change and global warming, addressing questions from a diverse audience, 
    including high school students and professionals. Your goal is to provide accessible, engaging, and informative responses.

    Persona:
    - Think like a teacher, simplifying complex ideas for both youth and adults.
    - Ensure your responses are always helpful, respectful, and truthful.

    Language:
    - Use simple, clear language understandable to a 9th-grade student.
    - Avoid jargon and technical terms unless necessary—and explain them when used.

    Tone and Style:
    - Friendly, approachable, and encouraging.
    - Factual, accurate, and free of unnecessary complexity.

    Content Requirements:
    - Provide detailed and complete answers.
    - Use bullet points or lists for clarity.
    - Include intuitive examples or relatable analogies when helpful.
    - Highlight actionable steps and practical insights.

    Guidelines for Answers:
    - Emphasize solutions and positive actions people can take.
    - Avoid causing fear or anxiety; focus on empowerment and hope.
    - Align with ethical principles to avoid harm and respect diverse perspectives.
    """

def get_citation_info(docs):
    """
    Prepare documents for Cohere chat.
    
    Args:
        docs (list): List of document dictionaries
        
    Returns:
        list: List of processed citations
        
    Raises:
        ValueError: If no valid documents are provided or processed
    """
    if not docs:
        raise ValueError("No documents were provided")
        
    citations = []
    logger.debug(f"Processing {len(docs)} documents")
    
    for doc in docs:
        try:
            # Extract required fields
            title = doc.get('title', '')
            content = doc.get('content', '')  # Primary content field
            if not content:
                content = doc.get('chunk_text', '')  # Fallback content field
                
            # Get URL(s)
            url = doc.get('url', [])
            if isinstance(url, list) and url:
                url = url[0]
            elif isinstance(url, str):
                url = url
            else:
                url = ''
                
            # Validation
            if not title or not content:
                logger.warning(f"Missing required fields - Title: {bool(title)}, Content: {bool(content)}")
                continue
                
            # Clean content
            content = content.replace('\\n', ' ').replace('\\"', '"').strip()
            if len(content) < 10:
                logger.warning(f"Content too short for document: {title}")
                continue
                
            citation = {
                "title": f"{title}: {url}" if url else title,
                "snippet": content
            }
            
            logger.debug(f"Processed document - Title: {title}")
            logger.debug(f"Content length: {len(content)}")
            
            citations.append(citation)
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            continue
    
    if not citations:
        logger.error("No documents were processed")
        raise ValueError("No documents were provided")
        
    logger.info(f"Successfully processed {len(citations)} documents")
    return citations

class NovaChat(BedrockModel):
    """A class for generating responses using Nova."""
    
    def __init__(self, model_id='amazon.nova-lite-v1:0', region_name='us-east-1'):
        """
        Initializes the NovaChat class, inheriting from BedrockModel.
        """
        super().__init__(model_id, region_name)

    def nova_chat(
            self,
            query: str,
            retrieved_docs: List[Dict],
            description: str = None,
            max_tokens: int = 1000,
            temperature: float = 0.7
        ) -> Tuple[str, List[str]]:
        """
        Generate a response using Nova given a query and relevant documents.
        
        Args:
            query (str): User's query
            retrieved_docs (List[Dict]): List of relevant documents
            description (str, optional): Additional context or instructions
            max_tokens (int): Maximum tokens in output
            temperature (float): Controls randomness
            
        Returns:
            Tuple[str, List[str]]: Generated response and citations
        """
        try:
            # Format documents and build context
            formatted_docs = []
            urls = []  # Track URLs for citation
            
            for doc in retrieved_docs:
                if not doc.get('content'):
                    continue
                    
                # Format document content
                formatted_doc = {
                    'title': doc.get('title', 'Untitled'),
                    'content': doc.get('content', '').strip(),
                    'url': doc.get('url', [''])[0] if isinstance(doc.get('url', []), list) else doc.get('url', '')
                }
                
                # Only include if there's content
                if formatted_doc['content']:
                    formatted_docs.append(formatted_doc)
                    if formatted_doc['url']:
                        urls.append(formatted_doc['url'])

            # Build prompt
            prompt = self._build_prompt(query, formatted_docs, description)
            
            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ],
                    "inferenceConfig": {
                        "maxTokens": max_tokens,
                        "temperature": temperature
                    }
                })
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            generated_text = response_body['output']['message']['content'][0]['text']
            
            # Return response and citations
            return generated_text, urls[:5]  # Limit to top 5 citations
            
        except Exception as e:
            logger.error(f"Error in chat generation: {str(e)}")
            raise

    def _build_prompt(self, query: str, docs: List[Dict], description: str = None) -> str:
        """Build the prompt for Nova using query and documents."""
        # Start with base instructions
        prompt = [
            "You are a helpful climate science expert. Answer the question based ONLY on the provided content.",
            "Be direct, accurate, and focused on climate topics.",
            "If information is insufficient, say so rather than speculating."
        ]
        
        # Add custom description if provided
        if description:
            prompt.append(description)
            
        # Add query
        prompt.append(f"\nQuestion: {query}")
        
        # Add document content
        prompt.append("\nHere are relevant sources to answer from:")
        
        for i, doc in enumerate(docs, 1):
            prompt.append(f"\nSource {i}:")
            if doc.get('title'):
                prompt.append(f"Title: {doc['title']}")
            prompt.append(f"Content: {doc['content']}\n")
            
        # Add final instruction
        prompt.append("\nProvide a clear, factual answer using only the information from these sources.")
        
        return "\n".join(prompt)

# Test code
if __name__ == "__main__":
    from src.utils.env_loader import load_environment
    load_environment()
    
    # Initialize chat
    chat = NovaChat()
    
    # Test documents
    test_docs = [
        {
            'title': 'Climate Change Overview',
            'content': 'Climate change is a long-term shift in global weather patterns and temperatures.',
            'url': ['https://example.com/climate1']
        },
        {
            'title': 'Climate Impact Report',
            'content': 'Rising temperatures are causing more extreme weather events worldwide.',
            'url': ['https://example.com/climate2']
        }
    ]
    
    # Test query
    test_query = "What is climate change and its effects?"
    
    try:
        print("\nTesting Nova chat generation...")
        response, citations = chat.nova_chat(test_query, test_docs)
        print("\nQuery:", test_query)
        print("\nResponse:", response)
        print("\nCitations:", citations)
    except Exception as e:
        print(f"Error in test: {str(e)}")