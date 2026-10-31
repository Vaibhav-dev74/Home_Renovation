# 🚀 Deployment Guide — AI Home Renovation Intelligence Platform

This repository is fully configured for production deployment across all major cloud providers and container platforms.

---

## ⚡ Option 1: Render (Recommended — Free & Easiest)

Render provides free hosting with native Python and FastAPI support directly from your GitHub repository.

### Step-by-Step Instructions:
1. Push your code to GitHub (already synced to `https://github.com/Vaibhav-dev74/Home_Renovation.git`).
2. Go to **[Render.com](https://render.com/)** and sign in with GitHub.
3. Click **"New +"** $\to$ **"Web Service"**.
4. Select your repository: **`Vaibhav-dev74/Home_Renovation`**.
5. Configure the service:
   - **Name**: `ai-home-renovation` (or your preferred name)
   - **Region**: Choose the closest region (e.g. Singapore, Frankfurt, Oregon)
   - **Branch**: `main`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn web_app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
6. Add Environment Variable:
   - Click **"Advanced"** $\to$ **"Add Environment Variable"**.
   - **Key**: `GOOGLE_API_KEY`
   - **Value**: `AIzaSy...` (your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey))
   - *(Optional)* **Key**: `PYTHON_VERSION`, **Value**: `3.11.9`
7. Click **"Create Web Service"**.
8. Render will build and launch your application. Your public URL will be ready at:
   `https://ai-home-renovation.onrender.com`

---

## 🚂 Option 2: Railway

Railway offers automatic container detection from the included `Dockerfile` or `Procfile`.

### Step-by-Step Instructions:
1. Go to **[Railway.app](https://railway.app/)** and sign in with GitHub.
2. Click **"New Project"** $\to$ **"Deploy from GitHub repo"**.
3. Select **`Vaibhav-dev74/Home_Renovation`**.
4. Click **"Variables"** and add:
   - `GOOGLE_API_KEY`: Your Gemini API key.
5. In **"Settings"**, ensure **Networking** has a public domain generated (click **"Generate Domain"**).
6. Railway builds and deploys your app automatically.

---

## ☁️ Option 3: Google Cloud Run (Serverless Container)

Because this platform leverages Google Gemini and Google ADK, Google Cloud Run offers best-in-class low latency and a generous free tier.

### Prerequisites:
- `gcloud` CLI installed and authenticated (`gcloud auth login`).
- Google Cloud project with Cloud Run and Artifact Registry APIs enabled.

### Deployment Commands:
```bash
# 1. Set your GCP project
gcloud config set project YOUR_GCP_PROJECT_ID

# 2. Build and deploy directly from source
gcloud run deploy ai-home-renovation \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY="YOUR_GEMINI_API_KEY" \
  --memory 1Gi \
  --cpu 1
```

Once finished, Cloud Run outputs your production HTTPS URL (e.g., `https://ai-home-renovation-xyz.run.app`).

---

## 🐳 Option 4: Docker (Local / VPS / AWS EC2 / DigitalOcean)

You can run the production container anywhere with Docker installed:

### Build & Run:
```bash
# 1. Build Docker image
docker build -t ai-home-renovation .

# 2. Run container
docker run -d \
  --name renovation-studio \
  -p 8000:8000 \
  -e GOOGLE_API_KEY="YOUR_GEMINI_API_KEY" \
  --restart unless-stopped \
  ai-home-renovation
```

Your service will be accessible at `http://localhost:8000` or `http://your-server-ip:8000`.

---

## 🤗 Option 5: Hugging Face Spaces (Free AI Showcase)

1. Go to **[Hugging Face Spaces](https://huggingface.co/spaces)** and click **"Create new Space"**.
2. Select **Docker** as Space SDK (Blank).
3. Connect your GitHub repository or push this repository to the Space remote.
4. Go to **Settings** $\to$ **Variables and secrets** and add `GOOGLE_API_KEY` under **Repository Secrets**.
5. Hugging Face builds and hosts your app with an embeddable public URL.

---

## 🛡️ Health Check & Verification

Once deployed, verify your service status:
```bash
curl https://your-deployed-domain.com/api/health
```
Expected response:
```json
{
  "status": "healthy",
  "version": "2.5.0",
  "architecture": "Google ADK Multi-Agent + Gemini Multimodal",
  "database": "connected",
  "gemini_api_configured": true
}
```
