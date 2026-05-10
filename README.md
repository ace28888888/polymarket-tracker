# 🎯 Celebrity Prediction Market Tracker

Live dashboard for tracking celebrity behavioral patterns and prediction market opportunities.

![Dashboard Preview](https://img.shields.io/badge/status-live-green)

## Features

- **Real-time signal detection** - Monitors celebrity social media for behavioral triggers
- **Market matching** - Cross-references signals with active prediction markets
- **Position sizing** - Auto-calculates bet sizes based on confidence scores
- **8 high-value targets** - Musk, Trump, Tate, KSI, Jake Paul, MrBeast, Kim K, Kanye

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Fork this repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select this repo, file: `app.py`
5. Deploy!

## Live Demo

Coming soon...

## How It Works

The system scores behavioral signals 1-10 based on:
- Pattern matching (cryptic tweets, emotional posts, etc.)
- Author-specific patterns (Musk+Doge = high probability)
- Timing (3am posts = drama incoming)
- Historical accuracy

Signals scoring 8+ trigger market alerts.

## API Integrations

- Twitter/X API - Signal detection
- Polymarket API - Market data
- Kalshi API - Alternative markets

## License

MIT
