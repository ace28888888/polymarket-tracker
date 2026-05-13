import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Polymarket Tracker — Combined Signal Alpha",
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
NEWS_API = "https://newsapi.org/v2"

NEWS_API_KEY = None
try:
    NEWS_API_KEY = st.secrets.get("newsapi_key", None)
except:
    pass

# ===== PERSONALITY PROFILES =====
PERSONALITIES = {
    "Trump": {
        "name": "Donald Trump",
        "western": "♊ Gemini (June 14)",
        "chinese": "🐕 Dog (1946 — Fire Dog)",
        "numerology": "🔢 Life Path 4 (Builder/Leader)",
        "element": "🔥 Fire (Dog) + Air (Gemini) = Explosive communication",
        "traits": [
            "Dual nature: charming then combative (Gemini split)",
            "Loyal to allies, vicious to enemies (Dog loyalty flipped)",
            "Thrives on chaos and attention — silence is death",
            "Life Path 4: builds empires, then tests their foundations",
            "Fire Dog: dramatic, theatrical, needs to be the hero"
        ],
        "speak_patterns": [
            "ALL CAPS when emotionally triggered",
            "Creates nicknames for enemies ('Sleepy Joe', 'Crooked')",
            "Declares victory before results ('I won by a lot!')",
            "Sets arbitrary deadlines ('BIG NEWS IN 2 WEEKS')",
            "Uses repetition for emphasis ('SAD!', 'WITCH HUNT!')",
            "Deflects with superlatives ('the greatest', 'nobody has ever')"
        ],
        "market_triggers": [
            "indictment", "trial", "court", "judge", "fraud",
            "election", "poll", "vote", "ballot", "rigged",
            "debate", "rally", "speech", "press conference",
            "truth social", "tweet", "post", "announcement"
        ],
        "hot_hours": "06:00-09:00 UTC (early morning US East Coast)",
        "behavioral_gauge": {
            "low_energy": "Silent for 12+ hours → Something big brewing or legal gag order",
            "normal": "2-5 posts/day, mix of attacks and boasts",
            "high_energy": "10+ posts, ALL CAPS, multiple nicknames → Market-moving event imminent",
            "manic": "20+ posts, retweeting random accounts, spelling errors → Emotional breakdown or major announcement"
        },
        "predictive_model": {
            "if_silent_12h": "60% chance major legal news drops within 24h",
            "if_all_caps": "75% chance he addresses specific market topic within 6h",
            "if_nickname_new": "50% chance that person is mentioned in new market within 48h",
            "if_deadline_claim": "40% chance he misses it, 30% chance it's underwhelming, 30% it's explosive"
        }
    },
    "Elon": {
        "name": "Elon Musk",
        "western": "♋ Cancer (June 28)",
        "chinese": "🐖 Pig/Boar (1971 — Metal Pig)",
        "numerology": "🔢 Life Path 7 (Seeker/Thinker/Analyst)",
        "element": "🪨 Metal (Pig) + Water (Cancer) = Cold, calculated, then emotional floods",
        "traits": [
            "Cancer: emotionally driven, protective shell, then sudden vulnerability",
            "Metal Pig: persistent, stubborn, accumulates wealth and knowledge",
            "Life Path 7: seeks hidden truths, conspiracy-adjacent thinking",
            "Needs to be perceived as smartest person in room",
            "Reacts to perceived slights with disproportionate force"
        ],
        "speak_patterns": [
            "Memes as deflection — when cornered, posts memes",
            "Cryptic one-liners ('The most entertaining outcome...')",
            "Replies to random small accounts (seeks validation)",
            "Sudden policy changes with no warning ('Twitter is now X')",
            "Uses 'lol' and '😂' when uncomfortable",
            "References sci-fi, anime, or obscure tech when excited"
        ],
        "market_triggers": [
            "dogecoin", "doge", "crypto", "bitcoin", "btc",
            "tesla", "spacex", "starlink", "neuralink", "boring",
            "twitter", "x", "social media", "free speech",
            "ai", "artificial intelligence", "chatgpt", "agi",
            "mars", "space", "mars colony", "rocket"
        ],
        "hot_hours": "02:00-06:00 UTC (late night California, early morning Europe)",
        "behavioral_gauge": {
            "low_energy": "Only business posts, no memes → Focused on something big or stressed",
            "normal": "Mix of business, memes, replies to fans",
            "high_energy": "Multiple memes, cryptic tweets, replies to critics → Something on his mind",
            "manic": "Rapid-fire tweets, changing profile pics, random declarations → Impulsive decision coming"
        },
        "predictive_model": {
            "if_meme_spam": "55% chance Dogecoin/crypto mention within 12h",
            "if_replies_critics": "65% chance he doubles down on controversial position within 6h",
            "if_cryptic_quote": "45% chance major product/service reveal within 72h",
            "if_policy_change": "80% chance related market moves >15% within 24h"
        }
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

@st.cache_data(ttl=600)
def get_news(query, api_key=None, page_size=20):
    if not api_key:
        try:
            api_key = st.secrets.get("newsapi_key", None)
        except:
            pass
    if not api_key:
        return {"error": "No NewsAPI key"}
    url = f"{NEWS_API}/everything"
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "language": "en",
        "apiKey": api_key
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

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

# ===== FRAMEWORK 1: MARKET DATA =====
def calc_hot_score(m):
    vol_24h = m["volume_24h"]
    vol_total = m["volume_total"]
    liquidity = m["liquidity"]
    yes_price = m["yes_price"]
    velocity = (vol_24h / max(vol_total, 1)) * 10
    uncertainty = 1 - abs(yes_price - 0.5) * 2
    liq_score = min(liquidity / 50000, 1.0)
    raw_vol = min(vol_24h / 100000, 1.0)
    return (velocity * 3) + (uncertainty * 2.5) + (liq_score * 2) + (raw_vol * 2.5)

def calc_big_play_score(m):
    uncertainty = 1 - abs(m["yes_price"] - 0.5) * 2
    liq_score = min(m["liquidity"] / 100000, 1.0)
    vol_score = min(m["volume_24h"] / 50000, 1.0)
    return (uncertainty * 4) + (liq_score * 3) + (vol_score * 3)

def market_framework_score(m):
    """Framework 1: Market Data (40% weight in combined)"""
    hot = calc_hot_score(m)
    big = calc_big_play_score(m)
    # Normalize to 0-100
    hot_norm = min(hot / 10 * 100, 100)
    big_norm = min(big / 10 * 100, 100)
    return (hot_norm * 0.6) + (big_norm * 0.4)

# ===== FRAMEWORK 2: PERSONALITY/BEHAVIORAL =====
def analyze_tweet(tweet_text, personality="Trump"):
    p = PERSONALITIES[personality]
    text_lower = tweet_text.lower()
    scores = {
        "energy_level": "normal",
        "caps_ratio": 0,
        "has_nickname": False,
        "has_deadline": False,
        "has_meme": False,
        "has_crypto": False,
        "mentions_market_trigger": [],
        "behavioral_match": [],
        "predicted_market_impact": "low",
        "confidence": 0
    }
    words = tweet_text.split()
    caps_words = [w for w in words if w.isupper() and len(w) > 1]
    scores["caps_ratio"] = len(caps_words) / max(len(words), 1)
    if scores["caps_ratio"] > 0.3:
        scores["energy_level"] = "high_energy"
    if scores["caps_ratio"] > 0.6:
        scores["energy_level"] = "manic"
    nickname_pattern = r'\b(sleepy|crooked|little|lyin|crazy|nasty|shifty|mini)\s+\w+\b'
    if re.search(nickname_pattern, text_lower):
        scores["has_nickname"] = True
        scores["behavioral_match"].append("Uses derogatory nickname")
    deadline_pattern = r'\b(coming soon|big news|announcement|in \d+ (days?|weeks?)|next week|tomorrow)\b'
    if re.search(deadline_pattern, text_lower):
        scores["has_deadline"] = True
        scores["behavioral_match"].append("Sets arbitrary deadline/expectation")
    meme_indicators = ['lol', '😂', 'meme', 'haha', 'lmao', 'bruh']
    if any(m in text_lower for m in meme_indicators):
        scores["has_meme"] = True
        scores["behavioral_match"].append("Uses humor/memes (deflection)")
    crypto_words = ['doge', 'bitcoin', 'btc', 'crypto', 'ethereum', 'eth', 'coin']
    if any(c in text_lower for c in crypto_words):
        scores["has_crypto"] = True
        scores["behavioral_match"].append("Mentions cryptocurrency")
    for trigger in p["market_triggers"]:
        if trigger in text_lower:
            scores["mentions_market_trigger"].append(trigger)
    trigger_count = len(scores["mentions_market_trigger"])
    if scores["energy_level"] == "manic" and trigger_count > 0:
        scores["predicted_market_impact"] = "very_high"
        scores["confidence"] = 85
    elif scores["energy_level"] == "high_energy" and trigger_count > 0:
        scores["predicted_market_impact"] = "high"
        scores["confidence"] = 70
    elif trigger_count > 0:
        scores["predicted_market_impact"] = "medium"
        scores["confidence"] = 55
    elif scores["energy_level"] in ["high_energy", "manic"]:
        scores["predicted_market_impact"] = "medium"
        scores["confidence"] = 45
    else:
        scores["predicted_market_impact"] = "low"
        scores["confidence"] = 25
    return scores

def personality_framework_score(tweet_analysis=None, personality="Trump", market_title=""):
    """Framework 2: Personality/Behavioral (30% weight in combined)"""
    if not tweet_analysis:
        return 50  # Neutral if no tweet data
    
    impact_scores = {"low": 30, "medium": 55, "high": 75, "very_high": 90}
    base = impact_scores.get(tweet_analysis["predicted_market_impact"], 50)
    confidence_boost = tweet_analysis["confidence"] / 100 * 10
    
    # Check if market is actually related to triggers
    if market_title:
        triggers = tweet_analysis.get("mentions_market_trigger", [])
        if any(t in market_title.lower() for t in triggers):
            base += 15  # Direct relevance bonus
    
    return min(base + confidence_boost, 100)

# ===== FRAMEWORK 3: NEWS SENTIMENT =====
def news_framework_score(news_data, personality="Trump", market_title=""):
    """Framework 3: News Sentiment (20% weight in combined)"""
    if "error" in news_data or "articles" not in news_data:
        return 50  # Neutral if no news
    
    articles = news_data["articles"][:10]
    if not articles:
        return 50
    
    pos_words = ['win', 'victory', 'success', 'gain', 'rise', 'surge', 'boost', 'strong', 'positive', 'breakthrough']
    neg_words = ['loss', 'fall', 'crash', 'decline', 'trouble', 'crisis', 'scandal', 'investigation', 'indictment', 'guilty', 'fraud']
    
    total_score = 0
    recent_count = 0
    now = datetime.now()
    
    for article in articles:
        text = f"{article.get('title','')} {article.get('description','')}".lower()
        published = article.get("publishedAt", "")
        
        # Time decay — recent news matters more
        try:
            pub_time = datetime.fromisoformat(published.replace('Z', '+00:00'))
            hours_ago = (now - pub_time.replace(tzinfo=None)).total_seconds() / 3600
            time_weight = max(1 - (hours_ago / 24), 0.1)  # Decay over 24h
        except:
            time_weight = 0.5
        
        pos = sum(1 for w in pos_words if w in text)
        neg = sum(1 for w in neg_words if w in text)
        
        if pos > neg:
            article_score = 70
        elif neg > pos:
            article_score = 30
        else:
            article_score = 50
        
        total_score += article_score * time_weight
        recent_count += time_weight
    
    if recent_count == 0:
        return 50
    
    avg_score = total_score / recent_count
    
    # Boost if news directly mentions market topic
    if market_title:
        for article in articles[:5]:
            text = f"{article.get('title','')} {article.get('description','')}".lower()
            market_keywords = [w for w in market_title.lower().split() if len(w) > 3]
            if any(kw in text for kw in market_keywords):
                avg_score = min(avg_score + 10, 100)
                break
    
    return avg_score

# ===== FRAMEWORK 4: TIMING =====
def timing_framework_score(m):
    """Framework 4: Timing (10% weight in combined)"""
    score = 50
    
    # Price proximity to 50/50 (more time = can be further from center)
    uncertainty = 1 - abs(m["yes_price"] - 0.5) * 2
    
    # If price is near 50/50 with high volume = good timing (event soon)
    if uncertainty > 0.7 and m["volume_24h"] > 50000:
        score = 80
    elif uncertainty > 0.5 and m["volume_24h"] > 20000:
        score = 65
    elif uncertainty < 0.3:
        score = 35  # Too certain, low edge
    
    # Liquidity check — can you actually trade?
    if m["liquidity"] < 10000:
        score -= 20  # Hard to enter/exit
    elif m["liquidity"] > 100000:
        score += 10
    
    return max(min(score, 100), 0)

# ===== COMBINED SIGNAL SCORE =====
def combined_signal_score(market, tweet_analysis=None, news_data=None, personality="Trump"):
    """
    COMBINED SIGNAL SCORE (0-100)
    
    Framework weights:
    - Market Data: 40% (objective market conditions)
    - Personality/Behavioral: 30% (tweet analysis, behavioral patterns)
    - News Sentiment: 20% (news velocity and sentiment)
    - Timing: 10% (entry timing, liquidity)
    """
    
    m_score = market_framework_score(market)
    p_score = personality_framework_score(tweet_analysis, personality, market["title"])
    n_score = news_framework_score(news_data, personality, market["title"])
    t_score = timing_framework_score(market)
    
    combined = (m_score * 0.40) + (p_score * 0.30) + (n_score * 0.20) + (t_score * 0.10)
    
    return {
        "combined": round(combined, 1),
        "market": round(m_score, 1),
        "personality": round(p_score, 1),
        "news": round(n_score, 1),
        "timing": round(t_score, 1),
        "action": get_action(combined),
        "position_pct": get_position_size(combined),
        "confidence": get_confidence_level(combined)
    }

def get_action(score):
    if score >= 75:
        return "🟢 STRONG BUY"
    elif score >= 60:
        return "🟡 BUY"
    elif score >= 45:
        return "🟠 WATCH"
    else:
        return "🔴 SKIP"

def get_position_size(score):
    """Suggested position as % of bankroll"""
    if score >= 85:
        return 4.0
    elif score >= 75:
        return 3.0
    elif score >= 65:
        return 2.0
    elif score >= 55:
        return 1.0
    elif score >= 45:
        return 0.5
    else:
        return 0.0

def get_confidence_level(score):
    if score >= 80:
        return "Very High"
    elif score >= 65:
        return "High"
    elif score >= 50:
        return "Medium"
    else:
        return "Low"

# ===== SIDEBAR =====
with st.sidebar:
    st.header("🎯 Settings")
    bankroll = st.number_input("Bankroll ($)", 1000, 10000000, 10000, 1000)
    min_volume = st.number_input("Min 24h Volume ($)", 1000, 10000000, 5000, 1000)
    min_liquidity = st.number_input("Min Liquidity ($)", 1000, 10000000, 5000, 1000)
    
    st.divider()
    st.subheader("🐦 Tweet Input (Optional)")
    tweet_personality = st.selectbox("Personality", ["Trump", "Elon"])
    tweet_input = st.text_area("Paste tweet:", height=80, placeholder="Paste tweet to include in signal...")
    
    st.divider()
    st.subheader("📰 NewsAPI Key (Optional)")
    news_input = st.text_input("NewsAPI Key", type="password", value=NEWS_API_KEY or "")
    if news_input:
        NEWS_API_KEY = news_input
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ===== HEADER =====
st.title("🎯 Polymarket Combined Signal Tracker")
st.caption("4-Framework Signal Fusion: Market (40%) + Personality (30%) + News (20%) + Timing (10%)")
st.divider()

# ===== FETCH DATA =====
with st.spinner("Loading markets..."):
    raw = get_gamma_markets(limit=200, min_liquidity=min_liquidity)
    markets = [parse_market(m) for m in raw]
    markets = [m for m in markets if m["volume_24h"] >= min_volume]

if not markets:
    st.warning("No markets loaded. API may be rate-limited.")
    st.stop()

# ===== FETCH NEWS (if key provided) =====
news_data = None
if NEWS_API_KEY:
    with st.spinner("Fetching news..."):
        query = "Donald Trump" if tweet_personality == "Trump" else "Elon Musk"
        news_data = get_news(query, api_key=NEWS_API_KEY, page_size=15)

# ===== PROCESS TWEET =====
tweet_analysis = None
if tweet_input.strip():
    tweet_analysis = analyze_tweet(tweet_input, tweet_personality)

# ===== CALCULATE COMBINED SCORES =====
for m in markets:
    m["scores"] = combined_signal_score(m, tweet_analysis, news_data, tweet_personality)

# Sort by combined score
markets.sort(key=lambda x: x["scores"]["combined"], reverse=True)

# ===== KPIs =====
total_vol = sum(m["volume_24h"] for m in markets)
strong_buy = len([m for m in markets if m["scores"]["combined"] >= 75])
buy = len([m for m in markets if 60 <= m["scores"]["combined"] < 75])
watch = len([m for m in markets if 45 <= m["scores"]["combined"] < 60])

k1, k2, k3, k4 = st.columns(4)
k1.metric("Markets", len(markets))
k2.metric("24h Volume", f"${total_vol:,.0f}")
k3.metric("🟢 Strong Buy", strong_buy)
k4.metric("🟡 Buy", buy, delta=f"{watch} watching")
st.divider()

# ===== TOP SIGNALS BANNER =====
top_signals = [m for m in markets if m["scores"]["combined"] >= 60][:5]
if top_signals:
    st.subheader("🔥 Top Combined Signals Right Now")
    cols = st.columns(min(len(top_signals), 5))
    for i, m in enumerate(cols):
        if i < len(top_signals):
            market = top_signals[i]
            score = market["scores"]["combined"]
            action = market["scores"]["action"]
            pos = (bankroll * market["scores"]["position_pct"] / 100)
            
            color = "green" if score >= 75 else "orange" if score >= 60 else "gray"
            with m:
                st.markdown(f"**{market['title'][:40]}...**")
                st.markdown(f"### {score}/100")
                st.markdown(f"**{action}**")
                st.caption(f"Suggested: ${pos:,.0f}")
                st.markdown(f"[Trade](https://polymarket.com/event/{market['slug']})")
    st.divider()

# ===== TABS =====
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Combined Signals", "🐦 Tweet Analyzer", "📰 News Sentiment",
    "🔥 Hot Markets", "🎯 Trump & Elon", "🔮 Profiles"
])

# ===== TAB 1: COMBINED SIGNALS =====
with tab1:
    st.subheader("📊 All Markets Ranked by Combined Signal Score")
    st.caption("Sorted by combined score. Higher = stronger signal across all 4 frameworks.")
    
    filter_action = st.multiselect("Filter by action:", 
                                   ["🟢 STRONG BUY", "🟡 BUY", "🟠 WATCH", "🔴 SKIP"],
                                   default=["🟢 STRONG BUY", "🟡 BUY", "🟠 WATCH"])
    
    search = st.text_input("Search markets...", placeholder="type to filter...")
    
    filtered = [m for m in markets if m["scores"]["action"] in filter_action]
    if search:
        filtered = [m for m in filtered if search.lower() in m["title"].lower()]
    
    for m in filtered[:30]:
        s = m["scores"]
        pos = (bankroll * s["position_pct"] / 100)
        
        # Color code the expander
        if s["combined"] >= 75:
            status_color = "🟢"
        elif s["combined"] >= 60:
            status_color = "🟡"
        elif s["combined"] >= 45:
            status_color = "🟠"
        else:
            status_color = "🔴"
        
        with st.expander(f"{status_color} {s['combined']}/100 | {m['title'][:60]}... | {s['action']}"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown(f"**{m['title']}**")
                st.caption(f"Yes: {m['yes_price']:.1%} | 24h Vol: ${m['volume_24h']:,.0f} | Liq: ${m['liquidity']:,.0f}")
                st.markdown(f"**Suggested Position:** ${pos:,.0f} ({s['position_pct']}% of bankroll)")
                st.markdown(f"**Confidence:** {s['confidence']}")
            
            with col2:
                st.markdown("**Framework Breakdown:**")
                st.markdown(f"📊 Market Data: **{s['market']}/100**")
                st.markdown(f"🧠 Personality: **{s['personality']}/100**")
                st.markdown(f"📰 News: **{s['news']}/100**")
                st.markdown(f"⏱️ Timing: **{s['timing']}/100**")
            
            with col3:
                st.markdown(f"### {s['action']}")
                st.markdown(f"[Trade Now](https://polymarket.com/event/{m['slug']})")
            
            # Signal meter
            st.progress(s["combined"] / 100)
            st.caption(f"Combined Signal: {s['combined']}/100")
        
        st.divider()

# ===== TAB 2: TWEET ANALYZER =====
with tab2:
    st.subheader("🐦 Tweet Analyzer")
    st.caption("Paste a tweet. Analyzes using personality + behavioral + predictive models.")
    
    ta_personality = st.selectbox("Who tweeted?", ["Trump", "Elon"], key="ta_personality")
    ta_tweet = st.text_area("Paste tweet:", height=150, placeholder="e.g. WITCH HUNT CONTINUES! BIG NEWS COMING!!!", key="ta_tweet")
    
    if st.button("Analyze Tweet", type="primary", key="ta_button") and ta_tweet:
        analysis = analyze_tweet(ta_tweet, ta_personality)
        p = PERSONALITIES[ta_personality]
        
        st.divider()
        
        # Energy gauge
        st.subheader("🔋 Energy Level")
        energy = analysis["energy_level"]
        energy_desc = p["behavioral_gauge"].get(energy, "Unknown")
        
        if energy == "manic":
            st.error(f"**{energy.upper()}** — {energy_desc}")
        elif energy == "high_energy":
            st.warning(f"**{energy.upper()}** — {energy_desc}")
        elif energy == "low_energy":
            st.info(f"**{energy.upper()}** — {energy_desc}")
        else:
            st.success(f"**{energy.upper()}** — {energy_desc}")
        
        # Pattern matches
        st.subheader("🎯 Pattern Matches")
        if analysis["behavioral_match"]:
            for match in analysis["behavioral_match"]:
                st.markdown(f"- ✅ {match}")
        else:
            st.caption("No strong patterns")
        
        st.metric("CAPS Ratio", f"{analysis['caps_ratio']:.0%}")
        
        # Market triggers
        st.subheader("📊 Market Triggers")
        if analysis["mentions_market_trigger"]:
            st.markdown("**Keywords:**")
            for trigger in set(analysis["mentions_market_trigger"]):
                st.markdown(f"- 🔥 `{trigger}`")
        else:
            st.caption("No direct triggers")
        
        # Predictive
        st.subheader("🔮 Predicted Impact")
        st.markdown(f"**Impact:** {analysis['predicted_market_impact'].upper()} | **Confidence:** {analysis['confidence']}%")
        
        # Show personality predictions
        pred_model = p["predictive_model"]
        if analysis["has_nickname"] and "nickname" in str(pred_model):
            st.info(f"🎯 {pred_model.get('if_nickname_new', '')}")
        if analysis["has_deadline"] and "deadline" in str(pred_model):
            st.info(f"🎯 {pred_model.get('if_deadline_claim', '')}")
        if analysis["energy_level"] == "manic":
            st.info(f"🎯 {pred_model.get('if_all_caps' if ta_personality=='Trump' else 'if_meme_spam', '')}")
        
        # Related markets
        st.subheader("📈 Related Markets")
        related = [m for m in markets if any(t in m["title"].lower() for t in analysis.get("mentions_market_trigger", []))]
        related.sort(key=lambda x: x["scores"]["combined"], reverse=True)
        if related:
            for m in related[:5]:
                s = m["scores"]
                st.markdown(f"- **{m['title']}** — Score: {s['combined']}/100 | {s['action']} | [Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.caption("No directly related markets. Check Combined Signals tab.")

# ===== TAB 3: NEWS SENTIMENT =====
with tab3:
    st.subheader("📰 News Sentiment Tracker")
    st.caption("Latest news on Trump and Elon — correlate with market movements")
    
    news_personality = st.selectbox("Track news for:", ["Trump", "Elon"], key="news_personality")
    
    if not NEWS_API_KEY:
        st.warning("⚠️ No NewsAPI key. Get a free key at newsapi.org and add it as Render env var 'newsapi_key' or in sidebar")
    else:
        with st.spinner("Fetching latest news..."):
            query = "Donald Trump" if news_personality == "Trump" else "Elon Musk"
            news_data = get_news(query, api_key=NEWS_API_KEY, page_size=15)
        
        if "error" in news_data:
            st.error(f"News API error: {news_data['error']}")
        elif "articles" in news_data:
            articles = news_data["articles"]
            st.success(f"Found {len(articles)} articles")
            
            for article in articles:
                title = article.get("title", "No title")
                source = article.get("source", {}).get("name", "Unknown")
                published = article.get("publishedAt", "")
                url = article.get("url", "")
                description = article.get("description", "")
                
                with st.expander(f"📰 {title} — {source}"):
                    st.caption(f"Published: {published[:10]} {published[11:16]}")
                    if description:
                        st.markdown(description)
                    if url:
                        st.markdown(f"[Read full article]({url})")
                    
                    pos_words = ['win', 'victory', 'success', 'gain', 'rise', 'surge', 'boost', 'strong', 'positive', 'breakthrough']
                    neg_words = ['loss', 'fall', 'crash', 'decline', 'trouble', 'crisis', 'scandal', 'investigation', 'indictment', 'guilty', 'fraud']
                    
                    text_to_check = f"{title} {description}".lower()
                    pos_count = sum(1 for w in pos_words if w in text_to_check)
                    neg_count = sum(1 for w in neg_words if w in text_to_check)
                    
                    if pos_count > neg_count:
                        st.success("📈 Sentiment: Positive")
                    elif neg_count > pos_count:
                        st.error("📉 Sentiment: Negative")
                    else:
                        st.info("📊 Sentiment: Neutral")
            
            st.divider()
            st.subheader("📊 Market Correlation")
            st.caption("Check if any markets spiked after these news times")
            
            TRUMP_KEYWORDS = ["trump", "donald", "indictment", "trial", "court", "election", "biden", "kamala", "gop", "republican"]
            ELON_KEYWORDS = ["elon", "musk", "tesla", "spacex", "dogecoin", "doge", "crypto", "bitcoin", "twitter", "x", "neuralink", "starlink", "mars", "ai"]
            related_keywords = TRUMP_KEYWORDS if news_personality == "Trump" else ELON_KEYWORDS
            related_markets = [m for m in markets if any(kw in m["title"].lower() for kw in related_keywords)]
            related_markets.sort(key=lambda x: x["scores"]["combined"], reverse=True)
            
            if related_markets:
                st.markdown("**Top related markets by signal score:**")
                for m in related_markets[:5]:
                    s = m["scores"]
                    st.markdown(f"- **{m['title']}** — Yes: {m['yes_price']:.1%} | Signal: {s['combined']}/100 | {s['action']} | [Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.warning("No articles found or API limit reached")

# ===== TAB 4: HOT MARKETS =====
with tab4:
    st.subheader("🔥 Hot Markets")
    st.caption("Markets ranked by volume velocity + uncertainty + liquidity")
    
    hot_markets = sorted(markets, key=lambda x: x["scores"]["market"], reverse=True)
    
    for m in hot_markets[:20]:
        s = m["scores"]
        pos = (bankroll * s["position_pct"] / 100)
        velocity = (m["volume_24h"] / max(m["volume_total"], 1)) * 100
        
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            emoji = "🔥🔥" if s["market"] >= 80 else "🔥" if s["market"] >= 60 else "⚡"
            st.markdown(f"## {emoji}")
            st.markdown(f"**{s['market']:.0f}/100**")
        with c2:
            st.markdown(f"**{m['title']}**")
            st.caption(f"Yes: {m['yes_price']:.1%} | 24h Vol: ${m['volume_24h']:,.0f} | Velocity: {velocity:.1f}%")
            st.caption(f"Combined Signal: {s['combined']}/100 | {s['action']}")
        with c3:
            st.markdown(f"**${pos:,.0f}** suggested")
            st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        st.divider()

# ===== TAB 5: TRUMP & ELON =====
with tab5:
    st.subheader("🎯 Trump & Elon Markets")
    
    TRUMP_KEYWORDS = ["trump", "donald", "indictment", "trial", "court", "election", "biden", "kamala", "gop", "republican"]
    ELON_KEYWORDS = ["elon", "musk", "tesla", "spacex", "dogecoin", "doge", "crypto", "bitcoin", "twitter", "x", "neuralink", "starlink", "mars", "ai"]
    
    trump_markets = [m for m in markets if any(kw in m["title"].lower() for kw in TRUMP_KEYWORDS)]
    elon_markets = [m for m in markets if any(kw in m["title"].lower() for kw in ELON_KEYWORDS)]
    trump_markets.sort(key=lambda x: x["scores"]["combined"], reverse=True)
    elon_markets.sort(key=lambda x: x["scores"]["combined"], reverse=True)
    
    col_t, col_e = st.columns(2)
    
    with col_t:
        st.markdown("### 🟥 Trump Markets")
        if trump_markets:
            for m in trump_markets[:8]:
                s = m["scores"]
                st.markdown(f"**{m['title']}**")
                st.caption(f"Yes: {m['yes_price']:.1%} | Signal: {s['combined']}/100 | {s['action']}")
                st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.caption("No active Trump markets")
    
    with col_e:
        st.markdown("### 🟦 Elon Markets")
        if elon_markets:
            for m in elon_markets[:8]:
                s = m["scores"]
                st.markdown(f"**{m['title']}**")
                st.caption(f"Yes: {m['yes_price']:.1%} | Signal: {s['combined']}/100 | {s['action']}")
                st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.caption("No active Elon markets")

# ===== TAB 6: PROFILES =====
with tab6:
    st.subheader("🔮 Personality & Communication Profiles")
    
    for name, p in PERSONALITIES.items():
        with st.expander(f"🔮 {p['name']} — {p['western']} | {p['chinese']} | {p['numerology']}", expanded=(name=="Trump")):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Element:** {p['element']}")
                st.markdown("**Core Traits:**")
                for trait in p['traits']:
                    st.markdown(f"- {trait}")
                st.markdown("**Communication Patterns:**")
                for pattern in p['speak_patterns']:
                    st.markdown(f"- 💬 {pattern}")
            with col2:
                st.markdown("**Behavioral Gauge:**")
                for level, desc in p['behavioral_gauge'].items():
                    st.markdown(f"- **{level.replace('_', ' ').title()}:** {desc}")
                st.markdown("**Hot Hours:**")
                st.markdown(f"- {p['hot_hours']}")
                st.markdown("**Predictive Model:**")
                for pred, desc in p['predictive_model'].items():
                    st.markdown(f"- **{pred.replace('if_', '').replace('_', ' ').title()}:** {desc}")
            
            st.divider()
            st.markdown("**🎯 Market Triggers to Watch:**")
            triggers = ', '.join([f'`{t}`' for t in p['market_triggers'][:10]])
            st.markdown(triggers)
    
    st.divider()
    st.subheader("📋 Combined Signal Methodology")
    st.markdown("""
    **How the Combined Signal Score works:**
    
    1. **Market Data Framework (40%)** — Volume velocity, liquidity depth, price uncertainty
    2. **Personality Framework (30%)** — Tweet analysis, behavioral patterns, predictive models
    3. **News Sentiment Framework (20%)** — Headline velocity, sentiment scoring, time decay
    4. **Timing Framework (10%)** — Entry timing, liquidity for exit, resolution proximity
    
    **Actions:**
    - 🟢 **STRONG BUY** (75-100): All frameworks align. High conviction.
    - 🟡 **BUY** (60-74): Most frameworks positive. Good setup.
    - 🟠 **WATCH** (45-59): Mixed signals. Wait for confirmation.
    - 🔴 **SKIP** (0-44): Weak or conflicting signals.
    """)

# ===== FOOTER =====
st.divider()
st.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Combined Signal v2.0 | 4-Framework Fusion")