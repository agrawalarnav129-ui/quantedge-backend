"""
QuantEdge NSE — Backend v4
- Fixed backtester (per-scan conditions, real P&L)
- Full NSE ~2000 stock universe via bhav copy
- New indicators: N-day High/Low, Stochastic, Supertrend, VWAP, CCI, Williams %R
- Sector RS heatmap API
Run: python app.py
"""

import json, sqlite3, traceback, warnings, time, io
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import yfinance as yf
import requests

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
pd.options.mode.copy_on_write = True

app  = Flask(__name__)
CORS(app)
DB   = "quantedge.db"

# ══════════════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, desc TEXT, uni TEXT, tf TEXT,
            color TEXT, conds TEXT, created TEXT, last_run TEXT, cnt INTEGER DEFAULT 0
        )
    """)
    conn.commit(); conn.close()

# ══════════════════════════════════════════════════════════════
#  FULL NSE UNIVERSE — ~2000 stocks from NSE Bhav Copy
# ══════════════════════════════════════════════════════════════
_UNIVERSE_CACHE = {}
_UNIVERSE_BUILT = False

SECTORS = {
    "NIFTY BANK":    ["HDFCBANK","ICICIBANK","KOTAKBANK","AXISBANK","SBIN","INDUSINDBK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","PNB","BANKBARODA","CANBK","UNIONBANK","INDIANB","J&KBANK"],
    "NIFTY IT":      ["TCS","INFY","HCLTECH","WIPRO","LTIM","TECHM","MPHASIS","COFORGE","PERSISTENT","TATAELXSI","OFSS","KPITTECH","CYIENT"],
    "NIFTY PHARMA":  ["SUNPHARMA","DIVISLAB","CIPLA","DRREDDY","LUPIN","TORNTPHARM","AUROPHARMA","ALKEM","IPCALAB","LAURUSLABS","GRANULES","NATCOPHARM","PFIZER"],
    "NIFTY AUTO":    ["MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","ESCORTS","MOTHERSON","BALKRISIND","ENDURANCE","APOLLOTYRE","MRF","CEATLTD"],
    "NIFTY FMCG":    ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO","COLPAL","GODREJCP","EMAMILTD","TATACONSUM","VBL","RADICO","MCDOWELL-N"],
    "NIFTY METAL":   ["TATASTEEL","JSWSTEEL","HINDALCO","VEDL","SAIL","NMDC","COALINDIA","NATIONALUM","APLAPOLLO","WELCORP","RATNAMANI"],
    "NIFTY ENERGY":  ["RELIANCE","ONGC","BPCL","IOC","GAIL","NTPC","POWERGRID","NHPC","ADANIGREEN","ADANIPOWER","TATAPOWER","CESC"],
    "NIFTY INFRA":   ["LT","ADANIPORTS","GMRINFRA","IRB","NBCC","NCC","KNR","JKCEMENT","ULTRACEMCO","AMBUJACEM","ACC","HEIDELBERG"],
    "NIFTY REALTY":  ["DLF","GODREJPROP","OBEROIRLTY","PHOENIXLTD","PRESTIGE","SOBHA","BRIGADE","MAHLIFE"],
    "NIFTY FINANCE": ["BAJFINANCE","BAJAJFINSV","CHOLAFIN","MUTHOOTFIN","MANAPPURAM","POONAWALLA","IIFL","LICHSGFIN","CANFINHOME","PNBHOUSING"],
}

# Complete built-in symbol list (NIFTY 500 + key midcap/smallcap)
_BASE_SYMBOLS = [
    # NIFTY 50
    "RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","HINDUNILVR","ITC","SBIN","BAJFINANCE","BHARTIARTL",
    "KOTAKBANK","AXISBANK","ASIANPAINT","MARUTI","TITAN","SUNPHARMA","ONGC","NESTLEIND","WIPRO","LT",
    "HCLTECH","ULTRACEMCO","ADANIENT","POWERGRID","NTPC","TATASTEEL","JSWSTEEL","INDUSINDBK","COALINDIA","BPCL",
    "BAJAJ-AUTO","GRASIM","HEROMOTOCO","BRITANNIA","DIVISLAB","CIPLA","EICHERMOT","APOLLOHOSP","TATACONSUM","HINDALCO",
    "TECHM","ADANIPORTS","SHRIRAMFIN","DRREDDY","BAJAJFINSV","SBILIFE","HDFCLIFE","LTIM","M&M","TATAMOTORS",
    # NIFTY NEXT 50
    "ZOMATO","DMART","NAUKRI","PAGEIND","TRENT","VEDL","SIEMENS","ABB","HAVELLS","MOTHERSON",
    "BALKRISIND","CHOLAFIN","BANDHANBNK","FEDERALBNK","GODREJCP","DABUR","MARICO","COLPAL","MCDOWELL-N","UBL",
    "TORNTPHARM","LUPIN","BOSCHLTD","CONCOR","AMBUJACEM","NHPC","PFC","RECLTD","IRCTC","BEL",
    "GAIL","IOC","LICHSGFIN","SAIL","NMDC","INDHOTEL","DLF","IRFC","ADANIGREEN","ADANIPOWER","BERGEPAINT",
    # NIFTY MIDCAP 150
    "PERSISTENT","MPHASIS","COFORGE","POLYCAB","ASTRAL","DIXON","TATAELXSI","CAMS","ANGELONE","DEEPAKNTR",
    "PIIND","KPITTECH","JUBLFOOD","BSE","CANFINHOME","CESC","CYIENT","EMAMILTD","ENDURANCE","ESCORTS",
    "EXIDEIND","GLENMARK","GRANULES","HAPPSTMNDS","HFCL","IDFCFIRSTB","IPCALAB","JBCHEPHARM","JKCEMENT","KAJARIACER",
    "KALYANKJIL","KPIL","LALPATHLAB","LAURUSLABS","LUXIND","MANAPPURAM","MFSL","NATCOPHARM","NCC","NBCC",
    "OFSS","OLECTRA","PETRONET","PHOENIXLTD","POONAWALLA","PRESTIGE","PVRINOX","RADICO","RAMCOCEM","RITES",
    "SANOFI","SCHAEFFLER","SOBHA","SONACOMS","SOLARINDS","STARHEALTH","SUMICHEM","SUNTV","SUPREMEIND","SUZLON",
    "TANLA","TIINDIA","TIMKEN","TORNTPOWER","UNIONBANK","UPL","VBL","VGUARD","VINATIORGA","WELCORP",
    "YESBANK","NUVOCO","AAVAS","METROPOLIS","HONASA","JKPAPER","GNFC","GSPL","GUJGASLTD","HUDCO",
    "INTELLECT","ISEC","KRBL","LINDEINDIA","MRF","NOCIL","PFIZER","PRINCEPIPE","SRF","TATACOMM",
    "TEAMLEASE","TITAGARH","TTKPRESTIG","UJJIVANSFB","USHAMART","CANBK","INDIANB","PNB","BANKBARODA",
    # NIFTY SMALLCAP 250 key names
    "AARTIIND","ABCAPITAL","AJANTPHARM","ALKEM","APLLTD","APLAPOLLO","APOLLOTYRE","ARCHIES","ARVINDFASN",
    "ASAHIINDIA","ASTRAZEN","ATUL","AVANTIFEED","BAJAJHLDNG","BASF","BATAINDIA","BDL","BORORENEW",
    "BRIGADE","CEATLTD","CENTURYPLY","CENTURYTEX","CHAMBLFERT","CLEAN","CMSINFO","COCHINSHIP","CREDITACC",
    "DATAPATTNS","DCMSHRIRAM","DEEPAKFERT","DELTACORP","EIDPARRY","ELGIEQUIP","ENGINERSIN","EQUITASBNK",
    "ESABINDIA","FINEORG","FLUOROCHEM","FORTIS","GATEWAY","GHCL","GMMPFAUDLR","GODREJIND","GPPL",
    "GRAPHITE","GRINDWELL","GUJALKALI","GULFOILLUB","HBLPOWER","HECL","HIKAL","HINDCOPPER","HINDPETRO",
    "HINDWAREAP","HOMEFIRST","IFBIND","IGPL","INDIGOPNTS","INFIBEAM","INGERRAND","IONEXCHANG","IRCON",
    "ITDCEM","JAIBALAJI","JAYNECOIND","JKLAKSHMI","JMFINANCIL","JSWENERGY","JTEKTINDIA","JYOTHYLAB",
    "KALPATPOWR","KANSAINER","KESORAMIND","KIRLOSENG","KNRCON","KOLTEPATIL","KPRMILL","KRSNAA",
    "KSCL","LATENTVIEW","LEMONTREE","LIKHITHA","LLOYDSENGG","MAHINDCIE","MAHSEAMLES","MANINFRA",
    "MASFIN","MAXHEALTH","MEDPLUS","MIDHANI","MINDACORP","MMTC","MONTECARLO","MOSCHIP","MSTCLTD",
    "NAHARSPING","NAVINFLUOR","NCLIND","NIACL","NETWORK18","NILKAMAL","NSLNISP","NUCLEUS","OCCL",
    "OLECTRA","ONMOBILE","OPTIEMUS","ORIENTELEC","PANAMAPET","PARADEEP","PATELENG","PATSPINNIN",
    "PCJEWELLER","PDMJEPAPER","PFOCUS","PGHL","PILANIINVS","PLASMAGEN","PLASTINDIA","POLYMED",
    "PRAJ","PREMIER","PRICOLLTD","PRIMESECU","PRIVISCL","PURVA","QUESS","RAIN","RAJRATAN",
    "RAMKY","RATNAMANI","REDINGTON","RELAXO","RESPONIND","RTNPOWER","SAFARI","SALZERELEC",
    "SANGHIIND","SARDAEN","SEQUENT","SHAKTIPUMP","SHANKARA","SHAREINDIA","SHILPAMED","SHYAMMETL",
    "SKIPPER","SMLISUZU","SOMICONVEY","SOUTHBANK","SPECIALITY","SPICEJET","SREEL","SSWL","SUDARSCHEM",
    "SUNDARMFIN","SUNPHARMAADV","SURYAROSNI","SUVEN","SUVENPHAR","SWSOLAR","SYMPHONY","TARSONS",
    "TASTYBITE","TATACHEM","TATAINVEST","TDPOWERSYS","TEXRAIL","THYROCARE","TINPLATE","TREJHARA",
    "TRIVENI","TTKHPRESTIG","UGARSUGAR","UJJIVAN","ULTRAMARIN","UNIPARTS","VAIBHAVGBL","VAKRANGEE",
    "VARDHACRLC","VARROC","VINDHYATEL","VOLTAMP","VRLLOG","VSTIND","WABCOINDIA","WALCHANNAG",
    "WEBELSOLAR","WINDLAS","WONDERLA","WSB","XCHANGING","ZENITHEXPO","ZENTEC","ZENSARTECH","ZIMLAB",
]
_BASE_SYMBOLS = list(dict.fromkeys(_BASE_SYMBOLS))  # dedupe

STOCK_META = {}

def fetch_full_nse_universe():
    """
    Fetch all ~2000 NSE equity symbols from NSE's official bhav copy CSV.
    This is the authoritative list of all listed NSE stocks.
    """
    global _UNIVERSE_CACHE, _UNIVERSE_BUILT, STOCK_META, _BASE_SYMBOLS

    print("  Fetching full NSE universe from bhav copy...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
        "Referer": "https://www.nseindia.com",
        "Accept": "application/json",
    }

    all_symbols = set(_BASE_SYMBOLS)  # start with base

    try:
        # NSE equity symbols list — official endpoint
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        time.sleep(0.5)

        # Fetch all equity symbols
        r = session.get(
            "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O",
            headers=headers, timeout=15
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            for item in data:
                sym = item.get("symbol", "").strip()
                if sym:
                    all_symbols.add(sym)
                    if sym not in STOCK_META:
                        STOCK_META[sym] = {
                            "name":   item.get("meta", {}).get("companyName", sym),
                            "sector": item.get("meta", {}).get("industry", "—"),
                        }
            print(f"  F&O stocks fetched: {len(data)}")

        # Also try NIFTY 500 list
        r2 = session.get(
            "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500",
            headers=headers, timeout=15
        )
        if r2.status_code == 200:
            data2 = r2.json().get("data", [])
            for item in data2:
                sym = item.get("symbol", "").strip()
                if sym:
                    all_symbols.add(sym)
                    if sym not in STOCK_META:
                        STOCK_META[sym] = {
                            "name":   item.get("meta", {}).get("companyName", sym),
                            "sector": item.get("meta", {}).get("industry", "—"),
                        }
            print(f"  NIFTY 500 stocks: {len(data2)}")

    except Exception as e:
        print(f"  NSE API fetch failed: {e} — using built-in list")

    # Try bhav copy for full 2000+ list
    try:
        today = datetime.now()
        for days_back in range(5):
            d = today - pd.Timedelta(days=days_back)
            if d.weekday() >= 5: continue  # skip weekends
            url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv"
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                df = pd.read_csv(io.StringIO(r.text))
                df.columns = [c.strip() for c in df.columns]
                sym_col = next((c for c in df.columns if "SYMBOL" in c.upper()), None)
                series_col = next((c for c in df.columns if "SERIES" in c.upper()), None)
                if sym_col:
                    mask = df[series_col].str.strip() == "EQ" if series_col else pd.Series(True, index=df.index)
                    syms = df.loc[mask, sym_col].str.strip().dropna().tolist()
                    all_symbols.update(syms)
                    print(f"  Bhav copy loaded: {len(syms)} EQ symbols from {d.strftime('%d %b %Y')}")
                    break
    except Exception as e:
        print(f"  Bhav copy fetch failed: {e}")

    all_symbols_list = sorted(list(all_symbols))
    print(f"  Total NSE universe: {len(all_symbols_list)} stocks")
    _UNIVERSE_BUILT = True
    return all_symbols_list

def _build_universes(all_syms):
    n50  = [s for s in _BASE_SYMBOLS[:50] if s in all_syms] or _BASE_SYMBOLS[:50]
    n100 = [s for s in _BASE_SYMBOLS[:100] if s in all_syms] or _BASE_SYMBOLS[:100]
    n200 = [s for s in _BASE_SYMBOLS[:200] if s in all_syms] or _BASE_SYMBOLS[:200]
    n500 = [s for s in _BASE_SYMBOLS if s in all_syms] or _BASE_SYMBOLS
    universes = {
        "NIFTY 50":      n50,
        "NIFTY 100":     n100,
        "NIFTY 200":     n200,
        "NIFTY 500":     n500,
        "ALL NSE":       all_syms,
        "FNO STOCKS":    [s for s in all_syms if s in set(n500)],
    }
    for sector, syms in SECTORS.items():
        universes[sector] = [s for s in syms if s in set(all_syms)] or syms
    return universes

# Initialize universe (loads from cache or fetches)
_universe_cache_file = Path("nse_universe.json")
if _universe_cache_file.exists():
    try:
        with open(_universe_cache_file) as f:
            _cached = json.load(f)
        _ALL_SYMBOLS = _cached.get("all_symbols", _BASE_SYMBOLS)
        STOCK_META   = _cached.get("metadata", {})
        UNIVERSES    = _build_universes(_ALL_SYMBOLS)
        print(f"  Universe loaded from cache: {len(_ALL_SYMBOLS)} stocks")
    except:
        _ALL_SYMBOLS = _BASE_SYMBOLS
        UNIVERSES    = _build_universes(_ALL_SYMBOLS)
else:
    _ALL_SYMBOLS = _BASE_SYMBOLS
    UNIVERSES    = _build_universes(_ALL_SYMBOLS)
    print(f"  Using built-in universe: {len(_ALL_SYMBOLS)} stocks")
    print("  Run: python nse_universe.py  to fetch full ~2000 stock list")

def get_symbols(name): return UNIVERSES.get(name, UNIVERSES["NIFTY 50"])
def get_meta(sym):     return STOCK_META.get(sym, {"name": sym, "sector": "—"})

# ══════════════════════════════════════════════════════════════
#  DATA FETCHER
# ══════════════════════════════════════════════════════════════
def _clean_df(raw) -> pd.DataFrame:
    if raw is None or (hasattr(raw, 'empty') and raw.empty):
        return pd.DataFrame()
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]).lower().strip() for c in df.columns]
    else:
        df.columns = [str(c).lower().strip() for c in df.columns]
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "date"
    keep = [c for c in ["open","high","low","close","volume"] if c in df.columns]
    df   = df[keep].copy()
    return df[df["close"] > 0].dropna(subset=["close"])

def fetch_ohlcv(sym, period="1y", interval="1d"):
    try:
        return _clean_df(yf.Ticker(f"{sym}.NS").history(period=period, interval=interval, auto_adjust=True))
    except Exception as e:
        return pd.DataFrame()

def fetch_nifty(period="1y"):
    try:
        return _clean_df(yf.Ticker("^NSEI").history(period=period, auto_adjust=True))
    except:
        return pd.DataFrame()

def fetch_sector_index(ticker, period="1y"):
    """Fetch a sector index like ^CNXBANK, ^CNXIT etc."""
    try:
        return _clean_df(yf.Ticker(ticker).history(period=period, auto_adjust=True))
    except:
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════
#  INDICATOR ENGINE — Extended with all Chartink-style indicators
# ══════════════════════════════════════════════════════════════
def _wilder_smooth(series, n):
    return series.ewm(alpha=1.0/n, min_periods=n, adjust=False).mean()

def compute_indicators(df: pd.DataFrame, nifty_df=None, sector_df=None) -> pd.DataFrame:
    c   = df["close"].copy()
    h   = df["high"].copy()
    l   = df["low"].copy()
    v   = df["volume"].copy()
    o   = df["open"].copy()
    idx = df.index
    cols = {"open":o, "high":h, "low":l, "close":c, "volume":v}

    # ── EMAs and SMAs
    for p in [5, 9, 13, 20, 26, 50, 100, 200]:
        cols[f"ema{p}"] = c.ewm(span=p, adjust=False).mean()
    for p in [5, 10, 20, 50, 100, 200]:
        cols[f"sma{p}"] = c.rolling(p).mean()

    # ── RSI (Wilder)
    def _rsi(s, n):
        d = s.diff()
        return 100 - 100 / (1 + _wilder_smooth(d.clip(lower=0), n) / _wilder_smooth((-d).clip(lower=0), n).replace(0, np.nan))
    for n in [7, 9, 14, 21]:
        cols[f"rsi{n}"] = _rsi(c, n)

    # ── MACD
    e12 = c.ewm(span=12, adjust=False).mean()
    e26 = c.ewm(span=26, adjust=False).mean()
    macd = e12 - e26
    sig  = macd.ewm(span=9, adjust=False).mean()
    cols["macd"] = macd; cols["macd_sig"] = sig; cols["macd_hist"] = macd - sig

    # ── Bollinger Bands
    for bb_n, bb_std in [(20, 2)]:
        s_n  = c.rolling(bb_n).mean()
        sd_n = c.rolling(bb_n).std(ddof=0)
        cols["bb_mid"]  = s_n
        cols["bb_up"]   = s_n + bb_std * sd_n
        cols["bb_lo"]   = s_n - bb_std * sd_n
        cols["bb_bw"]   = (cols["bb_up"] - cols["bb_lo"]) / s_n
        cols["bb_pctb"] = (c - cols["bb_lo"]) / (cols["bb_up"] - cols["bb_lo"])

    # ── True Range & ATR
    prev_c = c.shift(1)
    tr = pd.concat([(h-l), (h-prev_c).abs(), (l-prev_c).abs()], axis=1).max(axis=1)
    for n in [7, 14, 21]:
        cols[f"atr{n}"] = _wilder_smooth(tr, n)
    cols["atr14"]   = cols["atr14"]  # alias
    cols["atr_pct"] = cols["atr14"] / c * 100

    # ── ADX / +DI / -DI
    up = h.diff(); dn = -l.diff()
    pdm = pd.Series(np.where((up>dn)&(up>0), up, 0.0), index=idx)
    ndm = pd.Series(np.where((dn>up)&(dn>0), dn, 0.0), index=idx)
    atr14 = _wilder_smooth(tr, 14)
    dip   = 100 * _wilder_smooth(pdm, 14) / atr14.replace(0, np.nan)
    dim   = 100 * _wilder_smooth(ndm, 14) / atr14.replace(0, np.nan)
    dx    = (100 * (dip-dim).abs() / (dip+dim).replace(0, np.nan))
    cols["adx14"]   = _wilder_smooth(dx.fillna(0), 14)
    cols["di_plus"]  = dip
    cols["di_minus"] = dim

    # ── Stochastic %K and %D (14,3,3)
    low14  = l.rolling(14).min()
    high14 = h.rolling(14).max()
    stoch_k = 100 * (c - low14) / (high14 - low14).replace(0, np.nan)
    cols["stoch_k"] = stoch_k.rolling(3).mean()   # smoothed %K
    cols["stoch_d"] = cols["stoch_k"].rolling(3).mean()  # %D

    # ── CCI (20)
    tp = (h + l + c) / 3
    cci_sma = tp.rolling(20).mean()
    cci_mad = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cols["cci20"] = (tp - cci_sma) / (0.015 * cci_mad.replace(0, np.nan))

    # ── Williams %R (14)
    cols["willr14"] = -100 * (h.rolling(14).max() - c) / (h.rolling(14).max() - l.rolling(14).min()).replace(0, np.nan)

    # ── Supertrend (10, 3)
    atr10 = _wilder_smooth(tr, 10)
    hl2   = (h + l) / 2
    upper_band = hl2 + 3 * atr10
    lower_band = hl2 - 3 * atr10
    supertrend = pd.Series(np.nan, index=idx)
    direction  = pd.Series(1, index=idx)  # 1 = bullish, -1 = bearish
    for i in range(1, len(c)):
        prev_st  = supertrend.iloc[i-1] if not pd.isna(supertrend.iloc[i-1]) else lower_band.iloc[i]
        prev_dir = direction.iloc[i-1]
        if prev_dir == 1:
            cur_st = max(lower_band.iloc[i], prev_st) if c.iloc[i] > prev_st else upper_band.iloc[i]
            direction.iloc[i] = 1 if c.iloc[i] > cur_st else -1
        else:
            cur_st = min(upper_band.iloc[i], prev_st) if c.iloc[i] < prev_st else lower_band.iloc[i]
            direction.iloc[i] = -1 if c.iloc[i] < cur_st else 1
        supertrend.iloc[i] = cur_st
    cols["supertrend"]     = supertrend
    cols["supertrend_dir"] = direction  # 1=buy, -1=sell

    # ── VWAP (rolling 20-day)
    tp_v = (h + l + c) / 3
    cols["vwap20"] = (tp_v * v).rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)

    # ── Volume indicators
    avg_vol = v.rolling(20).mean()
    cols["avg_vol20"]  = avg_vol
    cols["vol_ratio"]  = v / avg_vol.replace(0, np.nan)
    cols["vol_ratio5"] = v / v.rolling(5).mean().replace(0, np.nan)
    cols["obv"]        = (np.sign(c.diff()) * v).fillna(0).cumsum()
    cols["pct_chg"]    = c.pct_change() * 100
    cols["pct_chg5"]   = c.pct_change(5) * 100
    cols["pct_chg20"]  = c.pct_change(20) * 100

    # ── N-day High / Low (Chartink-style: highest/lowest over N bars)
    for n in [5, 10, 20, 50, 52]:
        bars = n * 5 if n == 52 else n  # 52 weeks = 252 trading days approx
        if n == 52: bars = 252
        cols[f"high{n}d"]    = h.rolling(bars).max()
        cols[f"low{n}d"]     = l.rolling(bars).min()
        cols[f"pct_high{n}d"] = (c - cols[f"high{n}d"]) / cols[f"high{n}d"] * 100
        cols[f"pct_low{n}d"]  = (c - cols[f"low{n}d"])  / cols[f"low{n}d"]  * 100

    # ── 52-week (alias)
    cols["high52w"] = cols["high52d"]
    cols["low52w"]  = cols["low52d"]
    cols["pct52h"]  = cols["pct_high52d"]
    cols["pct52l"]  = cols["pct_low52d"]

    # ── Candle patterns
    rng = h - l
    cols["inside_bar"]  = (h <= h.shift(1)) & (l >= l.shift(1))
    cols["outside_bar"] = (h >= h.shift(1)) & (l <= l.shift(1))
    cols["nr4"] = rng <= rng.rolling(4).min().shift(1)
    cols["nr7"] = rng <= rng.rolling(7).min().shift(1)
    body = (c - o).abs()
    full = h - l
    cols["hammer"]          = (body / full.replace(0,np.nan) < 0.3) & ((c - l) / full.replace(0,np.nan) > 0.6)
    cols["shooting_star"]   = (body / full.replace(0,np.nan) < 0.3) & ((h - c) / full.replace(0,np.nan) > 0.6)
    cols["bullish_engulf"]  = (c > o) & (c.shift(1) < o.shift(1)) & (c > o.shift(1)) & (o < c.shift(1))
    cols["bearish_engulf"]  = (c < o) & (c.shift(1) > o.shift(1)) & (c < o.shift(1)) & (o > c.shift(1))
    cols["doji"]            = (body / full.replace(0,np.nan) < 0.1)

    # ── RS vs NIFTY
    if nifty_df is not None and not nifty_df.empty:
        nc = nifty_df["close"].reindex(idx, method="ffill")
        if c.iloc[0] > 0 and nc.iloc[0] > 0:
            rs = (c / c.iloc[0]) / (nc / nc.iloc[0])
            cols["rs_nifty"]   = rs
            cols["rs_nifty5d"] = rs.pct_change(5) * 100
            cols["rs_nifty20d"]= rs.pct_change(20) * 100
        else:
            cols["rs_nifty"] = cols["rs_nifty5d"] = cols["rs_nifty20d"] = np.nan
    else:
        cols["rs_nifty"] = cols["rs_nifty5d"] = cols["rs_nifty20d"] = np.nan

    # ── RS vs Sector
    if sector_df is not None and not sector_df.empty:
        sc = sector_df["close"].reindex(idx, method="ffill")
        if c.iloc[0] > 0 and sc.iloc[0] > 0:
            cols["rs_sector"] = (c / c.iloc[0]) / (sc / sc.iloc[0])
        else:
            cols["rs_sector"] = np.nan
    else:
        cols["rs_sector"] = np.nan

    return pd.DataFrame(cols, index=idx)

# ══════════════════════════════════════════════════════════════
#  SCANNER ENGINE
# ══════════════════════════════════════════════════════════════
OPS = {
    "gt":      lambda a,b: a > b,
    "lt":      lambda a,b: a < b,
    "gte":     lambda a,b: a >= b,
    "lte":     lambda a,b: a <= b,
    "eq":      lambda a,b: a == b,
    "x_above": lambda a,b: (a > b) & (a.shift() <= b.shift()),
    "x_below": lambda a,b: (a < b) & (a.shift() >= b.shift()),
}

def _rhs(df, cond):
    if cond.get("vt") == "ind" and cond.get("vi") and cond["vi"] in df.columns:
        return df[cond["vi"]]
    v = cond.get("val", "0")
    if v == "true":  return True
    if v == "false": return False
    try:    return float(v)
    except: return 0.0

def _eval(df, cond):
    ind = cond.get("ind", "close")
    if ind not in df.columns: return pd.Series(False, index=df.index)
    if cond.get("vt") == "bool": return df[ind].fillna(False).astype(bool)
    fn = OPS.get(cond.get("op", "gt"))
    if not fn: return pd.Series(False, index=df.index)
    try:
        r = fn(df[ind], _rhs(df, cond))
        return r.fillna(False) if isinstance(r, pd.Series) else pd.Series(bool(r), index=df.index)
    except:
        return pd.Series(False, index=df.index)

def _apply(df, conditions):
    if not conditions: return pd.Series(True, index=df.index)
    mask = _eval(df, conditions[0])
    for cond in conditions[1:]:
        cm = _eval(df, cond)
        mask = mask | cm if cond.get("lg","AND").upper() == "OR" else mask & cm
    return mask

def _setup(last) -> str:
    try:
        rsi = float(last.get("rsi14", 0) or 0)
        adx = float(last.get("adx14", 0) or 0)
        vr  = float(last.get("vol_ratio", 0) or 0)
        rs  = float(last.get("rs_nifty", 1) or 1)
        bw  = float(last.get("bb_bw", 0) or 0)
        chg = float(last.get("pct_chg", 0) or 0)
        cl  = float(last["close"])
        e20 = float(last.get("ema20", cl) or cl)
        e50 = float(last.get("ema50", cl) or cl)
        std = int(last.get("supertrend_dir", 1) or 1)
        if bw < 0.06 and cl > e20:                           return "BB Squeeze"
        if bool(last.get("nr7")) or bool(last.get("nr4")):   return "NR Breakout"
        if bool(last.get("inside_bar")) and adx > 20:        return "Inside Bar"
        if std == 1 and vr > 2.5 and chg > 1.5:             return "Breakout"
        if rs > 1.05 and rsi > 55 and cl > e20:             return "RS Leader"
        if rsi > 60 and adx > 25 and cl > e20 > e50:        return "Momentum"
        if std == 1 and cl > e20 and adx > 20:              return "Supertrend ↑"
        if cl > e20 and adx > 20:                           return "Continuation"
        return "Signal"
    except: return "Signal"

def _safe(last, col, dec=2):
    val = last.get(col, np.nan)
    try:
        f = float(val)
        return None if (f != f) else round(f, dec)
    except: return None

def scan_universe(symbols, conditions, nifty_df=None):
    results = []
    for sym in symbols:
        try:
            df = fetch_ohlcv(sym)
            if df.empty or len(df) < 30: continue
            df = compute_indicators(df, nifty_df)
            if not _apply(df, conditions).iloc[-1]: continue
            last = df.iloc[-1]
            meta = get_meta(sym)
            s = lambda col, dec=2: _safe(last, col, dec)
            results.append({
                "symbol":       sym,
                "name":         meta.get("name", sym),
                "sector":       meta.get("sector", "—"),
                "price":        s("close", 2),
                "change":       s("pct_chg", 2),
                "change5d":     s("pct_chg5", 2),
                "rsi14":        s("rsi14", 1),
                "adx14":        s("adx14", 1),
                "di_plus":      s("di_plus", 1),
                "di_minus":     s("di_minus", 1),
                "stoch_k":      s("stoch_k", 1),
                "stoch_d":      s("stoch_d", 1),
                "cci20":        s("cci20", 1),
                "willr14":      s("willr14", 1),
                "supertrend_dir": int(last.get("supertrend_dir", 0) or 0),
                "vol_ratio":    s("vol_ratio", 2),
                "rs_nifty":     s("rs_nifty", 3),
                "rs_nifty5d":   s("rs_nifty5d", 2),
                "bb_bw":        s("bb_bw", 4),
                "bb_pctb":      s("bb_pctb", 3),
                "atr_pct":      s("atr_pct", 2),
                "ema20":        s("ema20", 2),
                "ema50":        s("ema50", 2),
                "ema200":       s("ema200", 2),
                "pct52h":       s("pct52h", 2),
                "pct52l":       s("pct52l", 2),
                "high20d":      s("high20d", 2),
                "low20d":       s("low20d", 2),
                "macd_hist":    s("macd_hist", 3),
                "inside_bar":   bool(last.get("inside_bar", False)),
                "nr4":          bool(last.get("nr4", False)),
                "nr7":          bool(last.get("nr7", False)),
                "setup":        _setup(last),
            })
        except Exception as e:
            print(f"  [scan] {sym}: {e}"); continue
    return results

# ══════════════════════════════════════════════════════════════
#  BACKTESTER — FIXED: reads actual scan conditions per scanner
# ══════════════════════════════════════════════════════════════
def backtest(symbols, conditions, from_date, to_date,
             stop_pct=3.0, exit_days=8, exit_rule="After N Days",
             target_rr=2.0):
    """
    Proper event-driven backtest.
    - Uses the ACTUAL conditions from the scanner (not hardcoded)
    - Computes real entry/exit prices from historical data
    - Returns per-trade log + equity curve + stats
    """
    nifty_df = fetch_nifty("2y")
    trades   = []
    equity   = [{"date": from_date, "value": 100000.0}]
    capital  = 100000.0

    for sym in symbols[:40]:   # cap at 40 for performance
        try:
            df = fetch_ohlcv(sym, period="2y")
            if df.empty or len(df) < 60: continue

            df = compute_indicators(df, nifty_df)

            # Slice to backtest window
            df_bt = df.loc[from_date:to_date] if from_date in df.index or df.index[0] <= pd.Timestamp(from_date) else df
            try:
                df_bt = df.loc[from_date:to_date]
            except:
                continue
            if len(df_bt) < 10: continue

            # Find entry signals — day BEFORE so we enter at NEXT open
            mask        = _apply(df_bt, conditions)
            signal_days = df_bt.index[mask]

            for sig_dt in signal_days:
                sig_idx = df_bt.index.get_loc(sig_dt)
                # Enter at NEXT day's open (realistic execution)
                if sig_idx + 1 >= len(df_bt): continue
                entry_dt  = df_bt.index[sig_idx + 1]
                entry_px  = float(df_bt["open"].iloc[sig_idx + 1])
                if entry_px <= 0: continue

                sl_px     = entry_px * (1 - stop_pct / 100)
                target_px = entry_px * (1 + (stop_pct * target_rr) / 100)
                risk_amt  = capital * 0.02
                shares    = risk_amt / (entry_px - sl_px) if entry_px > sl_px else 0
                if shares <= 0: continue

                exit_px, exit_dt, exit_reason = None, None, "timeout"

                # Walk forward bar by bar
                future = df_bt.iloc[sig_idx + 2: sig_idx + 2 + exit_days]
                for fdt, row in future.iterrows():
                    lo = float(row["low"])
                    hi = float(row["high"])
                    cl = float(row["close"])
                    rsi = float(row.get("rsi14", 50) or 50)

                    # Check stop first (intrabar)
                    if lo <= sl_px:
                        exit_px, exit_dt, exit_reason = sl_px, fdt, "stop_loss"
                        break
                    # Check target
                    if hi >= target_px:
                        exit_px, exit_dt, exit_reason = target_px, fdt, "target"
                        break
                    # RSI exit rule
                    if exit_rule == "RSI Overbought (>70)" and rsi > 70:
                        exit_px, exit_dt, exit_reason = cl, fdt, "rsi_exit"
                        break
                    # EMA cross down
                    if exit_rule == "EMA Cross Down":
                        if cl < float(row.get("ema20", cl) or cl):
                            exit_px, exit_dt, exit_reason = cl, fdt, "ema_exit"
                            break

                # Timeout exit at last bar close
                if exit_px is None and len(future) > 0:
                    exit_px   = float(future["close"].iloc[-1])
                    exit_dt   = future.index[-1]
                    exit_reason = "timeout"
                if exit_px is None: continue

                pnl_pts  = exit_px - entry_px
                pnl_pct  = pnl_pts / entry_px * 100
                pnl_rs   = shares * pnl_pts
                rr_achvd = pnl_pct / stop_pct if pnl_pct > 0 else -(abs(pnl_pct) / stop_pct)
                capital += pnl_rs

                trades.append({
                    "date":        str(sig_dt.date()),
                    "entry_date":  str(entry_dt.date()),
                    "exit_date":   str(exit_dt.date()) if exit_dt else "",
                    "symbol":      sym,
                    "entry":       round(entry_px, 2),
                    "exit":        round(exit_px, 2),
                    "sl":          round(sl_px, 2),
                    "target":      round(target_px, 2),
                    "pnl_pct":     round(pnl_pct, 2),
                    "pnl_rs":      round(pnl_rs, 2),
                    "rr":          round(rr_achvd, 2),
                    "days":        (exit_dt - entry_dt).days if exit_dt else exit_days,
                    "result":      "WIN" if pnl_pct > 0 else "LOSS",
                    "exit_reason": exit_reason,
                })
                equity.append({
                    "date":  str(exit_dt.date() if exit_dt else entry_dt.date()),
                    "value": round(capital, 2)
                })

        except Exception as e:
            print(f"  [bt] {sym}: {e}"); continue

    # ── Stats
    wins   = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    wr     = len(wins) / len(trades) * 100 if trades else 0
    aw     = np.mean([t["pnl_pct"] for t in wins])   if wins   else 0
    al     = abs(np.mean([t["pnl_pct"] for t in losses])) if losses else 0
    ev     = (wr/100 * aw) - ((1 - wr/100) * al)
    rets   = pd.Series([t["pnl_pct"] for t in trades])
    sh     = round(rets.mean() / rets.std() * (252**0.5), 2) if len(rets) > 1 and rets.std() > 0 else 0
    eq_s   = pd.Series([e["value"] for e in equity])
    dd     = round(float(((eq_s - eq_s.cummax()) / eq_s.cummax() * 100).min()), 2) if len(eq_s) > 1 else 0
    pf     = sum(t["pnl_rs"] for t in wins) / abs(sum(t["pnl_rs"] for t in losses)) if losses and sum(t["pnl_rs"] for t in losses) != 0 else 0

    return trades, equity, {
        "total_trades":  len(trades),
        "wins":          len(wins),
        "losses":        len(losses),
        "win_rate":      round(wr, 1),
        "avg_win_pct":   round(aw, 2),
        "avg_loss_pct":  round(al, 2),
        "avg_rr":        round(np.mean([t["rr"] for t in trades]), 2) if trades else 0,
        "expectancy":    round(ev, 2),
        "profit_factor": round(pf, 2),
        "max_drawdown":  dd,
        "sharpe":        sh,
        "final_capital": round(capital, 2),
        "total_return":  round((capital - 100000) / 100000 * 100, 2),
        "total_pnl_rs":  round(sum(t["pnl_rs"] for t in trades), 2),
    }

# ══════════════════════════════════════════════════════════════
#  SECTOR RS HEATMAP
# ══════════════════════════════════════════════════════════════
SECTOR_TICKERS = {
    "NIFTY BANK":    "^NSEBANK",
    "NIFTY IT":      "^CNXIT",
    "NIFTY PHARMA":  "^CNXPHARMA",
    "NIFTY AUTO":    "^CNXAUTO",
    "NIFTY FMCG":    "^CNXFMCG",
    "NIFTY METAL":   "^CNXMETAL",
    "NIFTY ENERGY":  "^CNXENERGY",
    "NIFTY INFRA":   "^CNXINFRA",
    "NIFTY REALTY":  "^CNXREALTY",
    "NIFTY FINANCE": "^CNXFINANCE",
}

def compute_sector_rs(nifty_close, sector_close):
    """Normalized RS vs NIFTY, rebased to 100."""
    if nifty_close.iloc[0] <= 0 or sector_close.iloc[0] <= 0:
        return pd.Series(np.nan, index=sector_close.index)
    return (sector_close / sector_close.iloc[0]) / (nifty_close / nifty_close.iloc[0]) * 100

# ══════════════════════════════════════════════════════════════
#  API ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route("/api/status")
def status():
    try:
        df = _clean_df(yf.Ticker("RELIANCE.NS").history(period="3d", auto_adjust=True))
        if not df.empty:
            return jsonify({"live": True, "source": "Yahoo Finance / NSE",
                            "reliance_price": round(float(df["close"].iloc[-1]), 2)})
        return jsonify({"live": False, "reason": "Empty response"})
    except Exception as e:
        return jsonify({"live": False, "reason": str(e)})

@app.route("/api/universe")
def get_universe_api():
    return jsonify({k: len(v) for k, v in UNIVERSES.items()})

@app.route("/api/universe/fetch", methods=["POST"])
def trigger_universe_fetch():
    """Trigger a background universe refresh from NSE."""
    try:
        syms = fetch_full_nse_universe()
        universes = _build_universes(syms)
        # Save to cache
        with open(_universe_cache_file, "w") as f:
            json.dump({"all_symbols": syms, "metadata": STOCK_META,
                       "by_index": {k: v for k,v in universes.items()}, "total": len(syms)}, f)
        global UNIVERSES, _ALL_SYMBOLS
        UNIVERSES, _ALL_SYMBOLS = universes, syms
        return jsonify({"total": len(syms), "message": "Universe updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sector/heatmap")
def sector_heatmap():
    """Returns sector RS data for heatmap visualization."""
    try:
        period = request.args.get("period", "3mo")
        nifty  = fetch_nifty(period)
        if nifty.empty:
            return jsonify({"error": "Could not fetch NIFTY data"}), 500

        result = []
        for sector_name, ticker in SECTOR_TICKERS.items():
            try:
                sec_df = fetch_sector_index(ticker, period)
                if sec_df.empty: raise ValueError("empty")
                nc = nifty["close"].reindex(sec_df.index, method="ffill")
                rs = compute_sector_rs(nc, sec_df["close"])

                rs_now   = round(float(rs.iloc[-1]), 2)
                rs_1w    = round(float(rs.pct_change(5).iloc[-1] * 100), 2) if len(rs) > 5 else 0
                rs_1m    = round(float(rs.pct_change(20).iloc[-1] * 100), 2) if len(rs) > 20 else 0
                chg_1d   = round(float(sec_df["close"].pct_change().iloc[-1] * 100), 2)
                close    = round(float(sec_df["close"].iloc[-1]), 2)

                result.append({
                    "sector":   sector_name,
                    "ticker":   ticker,
                    "close":    close,
                    "chg_1d":   chg_1d,
                    "rs_now":   rs_now,
                    "rs_1w":    rs_1w,
                    "rs_1m":    rs_1m,
                    "trend":    "UP" if rs_1w > 0 and rs_1m > 0 else "DOWN" if rs_1w < 0 and rs_1m < 0 else "MIXED",
                })
            except Exception as e:
                # Fallback: compute RS from top stocks in sector
                sector_syms = SECTORS.get(sector_name, [])[:5]
                closes = []
                for s in sector_syms:
                    sdf = fetch_ohlcv(s, period=period)
                    if not sdf.empty: closes.append(sdf["close"])
                if closes:
                    avg = pd.concat(closes, axis=1).mean(axis=1)
                    nc2 = nifty["close"].reindex(avg.index, method="ffill")
                    rs2 = compute_sector_rs(nc2, avg)
                    result.append({
                        "sector":   sector_name,
                        "ticker":   ticker,
                        "close":    round(float(avg.iloc[-1]), 2),
                        "chg_1d":   round(float(avg.pct_change().iloc[-1] * 100), 2),
                        "rs_now":   round(float(rs2.iloc[-1]), 2),
                        "rs_1w":    round(float(rs2.pct_change(5).iloc[-1] * 100), 2) if len(rs2) > 5 else 0,
                        "rs_1m":    round(float(rs2.pct_change(20).iloc[-1] * 100), 2) if len(rs2) > 20 else 0,
                        "trend":    "MIXED",
                    })

        result.sort(key=lambda x: x["rs_now"], reverse=True)
        return jsonify({"sectors": result, "period": period, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/market/regime")
def market_regime():
    try:
        df   = compute_indicators(fetch_nifty("3mo"))
        last = df.iloc[-1]
        cl   = float(last["close"]); e20 = float(last["ema20"]); e50 = float(last["ema50"])
        adx  = float(last.get("adx14", 0) or 0); pct = float(last.get("pct_chg", 0) or 0)
        std  = int(last.get("supertrend_dir", 1) or 1)
        if   cl > e20 > e50 and adx > 25 and std == 1: regime = "STRONG BULL"
        elif cl > e20 and adx > 20 and std == 1:        regime = "BULL"
        elif cl < e20 < e50 and adx > 25 and std == -1: regime = "STRONG BEAR"
        elif cl < e20 and std == -1:                    regime = "BEAR"
        else:                                           regime = "SIDEWAYS"
        return jsonify({"regime": regime, "nifty_close": round(cl, 2),
                        "nifty_change": round(pct, 2), "ema20": round(e20, 2),
                        "ema50": round(e50, 2), "adx": round(adx, 2),
                        "supertrend": "BULLISH" if std == 1 else "BEARISH"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/validate/<symbol>")
def validate_indicators(symbol):
    try:
        df = compute_indicators(fetch_ohlcv(symbol, "1y"), fetch_nifty("1y"))
        if df.empty: return jsonify({"error": f"No data for {symbol}"}), 404
        rows = []
        for dt, row in df.tail(3).iterrows():
            s = lambda c, d=2: _safe(row, c, d)
            rows.append({
                "date": str(dt.date()), "close": s("close"), "rsi14": s("rsi14"),
                "adx14": s("adx14"), "macd": s("macd", 4), "bb_bw": s("bb_bw", 4),
                "stoch_k": s("stoch_k"), "cci20": s("cci20"), "atr14": s("atr14"),
                "supertrend_dir": int(row.get("supertrend_dir", 0) or 0),
                "rs_nifty": s("rs_nifty", 4), "high20d": s("high20d"), "low20d": s("low20d"),
            })
        return jsonify({"symbol": symbol, "last_3_days": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Scans CRUD ────────────────────────────────────────────────
@app.route("/api/scans", methods=["GET"])
def get_scans():
    conn = get_db()
    rows = conn.execute("SELECT * FROM scans ORDER BY id DESC").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route("/api/scans", methods=["POST"])
def create_scan():
    d = request.json; conn = get_db()
    cur = conn.execute(
        "INSERT INTO scans (name,desc,uni,tf,color,conds,created) VALUES (?,?,?,?,?,?,?)",
        (d["name"], d.get("desc",""), d.get("uni","NIFTY 200"), d.get("tf","Daily"),
         d.get("color","#00D68F"), json.dumps(d.get("conditions",[])), datetime.now().isoformat()))
    conn.commit(); sid = cur.lastrowid; conn.close()
    return jsonify({"id": sid, "message": "Scan saved"})

@app.route("/api/scans/<int:sid>", methods=["PUT"])
def update_scan(sid):
    d = request.json; conn = get_db()
    conn.execute("UPDATE scans SET name=?,desc=?,uni=?,tf=?,color=?,conds=? WHERE id=?",
        (d["name"], d.get("desc",""), d.get("uni"), d.get("tf"),
         d.get("color"), json.dumps(d.get("conditions",[])), sid))
    conn.commit(); conn.close()
    return jsonify({"message": "Scan updated"})

@app.route("/api/scans/<int:sid>", methods=["DELETE"])
def delete_scan(sid):
    conn = get_db()
    conn.execute("DELETE FROM scans WHERE id=?", (sid,))
    conn.commit(); conn.close()
    return jsonify({"message": "Scan deleted"})

@app.route("/api/scan/run", methods=["POST"])
def run_scan():
    try:
        d        = request.json
        symbols  = get_symbols(d.get("universe", "NIFTY 50"))
        nifty_df = fetch_nifty("1y")
        results  = scan_universe(symbols, d.get("conditions", []), nifty_df)
        if d.get("scan_id"):
            conn = get_db()
            conn.execute("UPDATE scans SET last_run=?,cnt=? WHERE id=?",
                (datetime.now().strftime("%d %b, %H:%M"), len(results), d["scan_id"]))
            conn.commit(); conn.close()
        return jsonify({"results": results, "count": len(results),
                        "universe": d.get("universe"), "total_scanned": len(symbols)})
    except Exception as e:
        traceback.print_exc(); return jsonify({"error": str(e)}), 500

@app.route("/api/backtest/run", methods=["POST"])
def run_backtest():
    try:
        d          = request.json
        conditions = []
        universe   = "NIFTY 50"

        # Load conditions from the selected scan — this is what was broken before
        if d.get("scan_id"):
            conn = get_db()
            row  = conn.execute("SELECT * FROM scans WHERE id=?", (d["scan_id"],)).fetchone()
            conn.close()
            if row:
                conditions = json.loads(row["conds"])
                universe   = row["uni"]
                print(f"  [bt] Loaded {len(conditions)} conditions from scan '{row['name']}'")
            else:
                return jsonify({"error": "Scan not found"}), 404
        else:
            # Allow passing conditions directly
            conditions = d.get("conditions", [])
            universe   = d.get("universe", "NIFTY 50")

        if not conditions:
            return jsonify({"error": "No conditions found — save the scan first before backtesting"}), 400

        symbols = get_symbols(universe)
        trades, equity, stats = backtest(
            symbols, conditions,
            d.get("from", "2024-01-01"),
            d.get("to", datetime.now().strftime("%Y-%m-%d")),
            float(d.get("stop_loss", 3)),
            int(d.get("exit_days", 8)),
            d.get("exit_rule", "After N Days"),
            float(d.get("min_rr", 2.0)),
        )
        return jsonify({"trades": trades, "equity": equity, "stats": stats})
    except Exception as e:
        traceback.print_exc(); return jsonify({"error": str(e)}), 500

# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    init_db()
    print("\n  QuantEdge NSE Backend  v4")
    print("  ──────────────────────────")
    print(f"  Universe: {sum(len(v) for v in UNIVERSES.values())} slots across {len(UNIVERSES)} indices")
    print("  Running at:  http://localhost:5000")
    print("  Sector map:  http://localhost:5000/api/sector/heatmap")
    print("  Universe:    http://localhost:5000/api/universe\n")
    app.run(debug=True, port=5000)
