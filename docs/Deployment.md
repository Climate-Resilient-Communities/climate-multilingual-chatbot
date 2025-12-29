# Azure App Service Deployment Guide (Next.js + FastAPI/Python)

This guide shows a robust way to deploy this repository to Azure App Service as a single app that:
- Builds the Next.js frontend (static export) and serves it via FastAPI
- Runs the FastAPI backend (uvicorn/gunicorn) on port 8000
- Uses Oryx build automation on Azure (recommended) or an optional custom container
- Uses GitHub Actions for CI/CD

Authoritative references
- Configure Python on App Service (Oryx, startup, logs): https://learn.microsoft.com/azure/app-service/configure-language-python
- GitHub Actions for App Service: https://learn.microsoft.com/azure/app-service/deploy-github-actions
- Oryx build system: https://github.com/microsoft/Oryx
- Custom container on App Service (optional): https://learn.microsoft.com/azure/app-service/configure-custom-container?pivots=container-linux


## 1) App structure assumptions

- Backend entrypoint: `src/webui/api/main.py` exposing `app`
- Frontend: Next.js app in `src/webui/app` with static export to `out/`
- Requirements file: `requirements.txt` at repo root (required by App Service)
- Python version: 3.11+


## 2) Recommended approach: Built-in Python on App Service (with Oryx)

Oryx automatically installs Python dependencies (`pip install -r requirements.txt`) and can also run Node-based build steps for the frontend using pre-/post-build commands.

### 2.1 Create the Web App (CLI)

```bash
# Variables (edit these)
RESOURCE_GROUP="rg-mlcc"
LOCATION="canadacentral"   # pick your region
PLAN_NAME="asp-mlcc"
APP_NAME="mlcc-chatbot"

# Create resource group
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Create Linux App Service Plan (Basic or higher recommended for ML/RAG)
az appservice plan create \
  --name "$PLAN_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --sku B1 --is-linux

# Create Web App with Python runtime
az webapp create \
  --resource-group "$RESOURCE_GROUP" \
  --plan "$PLAN_NAME" \
  --name "$APP_NAME" \
  --runtime "PYTHON|3.11"

# Confirm runtime
az webapp config show -g "$RESOURCE_GROUP" -n "$APP_NAME" --query linuxFxVersion
```

### 2.2 Configure build automation (Oryx)

Set these app settings so App Service builds your code on deploy, including our Node build for the Next.js subfolder.

```bash
# Enable Oryx build during deployment
az webapp config appsettings set -g "$RESOURCE_GROUP" -n "$APP_NAME" \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=1

# Pre-build: build Next.js static export inside the subfolder
# Using npm ci for reproducibility; falls back to npm install if lockfile not present
az webapp config appsettings set -g "$RESOURCE_GROUP" -n "$APP_NAME" \
  --settings PRE_BUILD_COMMAND="cd src/webui/app && (npm ci || npm install) && npm run build"

# Optional: Post-build hooks (e.g., sanity checks)
az webapp config appsettings set -g "$RESOURCE_GROUP" -n "$APP_NAME" \
  --settings POST_BUILD_COMMAND="echo build complete"
```

Notes
- Oryx will install Python deps from `requirements.txt` at the repo root.
- Oryx has Node and npm available to run the frontend build.
- With Oryx build automation, content may run under a temp path (`/tmp/<uid>`). Your app should rely on relative paths inside the repo and not hard-coded absolute paths. This repo already serves `src/webui/app/out/` with FastAPI; the build step above ensures it exists at runtime.

### 2.3 Configure the startup command (Gunicorn + UvicornWorker)

For production-grade ASGI hosting on App Service, use Gunicorn with the Uvicorn worker.

```bash
# Start FastAPI via Gunicorn + UvicornWorker on port 8000
# NUM_CORES is provided in App Service; scale workers dynamically
STARTUP_CMD="gunicorn --bind=0.0.0.0:8000 --timeout 600 \
  --workers=$(((${NUM_CORES:-1}*2)+1)) \
  -k uvicorn.workers.UvicornWorker src.webui.api.main:app"

az webapp config set -g "$RESOURCE_GROUP" -n "$APP_NAME" \
  --startup-file "$STARTUP_CMD"

# Ensure port is visible for health checks
az webapp config appsettings set -g "$RESOURCE_GROUP" -n "$APP_NAME" \
  --settings WEBSITES_PORT=8000
```

Tip: If you prefer plain Uvicorn (simpler, fewer features), use:
```bash
az webapp config set -g "$RESOURCE_GROUP" -n "$APP_NAME" \
  --startup-file "uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000"
```

### 2.4 App settings (environment variables)

Set your secrets as App Settings. They’re injected as environment variables:

```bash
az webapp config appsettings set -g "$RESOURCE_GROUP" -n "$APP_NAME" --settings \
  COHERE_API_KEY="<secret>" \
  PINECONE_API_KEY="<secret>" \
  TAVILY_API_KEY="<secret>" \
  HF_API_TOKEN="<secret>" \
  AWS_ACCESS_KEY_ID="<secret>" \
  AWS_SECRET_ACCESS_KEY="<secret>" \
  REDIS_HOST="<redis-host>" \
  REDIS_PORT="6380" \
  REDIS_SSL="1" \
  LANGSMITH_API_KEY="<optional>" \
  LANGSMITH_PROJECT="<optional>"
```

### 2.5 Logging and troubleshooting

```bash
# Enable log streaming
az webapp log config --name "$APP_NAME" -g "$RESOURCE_GROUP" --docker-container-logging filesystem

# Stream logs
az webapp log tail --name "$APP_NAME" -g "$RESOURCE_GROUP"
```

Common checks
- If you see the default placeholder site, verify `SCM_DO_BUILD_DURING_DEPLOYMENT=1` and deployment logs in Deployment Center.
- Ensure `requirements.txt` is in repo root.
- If app won’t start, verify the startup command and import path `src.webui.api.main:app`.


## 3) CI/CD with GitHub Actions (single web app)

Recommended: OpenID Connect (OIDC) auth. Simpler alternative below uses publish profile.

### 3.1 Minimal workflow (publish profile)

Create `.github/workflows/azure-appservice.yml`:

```yaml
name: Deploy to Azure App Service

on:
  push:
    branches: [ main ]

env:
  AZURE_WEBAPP_NAME: mlcc-chatbot  # your app name
  AZURE_RESOURCE_GROUP: rg-mlcc    # your resource group

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      # Optional: Validate builds before deploy (CI fast feedback)
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Frontend build (validate only)
        run: |
          cd src/webui/app
          npm ci || npm install
          npm run build

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Python deps (validate only)
        run: |
          pip install -r requirements.txt
          # pytest -q  # optionally run tests

      # Deploy repo to App Service; Oryx builds on server
      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ env.AZURE_WEBAPP_NAME }}
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
          package: .
```

Notes
- Add the secret `AZURE_WEBAPP_PUBLISH_PROFILE` from the App Service “Download publish profile” (Overview blade). Ensure basic auth is enabled per docs.
- Oryx runs server-side because `SCM_DO_BUILD_DURING_DEPLOYMENT=1`.

### 3.2 OIDC alternative (recommended security)

Use `azure/login` with federated credentials and `azure/webapps-deploy`:

```yaml
- name: Azure Login (OIDC)
  uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

- name: Deploy to Azure Web App (OIDC)
  uses: azure/webapps-deploy@v3
  with:
    app-name: ${{ env.AZURE_WEBAPP_NAME }}
    package: .
```

Refer to the GitHub/Azure OIDC setup guide for creating the federated credential.


## 4) Alternative: appsvc.yaml for explicit Oryx build/run (optional)

Place `appsvc.yaml` at repo root to explicitly control build steps and run command.

```yaml
version: 1

pre-build: |
  cd src/webui/app
  npm ci || npm install
  npm run build

post-build: |
  echo "Build completed"

# Equivalent to Startup Command in portal
run: |
  gunicorn --bind=0.0.0.0:8000 --timeout 600 \
    --workers=$(((${NUM_CORES:-1}*2)+1)) \
    -k uvicorn.workers.UvicornWorker src.webui.api.main:app
```

If both `appsvc.yaml` and a portal Startup Command are present, the portal startup usually takes precedence. Prefer one source of truth.


## 5) Optional: custom container deployment

If you prefer a container image or need system-level packages, use a multi-stage Dockerfile:

```dockerfile
# --- Frontend build stage ---
FROM node:20-alpine AS web-build
WORKDIR /app
COPY src/webui/app/package*.json ./
RUN npm ci || npm install
COPY src/webui/app/ .
RUN npm run build   # produces out/

# --- Backend/runtime stage ---
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY src/ ./src/

# Copy static export from stage
COPY --from=web-build /app/out/ ./src/webui/app/out/

# Gunicorn + Uvicorn worker
EXPOSE 8000
ENV WEBSITES_PORT=8000
CMD ["bash", "-lc", "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers=$((($(nproc)*2)+1)) -k uvicorn.workers.UvicornWorker src.webui.api.main:app"]
```

Push to ACR or Docker Hub, then configure the Web App for a custom container and set:
- `WEBSITES_PORT=8000`
- App settings (secrets) as above
- (Optional) managed identity to pull from ACR

See: Configure a custom container (port, env, logs) in the docs linked above.


## 6) Health checks and static files

- Health endpoints are already implemented (`/health/live`, `/health/ready`).
- Static assets: FastAPI serves `src/webui/app/out/` and mounts `/_next` correctly. The pre-build step must run successfully so these directories exist at runtime.


## 7) Environment variables (project-specific)

Required
- COHERE_API_KEY
- PINECONE_API_KEY
- TAVILY_API_KEY
- HF_API_TOKEN
- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

Recommended
- REDIS_HOST, REDIS_PORT, REDIS_SSL=1
- LANGSMITH_API_KEY, LANGSMITH_PROJECT

Platform
- SCM_DO_BUILD_DURING_DEPLOYMENT=1
- PRE_BUILD_COMMAND (as shown)
- POST_BUILD_COMMAND (optional)
- WEBSITES_PORT=8000


## 8) Quick verification checklist

- App Settings: runtime and variables configured
- Deployment logs show Oryx detected Python and ran pre-build Node steps
- `/_next` responds and chat API works
- Log stream free of import/startup errors


## 9) Notes about this repository

- Prefer the Gunicorn+UvicornWorker startup over any legacy startup scripts (e.g., `azure_startup.sh` that start Streamlit). Ensure your App Service “Startup Command” uses the Gunicorn command shown above.
- This repo already has `requirements.txt` at root; Oryx will install from it.


## 10) Troubleshooting pointers

- Default site still appears: enable `SCM_DO_BUILD_DURING_DEPLOYMENT=1`, redeploy, and review Deployment Center logs.
- ModuleNotFoundError: don’t deploy virtualenvs; let Oryx create venv and install from `requirements.txt`.
- Slow startup on free/shared plans: try a larger plan tier or enable Always On.


---

Happy shipping!
