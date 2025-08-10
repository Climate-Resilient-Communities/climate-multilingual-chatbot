# Multilingual Climate Change Chatbot (MLCC)

Production notes
- Local JSONL chat logs are disabled by default. To enable locally, set `ENABLE_LOCAL_CHAT_LOGS=1`. Azure Blob logging remains enabled when Azure env vars are present.
- All project documentation lives under `info/`.
- The consent/Disclaimer is a true overlay via Streamlit `@st.dialog` and app is gated with `st.stop()` until accepted.
- The query rewriter now returns strict JSON; the pipeline short-circuits for canned intents (greeting/goodbye/thanks/emergency) and for "instruction" shows the How It Works text. Canned text is translated to the user’s selected language.

A multilingual climate chatbot built on RAG with Cohere Command A and Amazon Bedrock (Nova) both open source plus robust retrieval, safety, and UI refinements.

## Features

- **Multilingual Support**: 200+ languages in dropdown; responses translated to the selected language
- **Consent Modal**: Elegant overlay modal gating app usage
- **Advanced RAG Implementation**: 
  - Hybrid search with Pinecone vector store
  - BGE-M3 embeddings for superior semantic understanding
  - Cohere reranking for enhanced result relevance
- **Quality Assurance**:
  - Input validation and topic moderation
  - Hallucination detection
  - Response quality checks
- **Intent Handling**:
  - LLM-based classification into on-topic, off-topic, harmful, greeting, goodbye, thanks, emergency, instruction
  - Pre-canned responses for selected intents, translated to user language
- **Performance Optimizations**:
  - Redis caching layer
  - Asynchronous processing
  - Efficient document processing pipeline
- **User Interface**:
  - Clean, responsive Streamlit web interface
  - Source citations with detailed references
  - Chat history management
  - Sidebar improvements: dark theme, downloadable chat history icon with tooltip
  - Feedback button linking to Google Form

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

5. (Legacy) Local HF model download
Not required anymore. The application no longer depends on local ClimateBERT downloads.

## Important: Using Poetry Environment

**Always use `poetry run` when executing Python scripts or tests** to ensure you're using the correct virtual environment with all dependencies properly installed:

```bash
# ✅ Correct - Use poetry run for scripts
poetry run python test_deployment.py
poetry run python src/main_nova.py
poetry run streamlit run src/webui/app_nova.py

# ❌ Incorrect - May use wrong Python environment
python test_deployment.py
python src/main_nova.py
```

This is especially important because:
- Poetry manages its own virtual environment with exact dependency versions
- Direct `python` commands may use system Python or wrong virtual environment
- Missing dependencies errors typically indicate not using `poetry run`

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

Or run as a CLI application the second part is your pinecone index in the example below this is ours:
```bash
python src/main_nova.py climate-change-adaptation-index-10-24-prod
```

## Project Structure

```
climate-multilingual-chatbot/
├── src/
│   ├── webui/              # Streamlit UI (app_nova.py)
│   ├── models/             # Pipeline, retrieval, guards
│   └── utils/              # Env, logging, language maps
├── tests/                  # Unit, integration, system tests
├── info/                   # All markdown docs
├── reports/                # Generated charts/reports
├── Multilingual testing/   # Local bake-off utilities and cache
├── .env                    # Environment variables (not in repo)
├── poetry.lock             # Lock file
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## Azure Deployment

For Azure deployment, it's recommended to:

Configure Azure App Service environment variables as described in `info/AZURE_DEPLOYMENT.md`. The app no longer requires bundling a local ClimateBERT model.

See the `AZURE_DEPLOYMENT.md` file for detailed Azure deployment instructions.

## Development

**Important**: Always use `poetry run` for development commands to ensure proper environment:

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

Run deployment readiness tests:
```bash
poetry run python test_deployment.py
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
