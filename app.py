import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(
    page_title="Polymarket Tracker",
    page_icon="🎯",
    layout="wide"
)

# ===== SESSION STATE =====
if 'signals' not in st.session_state:
    st.session_state.signals = []
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# ===== API =====
@st.cache_data(ttl=60)
def get_polymarket_markets(limit=50, min_liquidity=1000):
    """Fetch live markets from Polymarket Gamma API (free, no key)"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "liquidityNumMin": min_liquidity,
        "limit": limit,
        "sort": "volume24hr",
        "ascending": "false"
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        # Handle both list and dict with markets key
        if isinstance(data, dict):
            markets = data.get("markets", data.get("data", []))
        else:
            markets = data
        return markets if isinstance(markets, list) else []
    except Exception as e:
        st.error(f"Polymarket API error: {e}")
        return []

@st.cache_data(ttl=60)
def get_market_orderbook(market_id):
    """Fetch orderbook for a specific market"""
    url = f"https://gamma-api.polymarket.com/markets/{market_id}/orderbook"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return {}

def parse_market(m):
    """Normalize Polymarket market data"""
    outcomes = m.get("outcomes", "Yes,No").split(",")
    prices = m.get("outcomePrices", "0.5,0.5")
    try:
        prices_list = [float(p) for p in prices.strip("[]").split(",")]
    except:
        prices_list = [0.5, 0.5]

    yes_price = prices_list[0] if len(prices_list) > 0 else 0.5
    volume = m.get("volume24hr", m.get("volume", 0))
    if isinstance(volume, str):
        try:
            volume = float(volume)
        except:
            volume = 0
    liquidity = m.get("liquidity", m.get("liquidityNum", 0))
    if isinstance(liquidity, str):
        try:
            liquidity = float(liquidity)
        except:
            liquidity = 0

    return {
        "id": m.get("conditionId", m.get("id", "")),
        "slug": m.get("slug", ""),
        "title": m.get("question", m.get("title", "Unknown Market")),
        "category": m.get("category", "General"),
        "yes_price": yes_price,
        "no_price": 1 - yes_price,
        "volume_24h": volume,
        "liquidity": liquidity,
        "end_date": m.get("resolutionTime", m.get("endDate", "N/A")),
        "volume_total": m.get("volume", volume),
        "spread": abs(prices_list[0] - prices_list[1]) if len(prices_list) > 1 else 0,
    }

# ===== SIDEBAR =====
with st.sidebar:
    st.header("🎯 Settings")
    bankroll = st.number_input("Bankroll ($)", 1000, 10000000, 10000, 1000)
    threshold = st.slider("Alert Threshold (score)", 5.0, 10.0, 7.0, 0.5)
    min_volume = st.number_input("Min Volume 24h ($)", 1000, 10000000, 10000, 1000)
    st.divider()
    st.subheader("📡 Data Sources")
    st.checkbox("Polymarket (LIVE)", value=True, disabled=True)
    st.checkbox("Kalshi", value=False, disabled=True)
    st.caption("Polymarket = free reads, no API key")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ===== HEADER =====
st.title("🎯 Polymarket Live Tracker")
st.caption("Real prediction markets. Real edge. Updated every 60s.")
st.divider()

# ===== FETCH DATA =====
with st.spinner("Pulling live Polymarket data..."):
    raw_markets = get_polymarket_markets(limit=100, min_liquidity=1000)
    markets = [parse_market(m) for m in raw_markets]
    # Filter by min volume
    markets = [m for m in markets if m["volume_24h"] >= min_volume]

if not markets:
    st.warning("No markets loaded. Polymarket API may be rate-limited. Click Refresh to retry.")
    st.stop()

# ===== KPIs =====
total_vol = sum(m["volume_24h"] for m in markets)
high_conf = len([m for m in markets if m["yes_price"] > 0.7 or m["yes_price"] < 0.3])
avg_price = sum(m["yes_price"] for m in markets) / len(markets) if markets else 0.5

k1, k2, k3, k4 = st.columns(4)
k1.metric("Markets Tracked", len(markets))
k2.metric("24h Volume", f"${total_vol:,.0f}")
k3.metric("High Confidence", high_conf, delta=">70% or <30%")
k4.metric("Avg Yes Price", f"{avg_price:.1%}")
st.divider()

# ===== TABS =====
tab1, tab2, tab3 = st.tabs(["🔥 Live Markets", "📊 Opportunities", "🎯 Targets"])

# ===== TAB 1: LIVE MARKETS =====
with tab1:
    st.subheader("Active Polymarket Markets")
    search = st.text_input("Filter markets...", placeholder="e.g. trump, election, elon...")
    
    df = pd.DataFrame(markets)
    if search:
        df = df[df["title"].str.lower().str.contains(search.lower(), na=False)]
    
    # Sort by volume
    df = df.sort_values("volume_24h", ascending=False)
    
    for _, m in df.head(20).iterrows():
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1:
            st.markdown(f"**{m['title']}**")
            st.caption(f"{m['category']} | Ends: {str(m['end_date'])[:10]}")
        with c2:
            st.metric("Yes", f"{m['yes_price']:.1%}")
        with c3:
            st.metric("24h Vol", f"${m['volume_24h']:,.0f}")
        with c4:
            # Edge score = inverse of confidence (lower confidence = higher edge if you have info)
            edge = 10 - abs(m['yes_price'] - 0.5) * 10
            st.metric("Edge", f"{edge:.1f}")
            if edge >= threshold:
                st.success("🔥 Signal")
            elif m['volume_24h'] > 100000:
                st.info("📈 Volume")
        st.divider()

# ===== TAB 2: OPPORTUNITIES =====
with tab2:
    st.subheader("Asymmetric Opportunities")
    st.caption("Markets with high volume but uncertain pricing (edge > 7)")
    
    opportunities = [m for m in markets if (10 - abs(m["yes_price"] - 0.5) * 10) >= threshold and m["volume_24h"] > 50000]
    opportunities.sort(key=lambda x: x["volume_24h"], reverse=True)
    
    if not opportunities:
        st.info("No high-edge opportunities right now. Lower the threshold or check back later.")
    
    for m in opportunities[:10]:
        edge = 10 - abs(m["yes_price"] - 0.5) * 10
        pos = (bankroll * 0.02) * (edge / 10)
        
        with st.container():
            c1, c2, c3 = st.columns([1, 3, 1])
            with c1:
                emoji = "🔥" if edge >= 9 else "⚡" if edge >= 7 else "📊"
                st.markdown(f"## {emoji}")
                st.markdown(f"**{edge:.1f}/10**")
            with c2:
                st.markdown(f"**{m['title']}**")
                st.caption(f"Yes: {m['yes_price']:.1%} | Vol: ${m['volume_24h']:,.0f} | Liq: ${m['liquidity']:,.0f}")
            with c3:
                st.markdown(f"**${pos:,.0f}** suggested")
                st.markdown(f"[View on Polymarket](https://polymarket.com/event/{m['slug']})")
            st.divider()

# ===== TAB 3: TARGETS =====
with tab3:
    st.subheader("Celebrity & Political Targets")
    
    # Keywords to track
    TARGETS = {
        "Trump": ["trump", "donald trump", "realDonaldTrump"],
        "Elon": ["elon", "musk", "tesla", "spacex", "dogecoin"],
        "Biden": ["biden", "joe biden"],
        "Crypto": ["bitcoin", "ethereum", "btc", "eth", "crypto"],
        "Election 2024": ["election", "president", "vote"],
        "Sports": ["super bowl", "world cup", "olympics", "nba"],
    }
    
    for target_name, keywords in TARGETS.items():
        matches = [m for m in markets if any(kw in m["title"].lower() for kw in keywords)]
        matches.sort(key=lambda x: x["volume_24h"], reverse=True)
        
        if matches:
            with st.expander(f"🎯 {target_name} — {len(matches)} markets"):
                for m in matches[:5]:
                    edge = 10 - abs(m["yes_price"] - 0.5) * 10
                    st.markdown(f"**{m['title']}** — Yes: {m['yes_price']:.1%} | Vol: ${m['volume_24h']:,.0f} | Edge: {edge:.1f}")
                    st.caption(f"[Trade now](https://polymarket.com/event/{m['slug']})")
        else:
            st.caption(f"🎯 {target_name} — no active markets")

# ===== FOOTER =====
st.divider()
st.caption(f"Last refreshed: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S UTC')} | Data: Polymarket Gamma API")
