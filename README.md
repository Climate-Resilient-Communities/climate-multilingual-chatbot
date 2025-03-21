# Multilingual Climate Change Chatbot Application

A sophisticated multilingual chatbot specialized in climate-related topics, leveraging advanced RAG (Retrieval Augmented Generation) architecture with Amazon Bedrock for response generation and multiple guardrails for quality assurance.

## Features

- **Multilingual Support**: Seamless multilingual interactions powered by Amazon Bedrock Nova
- **Advanced RAG Implementation**: 
  - Hybrid search with Pinecone vector store
  - BGE-M3 embeddings for superior semantic understanding
  - Cohere reranking for enhanced result relevance
- **Quality Assurance**:
  - Input validation and topic moderation
  - Hallucination detection
  - Response quality checks
- **Performance Optimizations**:
  - Redis caching layer
  - Asynchronous processing
  - Efficient document processing pipeline
- **User Interface**:
  - Clean, responsive Streamlit web interface
  - Source citations with detailed references
  - Chat history management

## Prerequisites

- Python 3.11 or higher
- Poetry for dependency management
- Redis server (optional, for caching)
- API Keys for:
  - AWS (for Amazon Bedrock)
  - Pinecone
  - Cohere
  - Hugging Face (optional)

## Installation

1. Install Poetry if not already installed:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clone the repository:
```bash
git clone https://github.com/yourusername/climate-multilingual-chatbot.git
cd climate-multilingual-chatbot
```

3. Install dependencies:
```bash
poetry install
```

4. Configure environment variables:
Create a `.env` file in the root directory with:
```env
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
PINECONE_API_KEY=your_pinecone_key
COHERE_API_KEY=your_cohere_key
HF_API_TOKEN=your_huggingface_token  # Optional
```

5. Download models for offline usage (recommended for Azure deployment):
```bash
python src/utils/download_models.py
```
This will download the ClimateBERT model files to the `models/climatebert` directory, allowing the application to work without internet access to Hugging Face.

## Usage

1. Activate the Poetry environment:
```bash
poetry shell
```

2. Start Redis server (optional, for caching):
```bash
redis-server
```

3. Run the web interface:
```bash
poetry run streamlit run src/webui/app_nova.py
```

Or run as a CLI application:
```bash
python src/main_nova.py climate-change-adaptation-index-10-24-prod
```

## Project Structure

```
climate-multilingual-chatbot/
├── models/                  # Local model files
│   └── climatebert/        # Downloaded ClimateBERT model files
├── src/                     # Main source code
│   ├── models/             # Core model implementations
│   ├── utils/              # Utility functions
│   └── webui/              # Streamlit web interface
├── tests/                   # Test suites
│   ├── integration/        # Integration tests
│   ├── system/             # System tests
│   └── unit/               # Unit tests
├── .env                     # Environment variables (not in repo)
├── poetry.lock             # Lock file for dependencies
├── pyproject.toml          # Project configuration
└── README.md              # Project documentation
```

## Azure Deployment

For Azure deployment, it's recommended to:

1. Download models locally before deployment using:
   ```bash
   python src/utils/download_models.py
   ```

2. Configure Azure App Service environment variables as described in `AZURE_DEPLOYMENT.md`

3. Review the Azure specific configurations in `AZURE_DEPLOYMENT.md`

See the `AZURE_DEPLOYMENT.md` file for detailed Azure deployment instructions.

## Development

Format code:
```bash
poetry run black .
poetry run isort .
```

Run tests:
```bash
poetry run pytest
```

Check code quality:
```bash
poetry run flake8
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

### Common Issues

1. **Model Loading Issues**
   - If you encounter issues with Hugging Face models in Azure, make sure you've downloaded the models locally using the provided script
   - Check that the models directory exists and contains the required files

2. **Git Not Found Error in Azure**
   - This is expected in some Azure environments. The application should handle this gracefully by using the local model files.

3. **Environment Variables**
   - Ensure all required environment variables are properly set

## License

This project is licensed under the terms of the license included with this repository.

## Acknowledgments

- Amazon Bedrock for the Nova language model
- Pinecone for vector storage
- Cohere for reranking capabilities
- Streamlit for the web interface framework
