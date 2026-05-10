# 🚀 Celebrity Tracker Dashboard - Deployment Guide

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run locally
streamlit run app.py

# 3. Open browser
# http://localhost:8501
```

## Deploy to Streamlit Cloud (FREE - RECOMMENDED)

Streamlit Cloud is the best option - it's free, handles all backend code, and requires zero server management.

### Step 1: Push to GitHub
```bash
# Create new repo
git init
git add .
git commit -m "Initial dashboard"

# Create GitHub repo (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/celebrity-tracker.git
git push -u origin main
```

### Step 2: Deploy
1. Go to https://streamlit.io/cloud
2. Sign in with GitHub
3. Click "New app"
4. Select your repo
5. Main file path: `app.py`
6. Click Deploy

### Step 3: Add Secrets (API Keys)
1. In Streamlit Cloud, go to your app → Settings → Secrets
2. Add your API keys:

```toml
[twitter]
bearer_token = "your_twitter_bearer_token"

[polymarket]
api_key = "your_polymarket_key"

[kalshi]
api_key = "your_kalshi_key"
```

**That's it!** App auto-deploys on every git push. Free tier includes:
- 1 GB RAM
- Unlimited public apps
- Custom domains
- Secrets management

---

## Alternative: Netlify (More Complex)

Netlify is primarily for static sites. To run Python backend code, you need:

### Option A: Netlify Functions (Limited)
- Convert Python logic to JavaScript
- Use serverless functions for API calls
- More dev work, not recommended

### Option B: Netlify + Streamlit Hybrid
- Deploy frontend to Netlify
- Run Streamlit backend separately
- Overkill for this use case

**Verdict:** Skip Netlify. Use Streamlit Cloud.

---

## Alternative: Self-Host (VPS/Server)

If you want full control, deploy to your own server.

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
# Build and run
docker build -t celebrity-tracker .
docker run -p 8501:8501 celebrity-tracker
```

### Docker Compose (with auto-restart)

```yaml
# docker-compose.yml
version: '3.8'
services:
  tracker:
    build: .
    ports:
      - "8501:8501"
    environment:
      - TWITTER_BEARER_TOKEN=${TWITTER_BEARER_TOKEN}
    restart: unless-stopped
```

---

## Feature Roadmap

### Phase 1: Basic (Current)
- ✅ Celebrity database
- ✅ Manual signal scoring
- ✅ Market list
- ✅ Position sizing calculator

### Phase 2: Live Data (Next)
- [ ] Twitter API integration
- [ ] Polymarket price feeds
- [ ] Auto signal detection
- [ ] Real-time alerts

### Phase 3: Advanced
- [ ] Pattern recognition ML
- [ ] Backtesting engine
- [ ] Multi-market arbitrage
- [ ] Telegram/Discord bot alerts

---

## API Integration Checklist

### Twitter API Setup
1. Apply at https://developer.twitter.com
2. Create app, get Bearer Token
3. Add to Streamlit secrets
4. Uncomment API calls in `app.py`

### Polymarket API
1. Docs: https://docs.polymarket.com/
2. No auth required for public data
3. Endpoints:
   - `GET /markets` - list all
   - `GET /events` - events with markets

### Kalshi API
1. Create account at https://kalshi.com
2. Generate API key in settings
3. Add to secrets

---

## Cost Summary

| Service | Monthly Cost | Why |
|---------|--------------|-----|
| Streamlit Cloud | **FREE** | Built-in hosting |
| Twitter API Basic | $100 | Essential for signals |
| YouTube API | $5 | Low quota usage |
| Reddit API | FREE | 100 req/min |
| Polymarket | FREE | Public data |
| Kalshi | FREE | Public data |
| **TOTAL** | **~$105/mo** | |

---

## Support

- Streamlit docs: https://docs.streamlit.io/
- Deploy issues: Check Streamlit Cloud logs
- API issues: Test with curl first
