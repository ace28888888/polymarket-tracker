import streamlit as st
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Celebrity Prediction Market Tracker",
    page_icon="🎯",
    layout="wide"
)

# Initialize session state
if 'signals' not in st.session_state:
    st.session_state.signals = []
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# ===== DATA =====
CELEBRITY_TARGETS = {
    "Elon Musk": {"handle": "@elonmusk", "category": "Tech CEO", "followers": "180M", "reliability": 10, "status": "active", "win_rate": 0.85},
    "Donald Trump": {"handle": "@realDonaldTrump", "category": "Politics", "followers": "87M", "reliability": 9, "status": "hot", "win_rate": 0.82},
    "Andrew Tate": {"handle": "@Cobratate", "category": "Influencer", "followers": "9M", "reliability": 9, "status": "hot", "win_rate": 0.79},
    "KSI": {"handle": "@KSI", "category": "Creator/Boxer", "followers": "12M", "reliability": 9, "status": "active", "win_rate": 0.84},
    "Jake Paul": {"handle": "@jakepaul", "category": "Boxer/Creator", "followers": "20M", "reliability": 8, "status": "watching", "win_rate": 0.73},
    "MrBeast": {"handle": "@MrBeast", "category": "Creator", "followers": "300M", "reliability": 8, "status": "active", "win_rate": 0.81},
    "Kim Kardashian": {"handle": "@KimKardashian", "category": "Celebrity", "followers": "360M", "reliability": 7, "status": "watching", "win_rate": 0.68},
    "Kanye West": {"handle": "@kanyewest", "category": "Music", "followers": "32M", "reliability": 8, "status": "hot", "win_rate": 0.71}
}

MARKETS = [
    {"title": "Will Elon tweet about Dogecoin this week?", "target": "Elon Musk", "platform": "Polymarket", "volume": 145000, "yes": 0.72, "score": 8.5, "signal": True},
    {"title": "Will Trump mention election fraud in next speech?", "target": "Donald Trump", "platform": "Polymarket", "volume": 89000, "yes": 0.81, "score": 9.2, "signal": True},
    {"title": "Will Tate be banned from X in January?", "target": "Andrew Tate", "platform": "Kalshi", "volume": 45000, "yes": 0.34, "score": 7.8, "signal": True},
    {"title": "Will KSI announce boxing opponent by Feb 1?", "target": "KSI", "platform": "Polymarket", "volume": 67000, "yes": 0.58, "score": 7.5, "signal": False},
    {"title": "Will MrBeast reach 300M subs by March?", "target": "MrBeast", "platform": "Polymarket", "volume": 120000, "yes": 0.89, "score": 8.1, "signal": False}
]

# ===== FUNCTIONS =====
def get_emoji(score):
    if score >= 9: return "🔥"
    elif score >= 7: return "⚡"
    elif score >= 5: return "📊"
    else: return "💤"

def calc_position(confidence, bankroll):
    return (bankroll * 0.02) * (confidence / 10)

# ===== SIDEBAR =====
with st.sidebar:
    st.header("🎯 Settings")
    bankroll = st.number_input("Bankroll ($)", 1000, 1000000, 10000, 1000)
    threshold = st.slider("Alert Threshold", 5.0, 10.0, 7.0, 0.5)
    st.divider()
    st.subheader("📡 APIs")
    st.checkbox("Twitter/X", value=False)
    st.checkbox("Polymarket", value=True)
    st.checkbox("Kalshi", value=True)

# ===== HEADER =====
st.title("🎯 Celebrity Prediction Market Tracker")
st.caption("Find asymmetric opportunities before the market catches on")
st.divider()

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Signals", "3", "+1 today")
col2.metric("High Confidence (>8)", "2", "🔥 Hot")
col3.metric("Markets Available", "5", "2 match signals")
col4.metric("Est. Edge", "15-25%", "vs. retail")
st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["🔥 Live Signals", "📊 Markets", "🎯 Targets"])

# ===== TAB 1: SIGNALS =====
with tab1:
    st.subheader("High-Priority Signals")
    
    signals = [
        {"time": "14:32", "target": "Donald Trump", "platform": "Truth Social",
         "text": "WITCH HUNT CONTINUES! THEY WON'T STOP UNTIL THEY DESTROY AMERICA! BIG NEWS COMING...",
         "score": 9.2, "timeframe": "24-48h", "market_ready": True},
        {"time": "09:15", "target": "Andrew Tate", "platform": "X",
         "text": "The Matrix is closing in. They fear the truth. Soon everyone will see.",
         "score": 8.5, "timeframe": "24-72h", "market_ready": True},
        {"time": "22:45", "target": "Kanye West", "platform": "X",
         "text": "...", "score": 6.8, "timeframe": "12-24h", "market_ready": False}
    ]
    
    for sig in signals:
        if sig["score"] >= threshold:
            with st.container():
                c1, c2, c3 = st.columns([1, 3, 1])
                with c1:
                    st.markdown(f"## {get_emoji(sig['score'])}")
                    st.markdown(f"**{sig['score']}/10**")
                with c2:
                    st.markdown(f"**{sig['target']}** - {sig['platform']} at {sig['time']}")
                    st.markdown(f"_{sig['text'][:60]}..._ ⏱️ **{sig['timeframe']}**")
                with c3:
                    pos = calc_position(sig['score'], bankroll)
                    st.markdown(f"**${pos:,.0f}**")
                    if sig["market_ready"]:
                        st.success("Market Live")
                    else:
                        st.info("Wait")
                st.divider()

# ===== TAB 2: MARKETS =====
with tab2:
    st.subheader("Active Markets")
    for m in MARKETS:
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            st.markdown(f"**{m['title']}**")
            st.caption(f"{m['target']} | {m['platform']}")
        with c2:
            st.metric("Volume", f"${m['volume']:,}")
        with c3:
            st.metric("Yes %", f"{m['yes']:.0%}")
        with c4:
            st.metric("Score", f"{m['score']}/10")
            if m['signal']:
                st.success("🔥 Signal")
        st.divider()

# ===== TAB 3: TARGETS =====
with tab3:
    st.subheader("Celebrity Database")
    
    cols = st.columns(4)
    for i, (name, data) in enumerate(CELEBRITY_TARGETS.items()):
        with cols[i % 4]:
            status_color = "🟢" if data['status'] == 'active' else "🔴" if data['status'] == 'hot' else "⚪"
            st.markdown(f"**{name}** {status_color}")
            st.caption(f"{data['category']} | {data['followers']} followers")
            st.caption(f"Reliability: {data['reliability']}/10 | Win rate: {data['win_rate']:.0%}")
            st.divider()
