# MyBrain Deployment Guide

## Architecture Overview

MyBrain consists of three main components:
1. **Frontend**: Next.js app (can be hosted on Netlify)
2. **Backend**: Python FastAPI server (needs separate hosting)
3. **Database**: Supabase (already cloud-hosted)

## Deployment Options

### Option 1: Netlify (Frontend) + Railway/Render (Backend)

#### Frontend on Netlify:
1. Connect GitHub repository to Netlify
2. Set environment variables from `.env.netlify`
3. Deploy will happen automatically on push

#### Backend Options:

**Railway (Recommended)**:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and initialize
railway login
railway init

# Deploy
railway up
```

**Render**:
- Create new Web Service
- Connect GitHub repo
- Set root directory to `/backend`
- Add environment variables

**Fly.io**:
```bash
fly launch --path backend
fly secrets set OPENAI_API_KEY=xxx ANTHROPIC_API_KEY=xxx
fly deploy
```

### Option 2: Vercel (Full Stack)

Since you already have a `vercel.json`, you could use Vercel instead:

1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` in project root
3. Set environment variables in Vercel dashboard

### Option 3: Self-Hosted (VPS)

Deploy both frontend and backend on a VPS (DigitalOcean, Linode, etc.):

```bash
# On your VPS
git clone https://github.com/quualle/mybrain.git
cd mybrain

# Setup frontend
npm install
npm run build

# Setup backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Use PM2 for process management
npm install -g pm2
pm2 start "npm start" --name mybrain-frontend
pm2 start "uvicorn main:app" --name mybrain-backend --cwd backend
```

## Required Environment Variables

### Frontend (.env.local):
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=
```

### Backend (.env):
```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DATABASE_URL=
SUPABASE_URL=
SUPABASE_KEY=
```

## Important Considerations

1. **CORS**: Backend needs to allow frontend domain
2. **API URL**: Frontend needs to know backend URL
3. **Security**: Never expose API keys in frontend code
4. **Scaling**: Consider using connection pooling for database

## Netlify-Specific Issues

Since Netlify only hosts static sites and serverless functions:
- The Python backend CANNOT run on Netlify
- You need a separate backend hosting solution
- API calls need to be proxied to the backend URL

## Recommended Architecture for Netlify

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   Netlify   │────▶│Backend Host  │────▶│  Supabase  │
│  (Frontend) │     │  (Railway)   │     │ (Database) │
└─────────────┘     └──────────────┘     └────────────┘
```

## Next Steps

1. Deploy backend to Railway/Render/Fly.io
2. Get the backend URL
3. Update `.env.netlify` with correct URLs
4. Deploy frontend to Netlify
5. Test the connection