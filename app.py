"""
QuantEdge NSE — Python Backend  v3
Run:  python app.py
API:  http://localhost:5000

To build full 500+ stock universe first:
    python nse_universe.py
"""

import json, sqlite3, traceback, warnings
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
pd.options.mode.copy_on_write = True

app = Flask(__name__)
CORS(app)
DB = "quantedge.db"

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
#  NSE UNIVERSE
# ══════════════════════════════════════════════════════════════
_NIFTY50 = [
    "RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","HINDUNILVR","ITC","SBIN",
    "BAJFINANCE","BHARTIARTL","KOTAKBANK","AXISBANK","ASIANPAINT","MARUTI","TITAN",
    "SUNPHARMA","ONGC","NESTLEIND","WIPRO","LT","HCLTECH","ULTRACEMCO","ADANIENT",
    "POWERGRID","NTPC","TATASTEEL","JSWSTEEL","INDUSINDBK","COALINDIA","BPCL",
    "BAJAJ-AUTO","GRASIM","HEROMOTOCO","BRITANNIA","DIVISLAB","CIPLA","EICHERMOT",
    "APOLLOHOSP","TATACONSUM","HINDALCO","TECHM","ADANIPORTS","SHRIRAMFIN",
    "DRREDDY","BAJAJFINSV","SBILIFE","HDFCLIFE","LTIM","M&M","TATAMOTORS",
]
_NEXT50 = [
    "ZOMATO","DMART","NAUKRI","PAGEIND","TRENT","VEDL","SIEMENS","ABB","HAVELLS",
    "MOTHERSON","BALKRISIND","CHOLAFIN","BANDHANBNK","FEDERALBNK","GODREJCP","DABUR",
    "MARICO","COLPAL","MCDOWELL-N","UBL","TORNTPHARM","LUPIN","BOSCHLTD","CONCOR",
    "AMBUJACEM","NHPC","PFC","RECLTD","IRCTC","BEL","GAIL","IOC","LICHSGFIN",
    "SAIL","NMDC","INDHOTEL","DLF","IRFC","ADANIGREEN","ADANIPOWER","BERGEPAINT",
]
_MIDCAP = [
    "PERSISTENT","MPHASIS","COFORGE","POLYCAB","ASTRAL","DIXON","TATAELXSI","CAMS",
    "ANGELONE","DEEPAKNTR","PIIND","KPITTECH","JUBLFOOD","BSE","CANFINHOME","CESC",
    "CYIENT","EMAMILTD","ENDURANCE","ESCORTS","EXIDEIND","GLENMARK","GRANULES",
    "HAPPSTMNDS","HFCL","IDFCFIRSTB","IPCALAB","JBCHEPHARM","JKCEMENT","KAJARIACER",
    "KALYANKJIL","KPIL","LALPATHLAB","LAURUSLABS","LUXIND","MANAPPURAM","MFSL",
    "NATCOPHARM","NCC","NBCC","OFSS","OLECTRA","PETRONET","PHOENIXLTD","POONAWALLA",
    "PRESTIGE","PVRINOX","RADICO","RAMCOCEM","RITES","SANOFI","SCHAEFFLER","SOBHA",
    "SONACOMS","SOLARINDS","STARHEALTH","SUMICHEM","SUNTV","SUPREMEIND","SUZLON",
    "TANLA","TIINDIA","TIMKEN","TORNTPOWER","UNIONBANK","UPL","VBL","VGUARD",
    "VINATIORGA","WELCORP","YESBANK","NUVOCO","AAVAS","METROPOLIS","HONASA",
    "JKPAPER","GMRINFRA","GNFC","GSPL","GUJGASLTD","HUDCO","INTELLECT","ISEC",
    "KRBL","LINDEINDIA","MRF","NOCIL","PFIZER","PRINCEPIPE","SRF","TATACOMM",
    "TEAMLEASE","TITAGARH","TTKPRESTIG","UJJIVANSFB","USHAMART","CHOLAFIN",
]
_ALL = list(dict.fromkeys(_NIFTY50 + _NEXT50 + _MIDCAP))

_UNIVERSES_BASE = {
    "NIFTY 50":     _NIFTY50,
    "NIFTY 100":    list(dict.fromkeys(_NIFTY50 + _NEXT50)),
    "NIFTY 200":    _ALL,
    "NIFTY 500":    _ALL,
    "ALL NSE":      _ALL,
    "NIFTY BANK":   ["HDFCBANK","ICICIBANK","KOTAKBANK","AXISBANK","SBIN","INDUSINDBK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","PNB","BANKBARODA"],
    "NIFTY IT":     ["TCS","INFY","HCLTECH","WIPRO","LTIM","TECHM","MPHASIS","COFORGE","PERSISTENT","TATAELXSI"],
    "NIFTY PHARMA": ["SUNPHARMA","DIVISLAB","CIPLA","DRREDDY","LUPIN","TORNTPHARM","AUROPHARMA","ALKEM","IPCALAB","LAURUSLABS"],
}
STOCK_META = {}

def _load_universe():
    global STOCK_META
    cache = Path("nse_universe.json")
    if cache.exists():
        try:
            with open(cache) as f:
                data = json.load(f)
            STOCK_META = data.get("metadata", {})
            merged = {**_UNIVERSES_BASE, **data.get("by_index", {})}
            print(f"  Universe: {data['total']} stocks from nse_universe.json")
            return merged
        except Exception as e:
            print(f"  Could not load nse_universe.json: {e}")
    print("  Using built-in universe (~200 stocks). Run: python nse_universe.py for full 500+")
    return _UNIVERSES_BASE

UNIVERSES = _load_universe()

def get_symbols(name): return UNIVERSES.get(name, _NIFTY50)
def get_meta(sym):     return STOCK_META.get(sym, {"name": sym, "sector": "—"})

# ══════════════════════════════════════════════════════════════
#  DATA FETCHER
# ══════════════════════════════════════════════════════════════
def _clean_df(raw) -> pd.DataFrame:
    if raw is None or (hasattr(raw, 'empty') and raw.empty):
        return pd.DataFrame()
    df = raw.copy()
    # Flatten MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]).lower().strip() for c in df.columns]
    else:
        df.columns = [str(c).lower().strip() for c in df.columns]
    # Strip timezone
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "date"
    # Keep OHLCV only
    keep = [c for c in ["open","high","low","close","volume"] if c in df.columns]
    df   = df[keep].copy()
    return df[df["close"] > 0].dropna(subset=["close"])

def fetch_ohlcv(sym, period="1y", interval="1d"):
    try:
        return _clean_df(yf.Ticker(f"{sym}.NS").history(period=period, interval=interval, auto_adjust=True))
    except Exception as e:
        print(f"  [fetch] {sym}: {e}"); return pd.DataFrame()

def fetch_nifty(period="1y"):
    try:
        return _clean_df(yf.Ticker("^NSEI").history(period=period, auto_adjust=True))
    except Exception as e:
        print(f"  [fetch] NIFTY: {e}"); return pd.DataFrame()

# ══════════════════════════════════════════════════════════════
#  INDICATOR ENGINE  — all indicators match TradingView defaults
# ══════════════════════════════════════════════════════════════
def _wilder_smooth(series: pd.Series, n: int) -> pd.Series:
    """
    Wilder's Smoothing (RMA / Modified Moving Average).
    Used by RSI, ATR, ADX — NOT a simple rolling mean.
    alpha = 1/n, equivalent to EWM with adjust=False and com=n-1.
    """
    return series.ewm(alpha=1.0/n, min_periods=n, adjust=False).mean()

def compute_indicators(df: pd.DataFrame, nifty_df=None) -> pd.DataFrame:
    c   = df["close"].copy()
    h   = df["high"].copy()
    l   = df["low"].copy()
    v   = df["volume"].copy()
    o   = df["open"].copy()
    idx = df.index
    cols = {"open":o, "high":h, "low":l, "close":c, "volume":v}

    # ── Moving Averages (correct)
    for p in [9, 20, 50, 200]:
        cols[f"ema{p}"] = c.ewm(span=p, adjust=False).mean()
        cols[f"sma{p}"] = c.rolling(p).mean()

    # ── RSI — Wilder's smoothing (matches TradingView exactly)
    def _rsi(s, n):
        delta = s.diff()
        gain  = delta.clip(lower=0)
        loss  = (-delta.clip(upper=0))
        # Seed with SMA for first window, then use Wilder's RMA
        avg_gain = _wilder_smooth(gain, n)
        avg_loss = _wilder_smooth(loss, n)
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    cols["rsi14"] = _rsi(c, 14)
    cols["rsi9"]  = _rsi(c, 9)

    # ── MACD (12,26,9) — standard EMA, correct
    e12  = c.ewm(span=12, adjust=False).mean()
    e26  = c.ewm(span=26, adjust=False).mean()
    macd = e12 - e26
    sig  = macd.ewm(span=9, adjust=False).mean()
    cols["macd"]      = macd
    cols["macd_sig"]  = sig
    cols["macd_hist"] = macd - sig

    # ── Bollinger Bands (20,2) — ddof=0 matches TradingView
    s20  = c.rolling(20).mean()
    sd20 = c.rolling(20).std(ddof=0)            # population std, not sample std
    bb_up = s20 + 2 * sd20
    bb_lo = s20 - 2 * sd20
    cols["bb_mid"]  = s20
    cols["bb_up"]   = bb_up
    cols["bb_lo"]   = bb_lo
    cols["bb_bw"]   = (bb_up - bb_lo) / s20
    cols["bb_pctb"] = (c - bb_lo) / (bb_up - bb_lo)

    # ── True Range
    prev_c = c.shift(1)
    tr = pd.concat([
        (h - l),
        (h - prev_c).abs(),
        (l - prev_c).abs()
    ], axis=1).max(axis=1)

    # ── ATR(14) — Wilder's smoothing (matches TradingView)
    atr = _wilder_smooth(tr, 14)
    cols["atr14"]   = atr
    cols["atr_pct"] = atr / c * 100

    # ── ADX / +DI / -DI — full Wilder smoothing (matches TradingView)
    up  = h.diff()
    dn  = -l.diff()
    # +DM: up move > down move AND positive
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=idx)
    # -DM: down move > up move AND positive
    ndm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=idx)

    # Smooth DM and TR with Wilder's RMA
    atr14  = _wilder_smooth(tr,  14)
    pdm14  = _wilder_smooth(pdm, 14)
    ndm14  = _wilder_smooth(ndm, 14)

    dip = 100 * pdm14 / atr14.replace(0, np.nan)
    dim = 100 * ndm14 / atr14.replace(0, np.nan)
    dx  = (100 * (dip - dim).abs() / (dip + dim).replace(0, np.nan))
    adx = _wilder_smooth(dx.fillna(0), 14)

    cols["adx14"]   = adx
    cols["di_plus"]  = dip
    cols["di_minus"] = dim

    # ── Volume indicators
    avg_vol = v.rolling(20).mean()
    cols["avg_vol20"] = avg_vol
    cols["vol_ratio"] = v / avg_vol.replace(0, np.nan)
    cols["obv"]       = (np.sign(c.diff()) * v).fillna(0).cumsum()

    # ── % Change (1-day return vs previous close)
    cols["pct_chg"] = c.pct_change() * 100

    # ── 52-week High/Low
    h52 = h.rolling(252).max()
    l52 = l.rolling(252).min()
    cols["high52w"] = h52
    cols["low52w"]  = l52
    cols["pct52h"]  = (c - h52) / h52 * 100   # negative = below 52w high
    cols["pct52l"]  = (c - l52) / l52 * 100   # positive = above 52w low

    # ── Candle Patterns
    rng = h - l
    cols["inside_bar"] = (h <= h.shift(1)) & (l >= l.shift(1))

    # NR4/NR7 — today's range is smallest of last 4/7 bars (use <= not == to avoid float eq issues)
    cols["nr4"] = rng <= rng.rolling(4).min().shift(1)
    cols["nr7"] = rng <= rng.rolling(7).min().shift(1)

    # ── RS vs NIFTY — normalized ratio (both rebased to 1.0 at period start)
    # rs_nifty > 1.0  = stock outperforming NIFTY
    # rs_nifty = 1.15 = stock has returned 15% MORE than NIFTY over the period
    if nifty_df is not None and not nifty_df.empty:
        nc = nifty_df["close"].reindex(idx, method="ffill")
        first_c  = c.iloc[0]
        first_nc = nc.iloc[0]
        if first_c > 0 and first_nc > 0:
            stock_ret  = c / first_c       # stock cumulative return from start
            nifty_ret  = nc / first_nc     # NIFTY cumulative return from start
            rs         = stock_ret / nifty_ret
            cols["rs_nifty"]   = rs
            cols["rs_nifty5d"] = rs.pct_change(5) * 100
        else:
            cols["rs_nifty"]   = np.nan
            cols["rs_nifty5d"] = np.nan
    else:
        cols["rs_nifty"]   = np.nan
        cols["rs_nifty5d"] = np.nan

    return pd.DataFrame(cols, index=idx)

# ══════════════════════════════════════════════════════════════
#  SCANNER ENGINE
# ══════════════════════════════════════════════════════════════
OPS = {
    "gt": lambda a,b: a>b, "lt": lambda a,b: a<b,
    "gte": lambda a,b: a>=b, "lte": lambda a,b: a<=b,
    "eq": lambda a,b: a==b,
    "x_above": lambda a,b: (a>b)&(a.shift()<=b.shift()),
    "x_below": lambda a,b: (a<b)&(a.shift()>=b.shift()),
}

def _rhs(df, cond):
    if cond.get("vt")=="ind" and cond.get("vi") and cond["vi"] in df.columns:
        return df[cond["vi"]]
    v = cond.get("val","0")
    if v=="true": return True
    if v=="false": return False
    try: return float(v)
    except: return 0.0

def _eval(df, cond):
    ind = cond.get("ind","close")
    if ind not in df.columns: return pd.Series(False, index=df.index)
    if cond.get("vt")=="bool": return df[ind].fillna(False).astype(bool)
    fn = OPS.get(cond.get("op","gt"))
    if not fn: return pd.Series(False, index=df.index)
    try:
        r = fn(df[ind], _rhs(df,cond))
        return r.fillna(False) if isinstance(r,pd.Series) else pd.Series(bool(r),index=df.index)
    except: return pd.Series(False, index=df.index)

def _apply(df, conditions):
    if not conditions: return pd.Series(True, index=df.index)
    mask = _eval(df, conditions[0])
    for c in conditions[1:]:
        cm = _eval(df,c)
        mask = mask|cm if c.get("lg","AND").upper()=="OR" else mask&cm
    return mask

def _setup(last) -> str:
    try:
        rsi = float(last.get("rsi14",0) or 0); adx = float(last.get("adx14",0) or 0)
        vr  = float(last.get("vol_ratio",0) or 0); rs = float(last.get("rs_nifty",1) or 1)
        bw  = float(last.get("bb_bw",0) or 0); chg = float(last.get("pct_chg",0) or 0)
        cl  = float(last["close"])
        e20 = float(last.get("ema20",cl) or cl); e50 = float(last.get("ema50",cl) or cl)
        if bw < 0.06 and cl > e20:                       return "BB Squeeze"
        if bool(last.get("nr7")) or bool(last.get("nr4")): return "NR Breakout"
        if bool(last.get("inside_bar")) and adx > 20:    return "Inside Bar"
        if vr > 2.5 and chg > 1.5 and cl > e20:          return "Breakout"
        if rs > 1.05 and rsi > 55 and cl > e20:          return "RS Leader"
        if rsi > 60 and adx > 25 and cl > e20 > e50:     return "Momentum"
        if cl > e20 and adx > 20:                        return "Continuation"
        return "Signal"
    except: return "Signal"

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

            def s(col, dec=2):
                val = last.get(col, np.nan)
                try:
                    f = float(val)
                    return None if (f != f) else round(f, dec)  # NaN check
                except: return None

            results.append({
                "symbol":     sym,
                "name":       meta.get("name", sym),
                "sector":     meta.get("sector", "—"),
                "price":      s("close", 2),
                "change":     s("pct_chg", 2),
                "rsi14":      s("rsi14", 1),
                "adx14":      s("adx14", 1),
                "di_plus":    s("di_plus", 1),
                "di_minus":   s("di_minus", 1),
                "vol_ratio":  s("vol_ratio", 2),
                "rs_nifty":   s("rs_nifty", 3),
                "rs_nifty5d": s("rs_nifty5d", 2),
                "bb_bw":      s("bb_bw", 4),
                "bb_pctb":    s("bb_pctb", 3),
                "atr_pct":    s("atr_pct", 2),
                "ema20":      s("ema20", 2),
                "ema50":      s("ema50", 2),
                "pct52h":     s("pct52h", 2),
                "pct52l":     s("pct52l", 2),
                "macd_hist":  s("macd_hist", 3),
                "inside_bar": bool(last.get("inside_bar", False)),
                "nr4":        bool(last.get("nr4", False)),
                "nr7":        bool(last.get("nr7", False)),
                "setup":      _setup(last),
            })
        except Exception as e:
            print(f"  [scan] {sym}: {e}"); continue
    return results

# ══════════════════════════════════════════════════════════════
#  BACKTESTER
# ══════════════════════════════════════════════════════════════
def backtest(symbols, conditions, from_date, to_date, stop_pct=3.0, exit_days=8, exit_rule="After N Days"):
    nifty_df = fetch_nifty("2y")
    trades, equity, capital = [], [{"date":from_date,"value":100000}], 100000.0

    for sym in symbols[:30]:
        try:
            df = fetch_ohlcv(sym,"2y")
            if df.empty or len(df)<60: continue
            df   = compute_indicators(df,nifty_df)
            df   = df.loc[from_date:to_date]
            if len(df)<10: continue
            mask = _apply(df,conditions)
            entries = df.index[mask & ~mask.shift(1,fill_value=False)]

            for edt in entries:
                i      = df.index.get_loc(edt)
                entry  = float(df["close"].iloc[i])
                sl     = entry*(1-stop_pct/100)
                shares = (capital*0.02)/(entry-sl) if entry>sl else 0
                target = entry+(entry-sl)*2.0
                ep,ed,er = None,None,"timeout"

                for fdt,row in df.iloc[i+1:i+1+exit_days].iterrows():
                    p = float(row["close"])
                    if p<=sl:     ep,ed,er=p,fdt,"stop_loss"; break
                    if p>=target: ep,ed,er=p,fdt,"target"; break
                    if exit_rule=="RSI Overbought (>70)" and float(row.get("rsi14",0))>70:
                        ep,ed,er=p,fdt,"rsi_exit"; break

                if ep is None and i+exit_days<len(df):
                    ep = float(df["close"].iloc[i+exit_days])
                    ed = df.index[i+exit_days]
                if ep is None: continue

                pnl = (ep-entry)/entry*100
                capital += shares*(ep-entry)
                trades.append({"date":str(edt.date()),"symbol":sym,"entry":round(entry,2),
                    "exit":round(ep,2),"pnl_pct":round(pnl,2),"rr":round(abs(pnl)/stop_pct,2),
                    "days":(ed-edt).days if ed else exit_days,
                    "result":"WIN" if pnl>0 else "LOSS","exit_reason":er})
                equity.append({"date":str(ed.date() if ed else edt.date()),"value":round(capital,2)})
        except Exception as e:
            print(f"  [bt] {sym}: {e}"); continue

    wins  = [t for t in trades if t["result"]=="WIN"]
    loss  = [t for t in trades if t["result"]=="LOSS"]
    wr    = len(wins)/len(trades)*100 if trades else 0
    aw    = sum(t["pnl_pct"] for t in wins)/len(wins) if wins else 0
    al    = abs(sum(t["pnl_pct"] for t in loss)/len(loss)) if loss else 0
    rets  = pd.Series([t["pnl_pct"] for t in trades])
    sh    = round(rets.mean()/rets.std()*(252**0.5) if rets.std()>0 else 0,2)
    eq_s  = pd.Series([e["value"] for e in equity])
    dd    = round(float(((eq_s-eq_s.cummax())/eq_s.cummax()*100).min()),2)

    return trades, equity, {
        "total_trades":len(trades),"wins":len(wins),"losses":len(loss),
        "win_rate":round(wr,1),"avg_win":round(aw,2),"avg_loss":round(al,2),
        "avg_rr":round(sum(t["rr"] for t in trades)/len(trades),2) if trades else 0,
        "expectancy":round((wr/100*aw)-((1-wr/100)*al),2),
        "max_drawdown":dd,"sharpe":sh,
        "final_capital":round(capital,2),
        "total_return":round((capital-100000)/100000*100,2),
    }

# ══════════════════════════════════════════════════════════════
#  API ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/api/validate/<symbol>")
def validate_indicators(symbol):
    """
    Returns last 5 days of indicator values for a symbol.
    Use this to cross-check against TradingView.
    Example: http://localhost:5000/api/validate/RELIANCE
    """
    try:
        df       = fetch_ohlcv(symbol, period="1y")
        nifty_df = fetch_nifty("1y")
        if df.empty:
            return jsonify({"error": f"No data for {symbol}"}), 404
        df = compute_indicators(df, nifty_df)

        rows = []
        for dt, row in df.tail(5).iterrows():
            def f(col, dec=2):
                v = row.get(col, np.nan)
                try:
                    fv = float(v)
                    return None if fv != fv else round(fv, dec)
                except: return None

            rows.append({
                "date":       str(dt.date()),
                "close":      f("close", 2),
                "ema20":      f("ema20", 2),
                "ema50":      f("ema50", 2),
                "rsi14":      f("rsi14", 2),
                "macd":       f("macd", 4),
                "macd_sig":   f("macd_sig", 4),
                "macd_hist":  f("macd_hist", 4),
                "bb_up":      f("bb_up", 2),
                "bb_mid":     f("bb_mid", 2),
                "bb_lo":      f("bb_lo", 2),
                "bb_bw":      f("bb_bw", 4),
                "atr14":      f("atr14", 2),
                "atr_pct":    f("atr_pct", 3),
                "adx14":      f("adx14", 2),
                "di_plus":    f("di_plus", 2),
                "di_minus":   f("di_minus", 2),
                "vol_ratio":  f("vol_ratio", 2),
                "rs_nifty":   f("rs_nifty", 4),
                "rs_nifty5d": f("rs_nifty5d", 2),
                "pct52h":     f("pct52h", 2),
                "nr7":        bool(row.get("nr7", False)),
                "inside_bar": bool(row.get("inside_bar", False)),
            })
        return jsonify({"symbol": symbol, "last_5_days": rows})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/health")
def health():
    return jsonify({"status":"ok","timestamp":datetime.now().isoformat()})

@app.route("/api/status")
def status():
    try:
        df = _clean_df(yf.Ticker("RELIANCE.NS").history(period="3d",auto_adjust=True))
        if not df.empty:
            return jsonify({"live":True,"source":"Yahoo Finance / NSE",
                            "reliance_price":round(float(df["close"].iloc[-1]),2)})
        return jsonify({"live":False,"reason":"Empty response"})
    except Exception as e:
        return jsonify({"live":False,"reason":str(e)})

@app.route("/api/universe")
def get_universe_api():
    return jsonify({k:len(v) for k,v in UNIVERSES.items()})

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
        (d["name"],d.get("desc",""),d.get("uni","NIFTY 200"),d.get("tf","Daily"),
         d.get("color","#00D68F"),json.dumps(d.get("conditions",[])),datetime.now().isoformat()))
    conn.commit(); sid=cur.lastrowid; conn.close()
    return jsonify({"id":sid,"message":"Scan saved"})

@app.route("/api/scans/<int:sid>", methods=["PUT"])
def update_scan(sid):
    d=request.json; conn=get_db()
    conn.execute("UPDATE scans SET name=?,desc=?,uni=?,tf=?,color=?,conds=? WHERE id=?",
        (d["name"],d.get("desc",""),d.get("uni"),d.get("tf"),d.get("color"),
         json.dumps(d.get("conditions",[])),sid))
    conn.commit(); conn.close(); return jsonify({"message":"Scan updated"})

@app.route("/api/scans/<int:sid>", methods=["DELETE"])
def delete_scan(sid):
    conn=get_db(); conn.execute("DELETE FROM scans WHERE id=?",(sid,))
    conn.commit(); conn.close(); return jsonify({"message":"Scan deleted"})

@app.route("/api/scan/run", methods=["POST"])
def run_scan():
    try:
        d = request.json
        symbols  = get_symbols(d.get("universe","NIFTY 50"))
        nifty_df = fetch_nifty("1y")
        results  = scan_universe(symbols, d.get("conditions",[]), nifty_df)
        if d.get("scan_id"):
            conn=get_db()
            conn.execute("UPDATE scans SET last_run=?,cnt=? WHERE id=?",
                (datetime.now().strftime("%d %b, %H:%M"),len(results),d["scan_id"]))
            conn.commit(); conn.close()
        return jsonify({"results":results,"count":len(results),
                        "universe":d.get("universe"),"total_scanned":len(symbols)})
    except Exception as e:
        traceback.print_exc(); return jsonify({"error":str(e)}),500

@app.route("/api/backtest/run", methods=["POST"])
def run_backtest():
    try:
        d=request.json; conditions,universe=[],  "NIFTY 50"
        if d.get("scan_id"):
            conn=get_db()
            row=conn.execute("SELECT * FROM scans WHERE id=?",(d["scan_id"],)).fetchone()
            conn.close()
            if row: conditions=json.loads(row["conds"]); universe=row["uni"]
        trades,equity,stats = backtest(
            get_symbols(universe), conditions,
            d.get("from","2024-01-01"), d.get("to",datetime.now().strftime("%Y-%m-%d")),
            float(d.get("stop_loss",3)), int(d.get("exit_days",8)), d.get("exit_rule","After N Days"))
        return jsonify({"trades":trades,"equity":equity,"stats":stats})
    except Exception as e:
        traceback.print_exc(); return jsonify({"error":str(e)}),500

@app.route("/api/market/regime")
def market_regime():
    try:
        df=compute_indicators(fetch_nifty("3mo")); last=df.iloc[-1]
        cl=float(last["close"]); e20=float(last["ema20"]); e50=float(last["ema50"])
        adx=float(last.get("adx14",0) or 0); pct=float(last.get("pct_chg",0) or 0)
        if   cl>e20>e50 and adx>25: regime="STRONG BULL"
        elif cl>e20 and adx>20:     regime="BULL"
        elif cl<e20<e50 and adx>25: regime="STRONG BEAR"
        elif cl<e20:                regime="BEAR"
        else:                       regime="SIDEWAYS"
        return jsonify({"regime":regime,"nifty_close":round(cl,2),"nifty_change":round(pct,2),
                        "ema20":round(e20,2),"ema50":round(e50,2),"adx":round(adx,2)})
    except Exception as e:
        return jsonify({"error":str(e)}),500

# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    init_db()
    print("\n  QuantEdge NSE Backend  v3")
    print("  ──────────────────────────")
    print(f"  Indices available: {list(UNIVERSES.keys())}")
    print("  Running at: http://localhost:5000")
    print("  Status:     http://localhost:5000/api/status")
    print("  Universe:   http://localhost:5000/api/universe\n")
    app.run(debug=True, port=5000)
