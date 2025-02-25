import boto3
import json
import os
from ..utils.env_loader import load_environment

class BedrockModel:
    def __init__(self, model_id='amazon.nova-micro-v1:0', region_name='us-east-1'):
        """
        Initializes the Bedrock Model client.
        Args:
            model_id (str): The ID of the model to interact with.
            region_name (str): AWS region where Bedrock is deployed.
        """
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=region_name,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        self.model_id = model_id

    def nova_translation(self, input_text: str, input_language: str, output_language: str, max_tokens=1000, temperature=0.7) -> str:
        """
        Translates text using Amazon Nova Micro.

        Args:
            input_text (str): The input text to translate.
            input_language (str): The input language name
            output_language (str): The output language name
            max_tokens (int): Maximum number of tokens in the output.
            temperature (float): Controls the randomness of the output.

        Returns:
            str: Translated text.
        """
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"text": f"Provide ONLY a direct translation of {input_text} from {input_language} to {output_language}"} 
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature
            }
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload)
            )
            response_body = json.loads(response['body'].read())
            return response_body['output']['message']['content'][0]['text']
        except Exception as e:
            #self.logger.error(f"Translation failed for language '{output_language}': {e}")
            return None

    def query_normalizer(self, query: str, language_name: str, max_tokens=1000, temperature=0.7) -> str:
        """
        Rephrase and normalize the query using Amazon Nova Micro.

        Args:
            query (str): The input query
            max_tokens (int): Maximum number of tokens in the output.
            temperature (float): Controls the randomness of the output.

        Returns:
            str: simplified and normalized query.
        """
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"text": f"""Rephrase the following query to its simplest, most basic form:
                                    1. Remove any personal information.
                                    2. Convert the query into simple, direct questions or statements.
                                    3. If the query contains multiple parts (e.g., multiple questions), preserve them separately but make them as basic as possible.
                                    4. If the query is already simple and in its basic form, leave it unchanged.
                                    Respond with ONLY the rephrased query, without any additional text or explanation.  
                                    Provide the rephrased query in {language_name}.  
                                    Query: {query}
                                    """
                        } 
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature
            }
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload)
            )
            response_body = json.loads(response['body'].read())
            return response_body['output']['message']['content'][0]['text']
        except Exception as e:
            raise RuntimeError(f"Error invoking model: {e}")
        
# Example Usage
if __name__ == "__main__":
    # Load environment variables from env_loader file
    load_environment()
    # Initialize the BedrockModel class with your model ID
    model = BedrockModel("amazon.nova-micro-v1:0")

    # Define the input text to translate
    #input_text = """
    #                Klimaatsverandering is 'n groot sak, en dit gaan oor hoe ons planeet se weerpatrone lanktermyn verander. Dink daaraan so:
    #                Weerpatrone: Klimaatsverandering is soos 'n langtermynverskuiwing in die gewoonlike weerpatrone, soos temperatuur en reënval.
    #                Tijd skakel: Hierdie veranderings gebeur nie oornag nie; hulle bly lank, dikwels dekades of meer.
    #                Oorsae: Klimaatsverandering kan plaasvind weens natuurlike dinge, soos vulkaanuitbarstings of die son se energie wat verander. Maar tans word dit hoofsaaklik veroorsaak deur menslike aktiwiteite, veral die verbranding vanfossiele brandstowwe, wat gasse vrystel wat hitte in ons atmosfeer vastig.
    #                Wêreldwye Impakt: Dit is nie net een plek nie; klimaatsverandering vind wêreldwyd plaas, en dit is 'n groot uitdaging vir almal.
    #                D us, klimaatsverandering is soos 'n lanktermynverskuiwing in ons planeet se weer, en dit is iets wat ons saam moet verstaan en aanpak.
    #                """
    #input_language='afrikaans'
    #output_language = 'english'
    # Translate the text 
    #try:
    #    translated_text = model.nova_translation(input_text, input_language, output_language)
    #    print("Translated Text:\n", translated_text)
    #except RuntimeError as e:
    #    print(e)

    queries = [
        ('what is climate change? why should we care?','english'),
        ('what is climate change and why should we care? ','english'),
        ("I am John from Boston and I am curious to learn about climate change. what is it?",'english'),
        ("I am anxious about climate change? what should I do?",'english'),
        ("tell me about climate change.",'english'),
        ("could you please explain what climate change is?",'english'),
        ('what is difference between climate and weather?','english'),
        ('are climate and weather different? how?','english'),
        ('tell me about difference between climate and weather.','english'),
        ('I have climate anxiety. what is it?','english'),
        ('what is climate anxiety?','english'),
        ('ممکن است درباره تغییرات اقلیمی توضیح دهید؟','persian'),
        ('تغییرات اقلیمی یعنی چه؟','persian'),
        #('Mi amigo y yo estábamos hablando sobre el cambio climático. Tenemos curiosidad por saber más al respecto','spanish')
    ]

    for query, language_name in queries:
        rephrased_query = model.query_normalizer(query, language_name)
        print('originial: ',query)
        print('rephrased: ',rephrased_query)
        print('-'*50)
