import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import json

st.set_page_config(
    page_title="Polymarket Tracker — Trump & Elon Alpha",
    page_icon="🎯",
    layout="wide"
)

# ===== SESSION STATE =====
if 'signals' not in st.session_state:
    st.session_state.signals = []
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# ===== API ENDPOINTS =====
GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

# ===== PERSONALITY PROFILES =====
PERSONALITIES = {
    "Trump": {
        "western": "♊ Gemini",
        "chinese": "🐕 Dog (1946)",
        "numerology": "🔢 Life Path 4 (Builder/Leader)",
        "traits": "Volatile communicator, thrives on attention, unpredictable decisions, pattern of bold claims",
        "speak_patterns": "ALL CAPS when emotional, uses nicknames, declares victory early, creates deadlines",
        "market_triggers": ["indictment", "debate", "poll numbers", "court", "fraud", "election", "rally"],
        "hot_hours": "06:00-09:00 UTC (early morning tweets)",
    },
    "Elon": {
        "western": "♋ Cancer",
        "chinese": "🐖 Pig/Boar (1971)",
        "numerology": "🔢 Life Path 7 (Seeker/Thinker)",
        "traits": "Meme-driven, reactive to criticism, sudden pivots, uses humor to deflect",
        "speak_patterns": "Memes, 'lol', cryptic one-liners, replies to random accounts, sudden policy changes",
        "market_triggers": ["dogecoin", "tesla", "spacex", "twitter", "x", "ai", "mars", "crypto"],
        "hot_hours": "02:00-06:00 UTC (late night / early US hours)",
    }
}

# ===== FETCH FUNCTIONS =====
@st.cache_data(ttl=120)
def get_gamma_markets(limit=200, min_liquidity=500):
    url = f"{GAMMA_API}/markets"
    params = {
        "active": "true",
        "closed": "false",
        "liquidityNumMin": min_liquidity,
        "limit": limit,
        "sort": "volume24hr",
        "ascending": "false"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return data.get("markets", data.get("data", []))
        return data if isinstance(data, list) else []
    except Exception as e:
        st.sidebar.error(f"Gamma API: {e}")
        return []

@st.cache_data(ttl=300)
def get_market_history(condition_id, start_ts=None, end_ts=None):
    """Fetch price history from Data API"""
    url = f"{DATA_API}/history/markets/{condition_id}"
    params = {}
    if start_ts:
        params["startTs"] = start_ts
    if end_ts:
        params["endTs"] = end_ts
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except:
        return {}

@st.cache_data(ttl=120)
def get_market_orderbook(condition_id):
    url = f"{CLOB_API}/markets/{condition_id}/orderbook"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return {}

# ===== PARSING =====
def parse_market(m):
    outcomes = m.get("outcomes", "Yes,No").split(",")
    prices_raw = m.get("outcomePrices", "0.5,0.5")
    try:
        prices_list = [float(p) for p in prices_raw.strip("[]").split(",")]
    except:
        prices_list = [0.5, 0.5]
    
    yes_price = prices_list[0] if len(prices_list) > 0 else 0.5
    
    volume = m.get("volume24hr", m.get("volume", 0))
    if isinstance(volume, str):
        try: volume = float(volume)
        except: volume = 0
    
    liquidity = m.get("liquidity", m.get("liquidityNum", 0))
    if isinstance(liquidity, str):
        try: liquidity = float(liquidity)
        except: liquidity = 0
    
    vol_total = m.get("volume", volume)
    if isinstance(vol_total, str):
        try: vol_total = float(vol_total)
        except: vol_total = volume
    
    return {
        "condition_id": m.get("conditionId", m.get("id", "")),
        "slug": m.get("slug", ""),
        "title": m.get("question", m.get("title", "Unknown")),
        "category": m.get("category", "General"),
        "yes_price": yes_price,
        "no_price": 1 - yes_price,
        "volume_24h": volume,
        "liquidity": liquidity,
        "volume_total": vol_total,
        "end_date": m.get("resolutionTime", m.get("endDate", "N/A")),
        "spread": abs(prices_list[0] - prices_list[1]) if len(prices_list) > 1 else 0,
    }

def calc_hot_score(m):
    """Hot score = volume velocity + uncertainty + total traction"""
    vol_24h = m["volume_24h"]
    vol_total = m["volume_total"]
    liquidity = m["liquidity"]
    yes_price = m["yes_price"]
    
    # Volume velocity (24h vs total ratio — new money flowing in)
    velocity = (vol_24h / max(vol_total, 1)) * 10  # 0-10 scale
    
    # Uncertainty (0.5 = max uncertainty)
    uncertainty = 1 - abs(yes_price - 0.5) * 2
    
    # Liquidity depth
    liq_score = min(liquidity / 50000, 1.0)
    
    # Raw volume score (markets with $100k+ 24h volume get boost)
    raw_vol = min(vol_24h / 100000, 1.0)
    
    hot_score = (velocity * 3) + (uncertainty * 2.5) + (liq_score * 2) + (raw_vol * 2.5)
    return hot_score

def calc_big_play_score(m):
    """Big play = high liquidity + near 50/50 + decent volume (the best opportunities)"""
    uncertainty = 1 - abs(m["yes_price"] - 0.5) * 2
    liq_score = min(m["liquidity"] / 100000, 1.0)
    vol_score = min(m["volume_24h"] / 50000, 1.0)
    return (uncertainty * 4) + (liq_score * 3) + (vol_score * 3)

def calc_momentum(m):
    """Placeholder for momentum — would need historical comparison"""
    # In future: compare current price vs 7d avg from Data API
    return "N/A"

# ===== SIDEBAR =====
with st.sidebar:
    st.header("🎯 Settings")
    bankroll = st.number_input("Bankroll ($)", 1000, 10000000, 10000, 1000)
    min_volume = st.number_input("Min 24h Volume ($)", 1000, 10000000, 5000, 1000)
    min_liquidity = st.number_input("Min Liquidity ($)", 1000, 10000000, 5000, 1000)
    
    st.divider()
    st.subheader("🔥 Hot Score Threshold")
    hot_threshold = st.slider("Min Hot Score", 3.0, 10.0, 6.0, 0.5)
    big_play_threshold = st.slider("Min Big Play Score", 3.0, 10.0, 6.5, 0.5)
    
    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ===== HEADER =====
st.title("🎯 Polymarket Tracker — Trump & Elon Alpha")
st.caption("Hot markets. Big plays. Personality-driven signal detection.")
st.divider()

# ===== FETCH =====
with st.spinner("Pulling live Polymarket data..."):
    raw = get_gamma_markets(limit=200, min_liquidity=min_liquidity)
    markets = [parse_market(m) for m in raw]
    markets = [m for m in markets if m["volume_24h"] >= min_volume]
    
    for m in markets:
        m["hot_score"] = calc_hot_score(m)
        m["big_play_score"] = calc_big_play_score(m)

if not markets:
    st.warning("No markets loaded. API may be rate-limited. Click Refresh.")
    st.stop()

# ===== KPIs =====
total_vol = sum(m["volume_24h"] for m in markets)
hot_count = len([m for m in markets if m["hot_score"] >= hot_threshold])
big_play_count = len([m for m in markets if m["big_play_score"] >= big_play_threshold])
uncertain_count = len([m for m in markets if 0.4 <= m["yes_price"] <= 0.6])

k1, k2, k3, k4 = st.columns(4)
k1.metric("Markets Tracked", len(markets))
k2.metric("24h Volume", f"${total_vol:,.0f}")
k3.metric("🔥 Hot Markets", hot_count)
k4.metric("⚡ Big Plays", big_play_count, delta=f"{uncertain_count} near 50/50")
st.divider()

# ===== TABS =====
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔥 Hot Markets", "⚡ Big Plays", "🎯 Trump & Elon", "📊 All Markets", "🔮 Profiles"
])

# ===== TAB 1: HOT MARKETS =====
with tab1:
    st.subheader("🔥 Hot Markets Right Now")
    st.caption("Volume velocity + uncertainty + liquidity. New money flowing into uncertain outcomes.")
    
    hot_markets = [m for m in markets if m["hot_score"] >= hot_threshold]
    hot_markets.sort(key=lambda x: x["hot_score"], reverse=True)
    
    if not hot_markets:
        st.info("No hot markets right now. Lower the threshold or check back later.")
    
    for m in hot_markets[:15]:
        pos = (bankroll * 0.02) * (m["hot_score"] / 10)
        velocity = (m["volume_24h"] / max(m["volume_total"], 1)) * 100
        
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            emoji = "🔥🔥" if m["hot_score"] >= 8 else "🔥" if m["hot_score"] >= 6 else "⚡"
            st.markdown(f"## {emoji}")
            st.markdown(f"**{m['hot_score']:.1f}/10**")
        with c2:
            st.markdown(f"**{m['title']}**")
            st.caption(f"Yes: {m['yes_price']:.1%} | 24h Vol: ${m['volume_24h']:,.0f} | Total Vol: ${m['volume_total']:,.0f}")
            st.caption(f"Velocity: {velocity:.1f}% of total volume in 24h | Liquidity: ${m['liquidity']:,.0f}")
        with c3:
            st.markdown(f"**${pos:,.0f}** suggested")
            st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        st.divider()

# ===== TAB 2: BIG PLAYS =====
with tab2:
    st.subheader("⚡ Potential Big Plays")
    st.caption("High liquidity + near 50/50 + volume. These have the most upside if you have an edge.")
    
    big_plays = [m for m in markets if m["big_play_score"] >= big_play_threshold and m["volume_24h"] > 10000]
    big_plays.sort(key=lambda x: x["big_play_score"], reverse=True)
    
    if not big_plays:
        st.info("No big plays right now. Lower threshold or check later.")
    
    for m in big_plays[:15]:
        pos = (bankroll * 0.03) * (m["big_play_score"] / 10)  # slightly higher allocation
        uncertainty = 1 - abs(m["yes_price"] - 0.5) * 2
        
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            emoji = "💰" if m["big_play_score"] >= 8 else "⚡" if m["big_play_score"] >= 6 else "📊"
            st.markdown(f"## {emoji}")
            st.markdown(f"**{m['big_play_score']:.1f}/10**")
        with c2:
            st.markdown(f"**{m['title']}**")
            st.caption(f"Yes: {m['yes_price']:.1%} (Uncertainty: {uncertainty:.0%}) | Vol: ${m['volume_24h']:,.0f} | Liq: ${m['liquidity']:,.0f}")
            st.caption("High uncertainty + deep liquidity = best risk/reward")
        with c3:
            st.markdown(f"**${pos:,.0f}** suggested")
            st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        st.divider()

# ===== TAB 3: TRUMP & ELON =====
with tab3:
    st.subheader("🎯 Trump & Elon Markets")
    st.caption("Markets directly tied to Trump or Elon. Filtered for relevance.")
    
    TRUMP_KEYWORDS = ["trump", "donald trump", "realDonaldTrump", "trump's", "trump indictment", 
                      "trump trial", "trump debate", "trump election", "trump poll", "trump court",
                      "biden", "kamala", "election", "president 2024", "gop primary"]
    ELON_KEYWORDS = ["elon", "musk", "tesla", "spacex", "dogecoin", "doge", "bitcoin", "btc", 
                     "ethereum", "crypto", "twitter", "x.com", "x corp", "neuralink", "mars",
                     "starlink", "boring company"]
    
    trump_markets = [m for m in markets if any(kw in m["title"].lower() for kw in TRUMP_KEYWORDS)]
    elon_markets = [m for m in markets if any(kw in m["title"].lower() for kw in ELON_KEYWORDS)]
    
    trump_markets.sort(key=lambda x: x["hot_score"], reverse=True)
    elon_markets.sort(key=lambda x: x["hot_score"], reverse=True)
    
    col_t, col_e = st.columns(2)
    
    with col_t:
        st.markdown("### 🟥 Trump Markets")
        if trump_markets:
            for m in trump_markets[:8]:
                st.markdown(f"**{m['title']}**")
                st.caption(f"Yes: {m['yes_price']:.1%} | Vol: ${m['volume_24h']:,.0f} | Hot: {m['hot_score']:.1f}")
                st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.caption("No active Trump markets right now")
        
        with st.expander("🔮 Trump Personality Context"):
            p = PERSONALITIES["Trump"]
            st.markdown(f"**{p['western']} | {p['chinese']} | {p['numerology']}**")
            st.markdown(f"*Traits:* {p['traits']}")
            st.markdown(f"*Speak:* {p['speak_patterns']}")
            st.markdown(f"*Hot hours:* {p['hot_hours']}")
            st.markdown("**Key triggers to watch:**")
            for t in p['market_triggers']:
                st.markdown(f"- {t}")
    
    with col_e:
        st.markdown("### 🟦 Elon Markets")
        if elon_markets:
            for m in elon_markets[:8]:
                st.markdown(f"**{m['title']}**")
                st.caption(f"Yes: {m['yes_price']:.1%} | Vol: ${m['volume_24h']:,.0f} | Hot: {m['hot_score']:.1f}")
                st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.caption("No active Elon markets right now")
        
        with st.expander("🔮 Elon Personality Context"):
            p = PERSONALITIES["Elon"]
            st.markdown(f"**{p['western']} | {p['chinese']} | {p['numerology']}**")
            st.markdown(f"*Traits:* {p['traits']}")
            st.markdown(f"*Speak:* {p['speak_patterns']}")
            st.markdown(f"*Hot hours:* {p['hot_hours']}")
            st.markdown("**Key triggers to watch:**")
            for t in p['market_triggers']:
                st.markdown(f"- {t}")
    
    st.divider()
    st.subheader("📈 Combined Signal Dashboard")
    combined = list({m['condition_id']: m for m in trump_markets + elon_markets}.values())
    combined.sort(key=lambda x: x['hot_score'], reverse=True)
    
    if combined:
        for m in combined[:10]:
            is_trump = any(kw in m["title"].lower() for kw in TRUMP_KEYWORDS)
            badge = "🟥 TRUMP" if is_trump else "🟦 ELON"
            st.markdown(f"{badge} **{m['title']}** — Yes: {m['yes_price']:.1%} | Hot: {m['hot_score']:.1f} | [Trade](https://polymarket.com/event/{m['slug']})")

# ===== TAB 4: ALL MARKETS =====
with tab4:
    st.subheader("📊 All Markets")
    search = st.text_input("Search markets...", placeholder="type to filter...")
    
    df = pd.DataFrame(markets)
    if search:
        df = df[df["title"].str.lower().str.contains(search.lower(), na=False)]
    df = df.sort_values("volume_24h", ascending=False)
    
    for _, m in df.head(30).iterrows():
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
        with c1:
            st.markdown(f"**{m['title']}**")
            st.caption(f"Ends: {str(m['end_date'])[:10]}")
        with c2:
            st.metric("Yes", f"{m['yes_price']:.1%}")
        with c3:
            st.metric("24h Vol", f"${m['volume_24h']:,.0f}")
        with c4:
            st.metric("Hot", f"{m['hot_score']:.1f}")
        with c5:
            st.metric("BigPlay", f"{m['big_play_score']:.1f}")
        st.divider()

# ===== TAB 5: PROFILES =====
with tab5:
    st.subheader("🔮 Personality & Communication Profiles")
    st.caption("Understanding how they communicate helps predict market-moving events.")
    
    for name, p in PERSONALITIES.items():
        with st.expander(f"🔮 {name} — {p['western']} | {p['chinese']} | {p['numerology']}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Personality Traits**")
                st.markdown(p['traits'])
                st.markdown("**Communication Patterns**")
                st.markdown(p['speak_patterns'])
            with col2:
                st.markdown("**Market Triggers**")
                for t in p['market_triggers']:
                    st.markdown(f"- {t}")
                st.markdown(f"**Hot Hours:** {p['hot_hours']}")
    
    st.divider()
    st.subheader("📋 Trading Signal Checklist")
    st.markdown("""
    When a market spikes, check:
    1. **Did Trump tweet between 06:00-09:00 UTC?** → Check for ALL CAPS, nicknames, deadline claims
    2. **Did Elon post memes between 02:00-06:00 UTC?** → Check for crypto references, sudden pivots
    3. **Is the market near 50/50 with high liquidity?** → Best risk/reward for directional bets
    4. **Is 24h volume >20% of total volume?** → New money = momentum
    5. **What's the narrative?** → Personality profile helps interpret the 'why'
    """)

# ===== FOOTER =====
st.divider()
st.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Gamma + Data + CLOB APIs | Hot scores update every 2 min")
