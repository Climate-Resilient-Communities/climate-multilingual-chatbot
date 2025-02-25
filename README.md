# Multilingual Climate Change Chatbot Application

A sophisticated multilingual chatbot specialized in climate-related topics, featuring RAG (Retrieval Augmented Generation) and various guardrails for input validation and output quality.

## Features

- Multilingual support through Amazon Nova translation
- RAG implementation with Pinecone and BGE embeddings
- Input validation and topic moderation
- Hallucination detection and quality checks
- Redis caching for improved performance
- Streamlit web interface

## Prerequisites

- Python 3.11+
- Poetry for dependency management
- AWS credentials for Bedrock
- API keys for various services (Cohere, Pinecone, etc.)

## Installation

1. Install Poetry if you haven't already:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clone the repository:
```bash
git clone https://github.com/yourusername/MLCCAPP.git
cd MLCCAPP
```

3. Install dependencies:
```bash
poetry install
```

4. Set up environment variables:
Create a `.env` file in the root directory with:
```env
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
PINECONE_API_KEY=your_pinecone_key
COHERE_API_KEY=your_cohere_key
TAVILY_API_KEY=your_tavily_key
HF_API_TOKEN=your_huggingface_token
```

## Usage

1. Activate the Poetry environment:
```bash
poetry shell
```

2. Run the application:
```bash
poetry run mlccapp climate-change-adaptation-index-10-24-prod
```

Or run the web interface:
```bash
poetry run streamlit run src/webui/app_nova.py
```

## Development

- Format code:
```bash
poetry run black .
poetry run isort .
```

- Check code quality:
```bash
poetry run flake8
```

## License

This project is licensed under the terms of the license included with this repository.
