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

# ===== API ENDPOINTS =====
GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

# ===== FETCH FUNCTIONS =====
@st.cache_data(ttl=60)
def get_gamma_markets(limit=100, min_liquidity=1000):
    """Fetch market listings from Gamma API (free, no key)"""
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
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return data.get("markets", data.get("data", []))
        return data if isinstance(data, list) else []
    except Exception as e:
        st.sidebar.error(f"Gamma API: {e}")
        return []

@st.cache_data(ttl=60)
def get_market_history(condition_id):
    """Fetch price history from Data API"""
    url = f"{DATA_API}/history/markets/{condition_id}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return {}

@st.cache_data(ttl=60)
def get_market_orderbook(condition_id):
    """Fetch orderbook from CLOB API"""
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
    
    return {
        "condition_id": m.get("conditionId", m.get("id", "")),
        "slug": m.get("slug", ""),
        "title": m.get("question", m.get("title", "Unknown")),
        "category": m.get("category", "General"),
        "yes_price": yes_price,
        "no_price": 1 - yes_price,
        "volume_24h": volume,
        "liquidity": liquidity,
        "end_date": m.get("resolutionTime", m.get("endDate", "N/A")),
        "volume_total": m.get("volume", volume),
        "spread": abs(prices_list[0] - prices_list[1]) if len(prices_list) > 1 else 0,
    }

def calc_edge(m):
    """Edge = uncertainty × liquidity. Higher = better opportunity."""
    price_uncertainty = 1 - abs(m["yes_price"] - 0.5) * 2  # 0 = certain, 1 = 50/50
    liquidity_score = min(m["liquidity"] / 50000, 1.0)  # cap at $50k
    volume_score = min(m["volume_24h"] / 100000, 1.0)  # cap at $100k vol
    return (price_uncertainty * 5) + (liquidity_score * 3) + (volume_score * 2)

# ===== SIDEBAR =====
with st.sidebar:
    st.header("🎯 Settings")
    bankroll = st.number_input("Bankroll ($)", 1000, 10000000, 10000, 1000)
    min_volume = st.number_input("Min 24h Volume ($)", 1000, 10000000, 10000, 1000)
    min_liquidity = st.number_input("Min Liquidity ($)", 1000, 10000000, 5000, 1000)
    edge_threshold = st.slider("Edge Threshold", 5.0, 10.0, 7.0, 0.5)
    st.divider()
    st.subheader("📡 APIs")
    st.markdown("✅ Gamma (markets)")
    st.markdown("✅ Data (history)")
    st.markdown("✅ CLOB (orderbook)")
    st.caption("All free, no keys needed for reads")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# ===== HEADER =====
st.title("🎯 Polymarket Live Tracker")
st.caption("Gamma + Data + CLOB APIs. Real markets. Real edge.")
st.divider()

# ===== FETCH =====
with st.spinner("Pulling from 3 Polymarket APIs..."):
    raw = get_gamma_markets(limit=100, min_liquidity=min_liquidity)
    markets = [parse_market(m) for m in raw]
    markets = [m for m in markets if m["volume_24h"] >= min_volume]
    
    # Calculate edge for all
    for m in markets:
        m["edge"] = calc_edge(m)
    
    # Fetch orderbook for top 20 by volume
    for m in markets[:20]:
        ob = get_market_orderbook(m["condition_id"])
        m["orderbook"] = ob
        # Best bid/ask spread
        bids = ob.get("bids", [])
        asks = ob.get("asks", [])
        if bids and asks:
            best_bid = float(bids[0]["price"]) if isinstance(bids[0], dict) else float(bids[0][0])
            best_ask = float(asks[0]["price"]) if isinstance(asks[0], dict) else float(asks[0][0])
            m["spread_bps"] = abs(best_ask - best_bid) * 10000
        else:
            m["spread_bps"] = None

if not markets:
    st.warning("No markets loaded. API may be rate-limited. Click Refresh.")
    st.stop()

# ===== KPIs =====
total_vol = sum(m["volume_24h"] for m in markets)
high_edge = len([m for m in markets if m["edge"] >= edge_threshold])
active_markets = len(markets)
avg_liq = sum(m["liquidity"] for m in markets) / len(markets)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Markets", active_markets)
k2.metric("24h Volume", f"${total_vol:,.0f}")
k3.metric("High Edge", high_edge, delta=">7.0")
k4.metric("Avg Liquidity", f"${avg_liq:,.0f}")
st.divider()

# ===== TABS =====
tab1, tab2, tab3, tab4 = st.tabs(["🔥 Live Markets", "⚡ Opportunities", "🎯 Targets", "📊 Market Detail"])

# ===== TAB 1: LIVE MARKETS =====
with tab1:
    st.subheader("All Active Markets")
    search = st.text_input("Filter...", placeholder="trump, crypto, election...")
    
    df = pd.DataFrame(markets)
    if search:
        df = df[df["title"].str.lower().str.contains(search.lower(), na=False)]
    df = df.sort_values("volume_24h", ascending=False)
    
    for _, m in df.head(25).iterrows():
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
        with c1:
            st.markdown(f"**{m['title']}**")
            st.caption(f"{m['category']} | Ends {str(m['end_date'])[:10]}")
        with c2:
            st.metric("Yes", f"{m['yes_price']:.1%}")
        with c3:
            st.metric("Vol 24h", f"${m['volume_24h']:,.0f}")
        with c4:
            st.metric("Liquidity", f"${m['liquidity']:,.0f}")
        with c5:
            st.metric("Edge", f"{m['edge']:.1f}")
            if m["edge"] >= edge_threshold:
                st.success("🔥")
        st.divider()

# ===== TAB 2: OPPORTUNITIES =====
with tab2:
    st.subheader("Asymmetric Opportunities")
    st.caption(f"Edge ≥ {edge_threshold}, decent volume. These have uncertainty + liquidity.")
    
    opps = [m for m in markets if m["edge"] >= edge_threshold and m["volume_24h"] > 10000]
    opps.sort(key=lambda x: x["edge"], reverse=True)
    
    if not opps:
        st.info("No high-edge markets right now. Lower threshold or check later.")
    
    for m in opps[:15]:
        pos = (bankroll * 0.02) * (m["edge"] / 10)
        spread_info = f"Spread: {m['spread_bps']:.0f} bps" if m.get('spread_bps') else ""
        
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            emoji = "🔥" if m["edge"] >= 9 else "⚡" if m["edge"] >= 7 else "📊"
            st.markdown(f"## {emoji}")
            st.markdown(f"**{m['edge']:.1f}/10**")
        with c2:
            st.markdown(f"**{m['title']}**")
            st.caption(f"Yes: {m['yes_price']:.1%} | Vol: ${m['volume_24h']:,.0f} | Liq: ${m['liquidity']:,.0f}")
            if spread_info:
                st.caption(spread_info)
        with c3:
            st.markdown(f"**${pos:,.0f}** suggested")
            st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        st.divider()

# ===== TAB 3: TARGETS =====
with tab3:
    st.subheader("Track by Category")
    
    TARGETS = {
        "Trump / Politics": ["trump", "donald", "election", "president", "vote", "biden", "kamala", "gop", "democrat"],
        "Elon / Tesla / Crypto": ["elon", "musk", "tesla", "spacex", "dogecoin", "doge", "bitcoin", "btc", "ethereum", "crypto"],
        "Sports": ["super bowl", "world cup", "olympics", "nba", "nfl", "ufc", "boxing"],
        "Pop Culture": ["taylor swift", "kanye", "kim kardashian", "celebrity", "oscar", "grammy", "album"],
        "Geopolitics": ["ukraine", "russia", "israel", "china", "war", "nato", "putin", "zelensky"],
        "Finance / Macro": ["fed", "inflation", "recession", "interest rate", "gdp", "unemployment", "sp500"],
    }
    
    for target_name, keywords in TARGETS.items():
        matches = [m for m in markets if any(kw in m["title"].lower() for kw in keywords)]
        matches.sort(key=lambda x: x["volume_24h"], reverse=True)
        
        if matches:
            with st.expander(f"🎯 {target_name} — {len(matches)} markets"):
                for m in matches[:7]:
                    st.markdown(f"**{m['title']}** — Yes: {m['yes_price']:.1%} | Vol: ${m['volume_24h']:,.0f} | Edge: {m['edge']:.1f}")
                    st.caption(f"[Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.caption(f"🎯 {target_name} — no active markets")

# ===== TAB 4: MARKET DETAIL =====
with tab4:
    st.subheader("Deep Dive")
    if not markets:
        st.warning("No markets loaded")
    else:
        market_titles = [m["title"] for m in markets]
        selected = st.selectbox("Pick a market", market_titles)
        m = next((m for m in markets if m["title"] == selected), None)
        
        if m:
            st.markdown(f"## {m['title']}")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Yes Price", f"{m['yes_price']:.2%}")
            c2.metric("24h Volume", f"${m['volume_24h']:,.0f}")
            c3.metric("Liquidity", f"${m['liquidity']:,.0f}")
            c4.metric("Edge Score", f"{m['edge']:.1f}")
            
            st.divider()
            
            # Show orderbook if we have it
            ob = m.get("orderbook", {})
            if ob:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("Bids")
                    bids = ob.get("bids", [])[:10]
                    if bids:
                        for b in bids:
                            if isinstance(b, dict):
                                st.text(f"${b.get('price', 0):.3f} × {b.get('size', 0):,.0f}")
                            else:
                                st.text(str(b))
                    else:
                        st.caption("No bids")
                
                with col_b:
                    st.subheader("Asks")
                    asks = ob.get("asks", [])[:10]
                    if asks:
                        for a in asks:
                            if isinstance(a, dict):
                                st.text(f"${a.get('price', 0):.3f} × {a.get('size', 0):,.0f}")
                            else:
                                st.text(str(a))
                    else:
                        st.caption("No asks")
            else:
                st.caption("Orderbook not available for this market")
            
            st.markdown(f"[🔗 Trade on Polymarket](https://polymarket.com/event/{m['slug']})")

# ===== FOOTER =====
st.divider()
st.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Gamma + Data + CLOB APIs")
