# Azure Deployment Guide for Climate Multilingual Chatbot

This guide provides instructions for deploying the Climate Multilingual Chatbot to Azure App Service.

## Prerequisites

- Azure account with active subscription
- Azure CLI installed (optional, for command-line deployments)
- Docker installed (optional, for container deployments)

## Important: Local Model Preparation

In Azure environments, accessing Hugging Face models can be problematic due to Git dependencies. To ensure your deployment works properly:

1. **Download models locally before deployment:**
   ```bash
   python src/utils/download_models.py
   ```

2. **Include the models directory in your deployment package** - This ensures the application can use local model files instead of downloading them during runtime.

3. **Make sure the models directory structure is preserved:** The application expects models at `models/climatebert/` relative to the project root.

## Using Git LFS for Model Files

Since the model files are large, we use Git LFS (Large File Storage) to manage them efficiently. When deploying to Azure:

### Option 1: Clone with Git LFS Support

If your Azure App Service has Git LFS installed and configured:

1. Make sure Git LFS is correctly set up in your deployment workflow:
   ```bash
   git lfs install
   git clone https://github.com/yourusername/climate-multilingual-chatbot.git
   ```

2. Verify the model files were properly downloaded:
   ```bash
   ls -la models/climatebert/
   ```

### Option 2: Manual Model Upload (Recommended for Azure)

For Azure App Service deployments where Git LFS might not be available:

1. Download models locally first:
   ```bash
   python src/utils/download_models.py
   ```

2. When deploying to Azure, ensure the model files are included in your deployment package
   - For GitHub Actions: Use the `actions/upload-artifact` to include the models directory
   - For manual deployments: Use `az webapp deploy` with the entire directory including models

3. Verify the model directory exists in your Azure App Service:
   ```
   /home/site/wwwroot/models/climatebert/
   ```

### Handling Git LFS in Docker Deployments

Our Docker configuration already handles copying the local model files into the container. Make sure the models are downloaded before building your Docker image:

```bash
# Download models locally
python src/utils/download_models.py

# Build Docker image (the models will be included)
docker build -t climate-chatbot:latest .
```

## Configuration Options

### 1. Environment Variables

The following environment variables should be configured in your Azure App Service:

#### Required API Keys:
- `COHERE_API_KEY`: Cohere API key for embeddings and reranking
- `PINECONE_API_KEY`: Pinecone API key for vector database
- `TAVILY_API_KEY`: Tavily API key for search
- `HF_API_TOKEN`: Hugging Face token for model access
- `AWS_ACCESS_KEY_ID`: AWS access key for Bedrock
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for Bedrock

#### Optional Environment Variables:
- `LANGSMITH_API_KEY`: LangSmith API key for tracing (recommended)
- `LANGSMITH_PROJECT`: LangSmith project name (default: "climate-chat-production")
- `REDIS_HOST`: Redis host address (default: "localhost")
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_PASSWORD`: Redis password if required
- `AZURE_REDIS_SSL`: Set to "true" if using Azure Redis Cache (default: auto-detect)
- `HF_HUB_DISABLE_SYMLINKS_WARNING`: Set to "1" to disable Hugging Face symlinks warnings
- `HF_HUB_DISABLE_IMPLICIT_TOKEN`: Set to "1" to disable implicit token authentication

### 2. Azure Redis Cache

For production deployments, we recommend using Azure Redis Cache:

1. Create an Azure Redis Cache instance in the Azure Portal
2. Configure the following environment variables:
   - `REDIS_HOST` or `AZURE_REDIS_HOST`: Your Redis instance hostname
   - `REDIS_PORT` or `AZURE_REDIS_PORT`: Your Redis instance port (typically 6380 for SSL)
   - `REDIS_PASSWORD` or `AZURE_REDIS_PASSWORD`: Your Redis instance access key
   - `AZURE_REDIS_SSL`: Set to "true" (Azure Redis Cache requires SSL)

## Deployment Methods

### Method 1: Direct Deployment from GitHub

1. In the Azure Portal, create a new App Service
2. Under Deployment Center, select GitHub as your source
3. Configure the deployment to use the GitHub repository
4. Configure the environment variables listed above
5. Deploy the application

### Method 2: Docker Container Deployment (Recommended)

1. Build the Docker container:
   ```bash
   docker build -t climate-chatbot:latest .
   ```

2. Push to Azure Container Registry:
   ```bash
   az acr login --name <your-registry-name>
   docker tag climate-chatbot:latest <your-registry-name>.azurecr.io/climate-chatbot:latest
   docker push <your-registry-name>.azurecr.io/climate-chatbot:latest
   ```

3. Deploy to Azure App Service from the container registry

## Application Insights

To enable application telemetry:

1. Create an Application Insights resource in Azure
2. Add the connection string as an environment variable:
   - `APPLICATIONINSIGHTS_CONNECTION_STRING`: Your Application Insights connection string
3. Install the required package:
   ```bash
   pip install opencensus-ext-azure
   ```

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   - Check if all required environment variables are set in App Service Configuration

2. **Redis Connection Issues**
   - Ensure firewall rules allow connections to Redis
   - Verify SSL setting is enabled for Azure Redis Cache
   - Check if Redis password is correct

3. **API Key Authentication Failures**
   - Verify all API keys are valid and not expired
   - Check for any special characters that might need escaping

4. **Git Not Found Error**
   - This is common in Azure environments: `Failed to initialize chatbot: [Errno 2] No such file or directory: 'git'`
   - Solution: Ensure you've downloaded models locally with `python src/utils/download_models.py` before deployment
   - The application has been modified to handle this case by loading models from local paths

5. **Hugging Face Model Download Issues**
   - If you see errors related to downloading models from Hugging Face, make sure your deployment includes the local model files
   - Check that the `models/climatebert` directory exists and contains all model files

### Logs

Access logs through:
- Azure Portal > Your App Service > Logs
- Application Insights if configured
- Kudu console at https://your-app-name.scm.azurewebsites.net/

## Performance Optimization

For better performance on Azure:
- Scale up your App Service Plan as needed
- Use Premium tier for production workloads
- Consider enabling autoscaling for variable loads
- Use Azure Redis Cache for session state and caching