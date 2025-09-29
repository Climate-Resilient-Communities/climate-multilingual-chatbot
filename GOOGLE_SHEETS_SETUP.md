# Google Sheets API Setup Guide

## Current Issue
Your current `service_account.json` file contains OAuth2 web client credentials, but we need **Service Account** credentials for server-to-server access to Google Sheets.

## Steps to Get Service Account Credentials

### 1. Go to Google Cloud Console
- Visit: https://console.cloud.google.com/
- Select your project: `climate-resilient-communities`

### 2. Enable Google Sheets API
- Go to **APIs & Services** → **Library**
- Search for "Google Sheets API"
- Click **Enable** if not already enabled

### 3. Create Service Account
- Go to **APIs & Services** → **Credentials**
- Click **+ CREATE CREDENTIALS** → **Service Account**
- Fill in:
  - **Service account name**: `climate-chatbot-sheets`
  - **Service account ID**: `climate-chatbot-sheets` (auto-filled)
  - **Description**: `Service account for climate chatbot feedback sheets`
- Click **CREATE AND CONTINUE**
- Skip roles for now, click **CONTINUE**
- Click **DONE**

### 4. Generate Service Account Key
- In the **Credentials** page, find your new service account
- Click on the service account email
- Go to **Keys** tab
- Click **ADD KEY** → **Create new key**
- Select **JSON** format
- Click **CREATE**
- **Download the JSON file** and replace your current `service_account.json`

### 5. Share Google Sheet with Service Account
- Open your Google Sheet: https://docs.google.com/spreadsheets/d/153jsk_B5l6Rsjtn6lm5j8LUc8sh-Bi8mB3dfxx6YYcs
- Click **Share** button
- Add the service account email (looks like `climate-chatbot-sheets@climate-resilient-communities.iam.gserviceaccount.com`)
- Give it **Editor** permissions
- Click **Send**

## What the Correct service_account.json Should Look Like

```json
{
  "type": "service_account",
  "project_id": "climate-resilient-communities",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n",
  "client_email": "climate-chatbot-sheets@climate-resilient-communities.iam.gserviceaccount.com",
  "client_id": "123456789...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

## Test the Setup

Once you have the correct service account file:

1. **Test the admin API server**:
   ```bash
   python admin_api_server.py
   ```

2. **Test feedback submission**:
   - Submit feedback through your chatbot
   - Check if it appears in both Redis and Google Sheets

3. **Test admin dashboard**:
   - Open the admin dashboard modal
   - Enter password: `mlcc_2025`
   - Check if real data shows up

## Current Configuration in .env
```
GOOGLE_SHEETS_ID=153jsk_B5l6Rsjtn6lm5j8LUc8sh-Bi8mB3dfxx6YYcs
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
ADMIN_PASSWORD=mlcc_2025
```

This is correct - just need to replace the service account file with the right format!