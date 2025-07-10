# MyBrain Deployment Guide

## Prerequisites
- GitHub repository: https://github.com/quualle/mybrain
- Supabase project with database URL and anon key
- OpenAI API key
- Anthropic API key (optional)

## Backend Deployment on Render.com

### 1. Create Render Account
Go to https://render.com and sign up/login

### 2. Create New Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub account if not already connected
3. Select the `quualle/mybrain` repository
4. Configure the service:
   - **Name**: mybrain-backend
   - **Root Directory**: Leave blank (uses repository root)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements-minimal.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. Set Environment Variables
Add these environment variables in Render dashboard:
```
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key (optional)
DATABASE_URL=your_supabase_database_url
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### 4. Deploy
Click "Create Web Service". Render will automatically deploy your backend.

Your backend URL will be: `https://mybrain-backend.onrender.com`

## Frontend Deployment on Railway

### 1. Create Railway Account
Go to https://railway.app and sign up/login

### 2. Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Connect your GitHub account if needed
4. Select the `quualle/mybrain` repository

### 3. Configure Service
1. Railway will auto-detect the Next.js app
2. Set the following environment variables:
   ```
   NEXT_PUBLIC_BACKEND_URL=https://mybrain-backend.onrender.com
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

### 4. Deploy
Railway will automatically build and deploy your frontend.

Your frontend URL will be provided by Railway (e.g., `https://mybrain.up.railway.app`)

## Post-Deployment Steps

### 1. Update CORS Settings
Once you have your Railway frontend URL, update the backend CORS settings:

1. Go to Render dashboard
2. Add an environment variable:
   ```
   FRONTEND_URL=https://your-app.up.railway.app
   ```

### 2. Test the Deployment
1. Visit your Railway frontend URL
2. Try ingesting a document
3. Test the chat functionality

### 3. Set up Custom Domain (Optional)
Both Render and Railway support custom domains:
- Render: Settings → Custom Domains
- Railway: Settings → Domains

## Monitoring and Logs

### Render
- View logs: Dashboard → Your Service → Logs
- Monitor metrics: Dashboard → Your Service → Metrics

### Railway
- View logs: Project → Service → Logs
- Monitor usage: Project → Usage

## Troubleshooting

### Backend Issues
1. Check Render logs for errors
2. Verify all environment variables are set
3. Ensure database migrations have run

### Frontend Issues
1. Check Railway logs
2. Verify NEXT_PUBLIC_BACKEND_URL is correct
3. Check browser console for errors

### Common Issues
- **CORS errors**: Update backend CORS settings with frontend URL
- **Database connection**: Verify DATABASE_URL format
- **API timeouts**: Render free tier may sleep after inactivity