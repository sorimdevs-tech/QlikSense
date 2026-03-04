# Qlik LoadScript Fetching - Setup Guide

## Problem
When you click on an app to view its LoadScript, you get an error (500 Internal Server Error). This is because the backend doesn't have your Qlik Cloud API credentials configured.

## Solution
You need to provide your Qlik API Key to enable LoadScript fetching. There are two ways to do this:

### Option 1: Via the Frontend (Recommended - Easier)

1. **Go to Qlik Cloud Console** and generate an API Key:
   - Open: https://c8vlzp3sx6akvnh.in.qlikcloud.com/console
   - Click **Admin** → **API Keys** → **Create new**
   - Select scopes: 
     - `apps:read`
     - `apps:read_script` 
     - `data:read`
   - Click **Create**
   - Copy the generated API Key

2. **Provide it to the frontend:**
   - On the Connect page, paste your API Key in the **"Qlik API Key"** field
   - Then click Connect
   - The API Key will be stored in your browser's session

3. **Now when you select an app:**
   - The LoadScript will automatically fetch and display
   - The system will show only the selected table's LoadScript
   - You can convert it to M Query for Power BI

### Option 2: Via Environment Variables (Advanced)

1. **Generate API Key** (same as Option 1):
   - https://c8vlzp3sx6akvnh.in.qlikcloud.com/console
   - Admin → API Keys → Create new
   - Copy the API Key  

2. **Set Environment Variables in your backend:**
   
   **Windows PowerShell:**
   ```powershell
   $env:QLIK_API_KEY = "your_api_key_here"
   $env:QLIK_TENANT_URL = "https://c8vlzp3sx6akvnh.in.qlikcloud.com"
   ```
   
   **Or create a `.env` file** in the backend directory:
   ```
   QLIK_API_KEY=your_api_key_here
   QLIK_TENANT_URL=https://c8vlzp3sx6akvnh.in.qlikcloud.com
   ```

3. **Restart the backend:**
   ```powershell
   cd d:\qlik_project_tamil\qlik\QlikSense\qlik_app\qlik\qlik-fastapi-backend
   python -m uvicorn main:app --reload
   ```

## Getting Your API Key

1. Go to https://c8vlzp3sx6akvnh.in.qlikcloud.com/console
2. Log in with your Qlik Cloud credentials
3. Click **Admin** (top left)
4. Click **API Keys** (left sidebar)
5. Click **Create new**
6. Set a name like "LoadScript Fetcher"
7. Select these scopes:
   - ✅ apps:read
   - ✅ apps:read_script (IMPORTANT for LoadScript)
   - ✅ data:read
8. Click **Create**
9. Copy the key (you only see it once!)

## Testing

After providing your API Key:

1. Refresh the browser
2. Go to the Discovery page
3. Click on any app
4. Select a table
5. You should see the LoadScript load automatically
6. Click "Convert to M Query" to generate Power BI M code

## Troubleshooting

**Error: "No LoadScript found for table"**
- Make sure your API Key has the `apps:read_script` scope
- The table name must exactly match the one in your Qlik LoadScript

**Error: "API Key not valid"**
- Generate a new API Key from the Qlik Cloud console
- The key may have expired

**Still getting errors?**
- Check the browser's developer console (F12) for more details
- Check the backend logs for error messages
