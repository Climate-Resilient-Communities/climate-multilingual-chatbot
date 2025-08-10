# Azure Deployment Guide for Climate Multilingual Chatbot

This guide provides instructions for deploying the Climate Multilingual Chatbot to Azure App Service.

## Prerequisites

- Azure account with active subscription
- Azure CLI installed (optional, for command-line deployments)
- Docker installed (optional, for container deployments)

## Important: Model Preparation

The application no longer requires bundling a local ClimateBERT model. Ensure environment variables are configured and network access to providers is available.

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

### Option 2: Manual Model Upload (Legacy)

Previously we supported bundling `models/climatebert/`. This is no longer required and is not recommended.

### Handling Git LFS in Docker Deployments

If you use containers, no local HF model bundling is necessary for this app.

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

### Method 1: Direct Deployment from GitHub (Recommended)

1. In the Azure Portal, create a new App Service
2. Under Deployment Center, select GitHub as your source
3. Configure the deployment to use the GitHub repository
4. Configure the environment variables listed above
5. Deploy the application

### Method 2: Docker Container Deployment 

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
   - If you see `git`-related errors when installing optional packages, ensure dependencies are preinstalled in your runtime. No local HF model download step is required.

5. **Hugging Face Model Download Issues**
   - The app no longer downloads HF models at runtime; this section is not applicable.

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