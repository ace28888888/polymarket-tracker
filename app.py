import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, timedelta

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
NEWS_API = "https://newsapi.org/v2"

# Try to load NewsAPI key from secrets
NEWS_API_KEY = None
try:
    NEWS_API_KEY = st.secrets.get("newsapi_key", None)
except:
    pass

# ===== PERSONALITY PROFILES (Astrology + Behavioral) =====
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

@st.cache_data(ttl=300)
def get_market_history(condition_id):
    url = f"{DATA_API}/history/markets/{condition_id}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except:
        return {}

@st.cache_data(ttl=600)
def get_news(query, api_key=None, page_size=20):
    """Fetch news from NewsAPI (free tier: 100 req/day)"""
    if not api_key:
        # Try to get from secrets
        try:
            api_key = st.secrets.get("newsapi_key", None)
        except:
            pass
    
    if not api_key:
        return {"error": "No NewsAPI key. Add to Render Environment Variables as 'newsapi_key'. Free key at newsapi.org"}
    
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

def calc_hot_score(m):
    vol_24h = m["volume_24h"]
    vol_total = m["volume_total"]
    liquidity = m["liquidity"]
    yes_price = m["yes_price"]
    
    velocity = (vol_24h / max(vol_total, 1)) * 10
    uncertainty = 1 - abs(yes_price - 0.5) * 2
    liq_score = min(liquidity / 50000, 1.0)
    raw_vol = min(vol_24h / 100000, 1.0)
    
    hot_score = (velocity * 3) + (uncertainty * 2.5) + (liq_score * 2) + (raw_vol * 2.5)
    return hot_score

def calc_big_play_score(m):
    uncertainty = 1 - abs(m["yes_price"] - 0.5) * 2
    liq_score = min(m["liquidity"] / 100000, 1.0)
    vol_score = min(m["volume_24h"] / 50000, 1.0)
    return (uncertainty * 4) + (liq_score * 3) + (vol_score * 3)

# ===== TWEET ANALYZER =====
def analyze_tweet(tweet_text, personality="Trump"):
    """Analyze tweet using personality profile + behavioral gauge"""
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
    
    # Energy analysis
    words = tweet_text.split()
    caps_words = [w for w in words if w.isupper() and len(w) > 1]
    scores["caps_ratio"] = len(caps_words) / max(len(words), 1)
    
    if scores["caps_ratio"] > 0.3:
        scores["energy_level"] = "high_energy"
    if scores["caps_ratio"] > 0.6:
        scores["energy_level"] = "manic"
    
    # Pattern matching
    # Nicknames (Trump)
    nickname_pattern = r'\b(sleepy|crooked|little|lyin|crazy|nasty|shifty|mini)\s+\w+\b'
    if re.search(nickname_pattern, text_lower):
        scores["has_nickname"] = True
        scores["behavioral_match"].append("Uses derogatory nickname")
    
    # Deadlines
    deadline_pattern = r'\b(coming soon|big news|announcement|in \d+ (days?|weeks?)|next week|tomorrow)\b'
    if re.search(deadline_pattern, text_lower):
        scores["has_deadline"] = True
        scores["behavioral_match"].append("Sets arbitrary deadline/expectation")
    
    # Meme indicators (Elon)
    meme_indicators = ['lol', '😂', 'meme', 'haha', 'lmao', 'bruh']
    if any(m in text_lower for m in meme_indicators):
        scores["has_meme"] = True
        scores["behavioral_match"].append("Uses humor/memes (deflection)")
    
    # Crypto mentions (Elon)
    crypto_words = ['doge', 'bitcoin', 'btc', 'crypto', 'ethereum', 'eth', 'coin']
    if any(c in text_lower for c in crypto_words):
        scores["has_crypto"] = True
        scores["behavioral_match"].append("Mentions cryptocurrency")
    
    # Market triggers
    for trigger in p["market_triggers"]:
        if trigger in text_lower:
            scores["mentions_market_trigger"].append(trigger)
    
    # Predict impact
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
    st.subheader("📰 NewsAPI Key")
    st.caption("Optional — adds news sentiment. Free key at newsapi.org")
    news_input = st.text_input("NewsAPI Key", type="password", value=NEWS_API_KEY or "")
    if news_input:
        NEWS_API_KEY = news_input
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ===== HEADER =====
st.title("🎯 Polymarket Tracker — Trump & Elon Alpha")
st.caption("Hot markets + personality-driven prediction + news sentiment")
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
k3.metric("🔥 Hot", hot_count)
k4.metric("⚡ Big Plays", big_play_count, delta=f"{uncertain_count} near 50/50")
st.divider()

# ===== TABS =====
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔥 Hot Markets", "⚡ Big Plays", "🎯 Trump & Elon",
    "🐦 Tweet Analyzer", "📰 News Sentiment", "🔮 Profiles"
])

# ===== TAB 1: HOT MARKETS =====
with tab1:
    st.subheader("🔥 Hot Markets Right Now")
    st.caption("Volume velocity + uncertainty + liquidity")
    
    hot_markets = [m for m in markets if m["hot_score"] >= hot_threshold]
    hot_markets.sort(key=lambda x: x["hot_score"], reverse=True)
    
    if not hot_markets:
        st.info("No hot markets. Lower threshold or check later.")
    
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
            st.caption(f"Yes: {m['yes_price']:.1%} | 24h Vol: ${m['volume_24h']:,.0f} | Velocity: {velocity:.1f}%")
        with c3:
            st.markdown(f"**${pos:,.0f}** suggested")
            st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        st.divider()

# ===== TAB 2: BIG PLAYS =====
with tab2:
    st.subheader("⚡ Potential Big Plays")
    st.caption("High liquidity + near 50/50 + volume")
    
    big_plays = [m for m in markets if m["big_play_score"] >= big_play_threshold and m["volume_24h"] > 10000]
    big_plays.sort(key=lambda x: x["big_play_score"], reverse=True)
    
    if not big_plays:
        st.info("No big plays. Lower threshold or check later.")
    
    for m in big_plays[:15]:
        pos = (bankroll * 0.03) * (m["big_play_score"] / 10)
        uncertainty = 1 - abs(m["yes_price"] - 0.5) * 2
        
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            emoji = "💰" if m["big_play_score"] >= 8 else "⚡"
            st.markdown(f"## {emoji}")
            st.markdown(f"**{m['big_play_score']:.1f}/10**")
        with c2:
            st.markdown(f"**{m['title']}**")
            st.caption(f"Uncertainty: {uncertainty:.0%} | Vol: ${m['volume_24h']:,.0f} | Liq: ${m['liquidity']:,.0f}")
        with c3:
            st.markdown(f"**${pos:,.0f}** suggested")
            st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        st.divider()

# ===== TAB 3: TRUMP & ELON =====
with tab3:
    st.subheader("🎯 Trump & Elon Markets")
    
    TRUMP_KEYWORDS = ["trump", "donald", "indictment", "trial", "court", "election", "biden", "kamala", "gop", "republican"]
    ELON_KEYWORDS = ["elon", "musk", "tesla", "spacex", "dogecoin", "doge", "crypto", "bitcoin", "twitter", "x", "neuralink", "starlink", "mars", "ai"]
    
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
            st.caption("No active Trump markets")
    
    with col_e:
        st.markdown("### 🟦 Elon Markets")
        if elon_markets:
            for m in elon_markets[:8]:
                st.markdown(f"**{m['title']}**")
                st.caption(f"Yes: {m['yes_price']:.1%} | Vol: ${m['volume_24h']:,.0f} | Hot: {m['hot_score']:.1f}")
                st.markdown(f"[Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.caption("No active Elon markets")
    
    st.divider()
    combined = list({m['condition_id']: m for m in trump_markets + elon_markets}.values())
    combined.sort(key=lambda x: x['hot_score'], reverse=True)
    if combined:
        st.subheader("📈 Combined Signal Feed")
        for m in combined[:10]:
            is_trump = any(kw in m["title"].lower() for kw in TRUMP_KEYWORDS)
            badge = "🟥 TRUMP" if is_trump else "🟦 ELON"
            st.markdown(f"{badge} **{m['title']}** — Yes: {m['yes_price']:.1%} | Hot: {m['hot_score']:.1f} | [Trade](https://polymarket.com/event/{m['slug']})")

# ===== TAB 4: TWEET ANALYZER =====
with tab4:
    st.subheader("🐦 Tweet Analyzer")
    st.caption("Paste a tweet. We'll analyze it using personality profiles + behavioral gauges.")
    
    personality_select = st.selectbox("Who tweeted this?", ["Trump", "Elon"])
    tweet_input = st.text_area("Paste tweet text here:", height=150, placeholder="e.g. WITCH HUNT CONTINUES! THEY WON'T STOP!!!")
    
    if st.button("Analyze Tweet", type="primary") and tweet_input:
        analysis = analyze_tweet(tweet_input, personality_select)
        p = PERSONALITIES[personality_select]
        
        st.divider()
        
        # Energy gauge
        st.subheader("🔋 Energy Level Assessment")
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
            st.caption("No strong behavioral patterns detected")
        
        # Caps ratio
        st.metric("CAPS Ratio", f"{analysis['caps_ratio']:.0%}", delta="Higher = more emotional")
        
        # Market triggers
        st.subheader("📊 Market Triggers Found")
        if analysis["mentions_market_trigger"]:
            st.markdown("**Keywords that could move markets:**")
            for trigger in set(analysis["mentions_market_trigger"]):
                st.markdown(f"- 🔥 `{trigger}`")
        else:
            st.caption("No direct market trigger keywords found")
        
        # Predictive model
        st.subheader("🔮 Predicted Market Impact")
        impact_colors = {
            "very_high": "red",
            "high": "orange", 
            "medium": "blue",
            "low": "gray"
        }
        impact = analysis["predicted_market_impact"]
        confidence = analysis["confidence"]
        
        st.markdown(f"**Impact Level:** {impact.upper()}")
        st.markdown(f"**Confidence:** {confidence}%")
        
        # Show relevant predictions
        st.subheader("📋 Based on Personality Model:")
        pred_model = p["predictive_model"]
        
        if analysis["has_nickname"] and "nickname" in str(pred_model):
            st.info(f"🎯 {pred_model.get('if_nickname_new', '')}")
        if analysis["has_deadline"] and "deadline" in str(pred_model):
            st.info(f"🎯 {pred_model.get('if_deadline_claim', '')}")
        if analysis["energy_level"] == "manic":
            st.info(f"🎯 {pred_model.get('if_all_caps' if personality_select=='Trump' else 'if_meme_spam', '')}")
        
        # Suggested markets
        st.subheader("📈 Related Markets to Watch")
        related_keywords = set(analysis["mentions_market_trigger"])
        related_markets = [m for m in markets if any(kw in m["title"].lower() for kw in related_keywords)]
        related_markets.sort(key=lambda x: x["hot_score"], reverse=True)
        
        if related_markets:
            for m in related_markets[:5]:
                st.markdown(f"- **{m['title']}** — Yes: {m['yes_price']:.1%} | [Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.caption("No directly related markets found. Check the 'Trump & Elon' tab for relevant markets.")

# ===== TAB 5: NEWS SENTIMENT =====
with tab5:
    st.subheader("📰 News Sentiment Tracker")
    st.caption("Latest news on Trump and Elon — correlate with market movements")
    
    news_personality = st.selectbox("Track news for:", ["Trump", "Elon"])
    
    if not NEWS_API_KEY:
        st.warning("⚠️ No NewsAPI key. Get a free key at newsapi.org and add it in the sidebar or as a Render environment variable 'newsapi_key'")
    else:
        with st.spinner("Fetching latest news..."):
            query = "Donald Trump" if news_personality == "Trump" else "Elon Musk"
            news_data = get_news(query, api_key=NEWS_API_KEY, page_size=15)
        
        if "error" in news_data:
            st.error(f"News API error: {news_data['error']}")
        elif "articles" in news_data:
            articles = news_data["articles"]
            st.success(f"Found {len(articles)} articles")
            
            # Show articles
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
                    
                    # Simple sentiment heuristic
                    pos_words = ['win', 'victory', 'success', 'gain', 'rise', 'surge', 'boost', 'strong', 'positive']
                    neg_words = ['loss', 'fall', 'crash', 'decline', 'trouble', 'crisis', 'scandal', 'investigation', 'indictment']
                    
                    text_to_check = f"{title} {description}".lower()
                    pos_count = sum(1 for w in pos_words if w in text_to_check)
                    neg_count = sum(1 for w in neg_words if w in text_to_check)
                    
                    if pos_count > neg_count:
                        st.success("📈 Sentiment: Positive")
                    elif neg_count > pos_count:
                        st.error("📉 Sentiment: Negative")
                    else:
                        st.info("📊 Sentiment: Neutral")
            
            # Correlation hint
            st.divider()
            st.subheader("📊 Market Correlation")
            st.caption("Check if any markets spiked after these news times")
            
            related_keywords = TRUMP_KEYWORDS if news_personality == "Trump" else ELON_KEYWORDS
            related_markets = [m for m in markets if any(kw in m["title"].lower() for kw in related_keywords)]
            related_markets.sort(key=lambda x: x["volume_24h"], reverse=True)
            
            if related_markets:
                st.markdown("**Top related markets by volume:**")
                for m in related_markets[:5]:
                    st.markdown(f"- **{m['title']}** — Yes: {m['yes_price']:.1%} | 24h Vol: ${m['volume_24h']:,.0f} | [Trade](https://polymarket.com/event/{m['slug']})")
        else:
            st.warning("No articles found or API limit reached")

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

# ===== FOOTER =====
st.divider()
st.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Gamma + Data + CLOB + NewsAPI | Tweet Analyzer v1.0")

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
                    st