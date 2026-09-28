# CEPA Cloud Deployment Guide (Vercel + Render)

This guide walks you through deploying the **CEPA AI Onion Grader** system live to the cloud so anyone (judges, evaluators, farmers, mandis) can access the system from anywhere in the world.

---

## Architecture Overview

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│       Frontend (Vercel)         │       │        Backend (Render)         │
│  - Expo / React Native Web SPA  │ ────> │  - Python 3.11 FastAPI          │
│  - Instant Global CDN           │ REST  │  - PyTorch CPU + YOLO11n-seg    │
│  - Camera & Mobile Web Upload   │       │  - MobileNetV3 Defect Classifier│
│  - Mandi Dashboard & HUD        │       │  - SQLite Database & Static Host│
└─────────────────────────────────┘       └─────────────────────────────────┘
```

> [!TIP]
> **Why Vercel for Frontend and Render for Backend?**  
> Vercel is designed for ultra-fast static web applications and edge delivery, but has a 250MB limit on serverless functions. PyTorch, YOLO11, and OpenCV require ~1.2GB of libraries, making **Render** (or Railway / Hugging Face Spaces) the ideal home for the continuous AI/CV backend container.

---

## Part 1: Deploy Backend to Render (5 Minutes)

### Method A: 1-Click Render Blueprint (Recommended)
1. Fork or push your `Cepa` repository to your GitHub account (`https://github.com/notUbaid/Cepa`).
2. Log in to [Render](https://render.com).
3. Click **New +** $\to$ **Blueprint**.
4. Connect your GitHub repository `Cepa`.
5. Render will automatically detect [`render.yaml`](file:///C:/Projects/Cepa/render.yaml) and configure the Docker web service.
6. Click **Apply**.
7. Once deployed, Render will provide your public backend URL, for example:  
   `https://cepa-backend.onrender.com`

### Method B: Manual Web Service on Render
1. Go to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** $\to$ **Web Service**.
3. Choose **Build and deploy from a Git repository**.
4. Select your `Cepa` repository.
5. In the service settings:
   - **Name**: `cepa-backend`
   - **Region**: Oregon (US West) or Frankfurt (EU)
   - **Language**: `Docker`
   - **Dockerfile Path**: `./backend/Dockerfile`
   - **Docker Build Context**: `./backend`
   - **Instance Type**: Free (or Starter for 24/7 non-sleeping)
6. Add Environment Variables:
   - `BACKEND_ENV`: `production`
   - `PORT`: `8000`
   - `ACTIVE_GRADING_POLICY`: `DEMO_ASSUMPTION_v1`
   - `CORS_ORIGINS`: `http://localhost:8081,https://*.vercel.app,http://localhost:3000`
   - `GROQ_API_KEY`: *(Optional) Your Groq API key for Multimodal LLM Agronomist*
7. Click **Create Web Service**.

> [!NOTE]
> On the Render Free Tier, services spin down after 15 minutes of inactivity and take 30–50 seconds to wake up on the first request. The endpoint `GET /api/v1/health` can be pinged to wake it up.

---

## Part 2: Deploy Frontend to Vercel (2 Minutes)

1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** $\to$ **Project**.
3. Import your GitHub repository `Cepa`.
4. In the Project Configuration:
   - **Framework Preset**: `Other`
   - **Root Directory**: `mobile` (Click Edit and select the `mobile` folder)
   - **Build Command**: `npx expo export --platform web`
   - **Output Directory**: `dist`
5. Open **Environment Variables** and add:
   - **Key**: `EXPO_PUBLIC_API_URL`
   - **Value**: Your Render Backend URL (e.g., `https://cepa-backend.onrender.com`)
6. Click **Deploy**.
7. In ~60 seconds, Vercel will give you a live production URL:  
   `https://cepa-mobile.vercel.app`

---

## Part 3: Verify Your Cloud Deployment

Once both services are running:

1. **Verify Backend Health**:
   Open in your browser:
   ```
   https://<your-render-app>.onrender.com/api/v1/health
   ```
   Expected response:
   ```json
   {"status":"ok","service":"cepa-backend","version":"0.1.0"}
   ```

2. **Verify CV Models**:
   Open:
   ```
   https://<your-render-app>.onrender.com/api/v1/health/cv
   ```
   Expected response:
   ```json
   {
     "status": "ready",
     "seg_provider": "yolo11-seg:yolo11n-seg:8.4.157",
     "defect_classifier": "defect-classifier:defect_classifier",
     "seg_is_mock": false,
     "defect_is_mock": false
   }
   ```

3. **Verify Frontend Experience**:
   Open your Vercel URL (`https://<your-app>.vercel.app`) on your phone or desktop:
   - Tap **"Load Verified Mandi Demo Lot"** $\to$ Instantly runs the authentic 24-bulb inspection with full grading, storageability index, and eNAM compliance.
   - Upload any real onion spread image or capture with your smartphone camera.
   - Tap **"Export PDF"** to download the official eNAM Mandi Assaying Certificate.

---

## Alternative: Free 16GB GPU/CPU on Hugging Face Spaces

If you prefer a free persistent server with 16GB RAM and no sleep timeout:
1. Create a **New Space** on [Hugging Face](https://huggingface.co/spaces).
2. Select **Docker** SDK (Blank).
3. Connect your GitHub repository.
4. Set Dockerfile path to `backend/Dockerfile`.
5. Hugging Face Spaces provides free, high-spec compute without cold start delays.
