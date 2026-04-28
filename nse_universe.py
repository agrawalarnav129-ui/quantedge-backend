"""
nse_universe.py
Fetches complete NSE stock universe from official NSE index CSV files.
Run once to build the universe cache, then app.py uses it automatically.

Usage:
    python nse_universe.py          # builds universe JSON
    python nse_universe.py --test   # fetch + verify 5 tickers
"""

import requests, json, io, time, sys
from pathlib import Path
import pandas as pd

CACHE_FILE = Path("nse_universe.json")

# ─────────────────────────────────────────────────────────────
#  NSE official index constituent CSV URLs
#  These are the real NSE download links — no login required
# ─────────────────────────────────────────────────────────────
NSE_INDEX_URLS = {
    "NIFTY 50":          "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "NIFTY NEXT 50":     "https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv",
    "NIFTY MIDCAP 100":  "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap100list.csv",
    "NIFTY SMALLCAP 100":"https://nsearchives.nseindia.com/content/indices/ind_niftysmallcap100list.csv",
    "NIFTY 500":         "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "NIFTY BANK":        "https://nsearchives.nseindia.com/content/indices/ind_niftybanklist.csv",
    "NIFTY IT":          "https://nsearchives.nseindia.com/content/indices/ind_niftyitlist.csv",
    "NIFTY PHARMA":      "https://nsearchives.nseindia.com/content/indices/ind_niftypharmalist.csv",
    "NIFTY AUTO":        "https://nsearchives.nseindia.com/content/indices/ind_niftyautolist.csv",
    "NIFTY FMCG":        "https://nsearchives.nseindia.com/content/indices/ind_niftyfmcglist.csv",
    "NIFTY METAL":       "https://nsearchives.nseindia.com/content/indices/ind_niftymetallist.csv",
    "NIFTY REALTY":      "https://nsearchives.nseindia.com/content/indices/ind_niftyrealtylist.csv",
    "NIFTY ENERGY":      "https://nsearchives.nseindia.com/content/indices/ind_niftyenergylist.csv",
    "NIFTY INFRA":       "https://nsearchives.nseindia.com/content/indices/ind_niftyinfralist.csv",
    "NIFTY MIDCAP 50":   "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap50list.csv",
    "NIFTY 100":         "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
    "NIFTY 200":         "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv",
}

# Headers required to bypass NSE's referer check
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com",
    "Connection": "keep-alive",
}

def fetch_index_csv(index_name: str, url: str, session: requests.Session) -> pd.DataFrame:
    """Fetch one NSE index CSV and return cleaned DataFrame."""
    try:
        # NSE requires a prior visit to nseindia.com to set cookies
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        # NSE CSVs have 'Symbol' column — normalize
        df.columns = [c.strip() for c in df.columns]
        sym_col = next((c for c in df.columns if c.upper() in ["SYMBOL","SCRIP CODE","TICKER"]), None)
        name_col = next((c for c in df.columns if "NAME" in c.upper() or "COMPANY" in c.upper()), None)
        sector_col = next((c for c in df.columns if "SECTOR" in c.upper() or "INDUSTRY" in c.upper()), None)

        if sym_col is None:
            print(f"  ⚠ {index_name}: no Symbol column found. Columns: {df.columns.tolist()}")
            return pd.DataFrame()

        result = pd.DataFrame()
        result["symbol"]  = df[sym_col].str.strip()
        result["name"]    = df[name_col].str.strip() if name_col else result["symbol"]
        result["sector"]  = df[sector_col].str.strip() if sector_col else "—"
        result["index"]   = index_name
        return result.dropna(subset=["symbol"])
    except Exception as e:
        print(f"  ❌ {index_name}: {e}")
        return pd.DataFrame()


def build_universe() -> dict:
    """
    Fetch all NSE index constituents and build a master universe.
    Returns dict with:
        - all_symbols: list of all unique symbols
        - by_index: {index_name: [symbols]}
        - metadata: {symbol: {name, sector, indices}}
    """
    print("\n  Building NSE Universe from official index CSVs...")
    print("  " + "─" * 50)

    session = requests.Session()
    # Warm up session with NSE homepage to get cookies
    try:
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
        time.sleep(0.5)
    except Exception:
        pass

    by_index = {}
    all_rows = []

    for idx_name, url in NSE_INDEX_URLS.items():
        print(f"  Fetching {idx_name}...", end=" ", flush=True)
        df = fetch_index_csv(idx_name, url, session)
        if not df.empty:
            syms = df["symbol"].tolist()
            by_index[idx_name] = syms
            all_rows.append(df)
            print(f"✓ {len(syms)} stocks")
        else:
            print("✗ skipped")
        time.sleep(0.3)

    if not all_rows:
        print("\n  ❌ All fetches failed — NSE may be blocking. Using fallback hardcoded universe.")
        return build_fallback_universe()

    master = pd.concat(all_rows, ignore_index=True)

    # Build metadata: one row per symbol with all indices it belongs to
    metadata = {}
    for sym, group in master.groupby("symbol"):
        metadata[sym] = {
            "name":    group["name"].iloc[0],
            "sector":  group["sector"].iloc[0],
            "indices": group["index"].tolist(),
        }

    # Add NIFTY 200 = NIFTY 100 + NIFTY NEXT 50 + top MIDCAP if not fetched
    if "NIFTY 200" not in by_index:
        n200 = list({s for k in ["NIFTY 100","NIFTY NEXT 50"] for s in by_index.get(k,[])})
        by_index["NIFTY 200"] = n200

    universe = {
        "all_symbols": list(metadata.keys()),
        "by_index":    by_index,
        "metadata":    metadata,
        "total":       len(metadata),
    }

    print(f"\n  ✓ Universe built: {len(metadata)} unique stocks across {len(by_index)} indices")
    return universe


def build_fallback_universe() -> dict:
    """Hardcoded fallback if NSE blocks the fetch."""
    NIFTY50 = [
        "RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","HINDUNILVR","ITC","SBIN",
        "BAJFINANCE","BHARTIARTL","KOTAKBANK","AXISBANK","ASIANPAINT","MARUTI","TITAN",
        "SUNPHARMA","ONGC","NESTLEIND","WIPRO","LT","HCLTECH","ULTRACEMCO","ADANIENT",
        "POWERGRID","NTPC","TATASTEEL","JSWSTEEL","INDUSINDBK","COALINDIA","BPCL",
        "BAJAJ-AUTO","GRASIM","HEROMOTOCO","BRITANNIA","DIVISLAB","CIPLA","EICHERMOT",
        "APOLLOHOSP","TATACONSUM","HINDALCO","TECHM","ADANIPORTS","SHRIRAMFIN",
        "DRREDDY","BAJAJFINSV","SBILIFE","HDFCLIFE","LTIM","M&M","TATAMOTORS",
    ]
    NIFTY_NEXT50 = [
        "ABB","ADANIGREEN","ADANIPOWER","AMBUJACEM","BAJAJHLDNG","BERGEPAINT","BEL",
        "BOSCHLTD","COLPAL","CONCOR","DABUR","DLF","GAIL","GODREJCP","HAVELLS",
        "INDHOTEL","IOC","IRCTC","LICHSGFIN","LUPIN","MCDOWELL-N","MOTHERSON","NHPC",
        "NMDC","NAUKRI","PAGEIND","PIDILITIND","PNBHOUSING","PFC","RECLTD","SAIL",
        "SIEMENS","SRF","TATACOMM","TORNTPHARM","TRENT","UBL","VEDL","VOLTAS","ZYDUSLIFE",
    ]
    NIFTY_MIDCAP = [
        "AARTIIND","ABCAPITAL","AJANTPHARM","ALKEM","APLLTD","ASTRAL","AUROPHARMA",
        "BALKRISIND","BANDHANBNK","BANKBARODA","BATAINDIA","BDL","BHARATFORG","BLUESTAR",
        "BSE","CAMS","CANFINHOME","CANBK","CARBORUNDUM","CASTROLIND","CESC","CHOLAFIN",
        "COFORGE","CROMPTON","CUB","CUMMINSIND","CYIENT","DEEPAKNTR","DIXON","ELECON",
        "EMAMILTD","ENDURANCE","ENGINERSIN","ESCORTS","EXIDEIND","FEDERALBNK","FINCABLES",
        "GLENMARK","GMRINFRA","GNFC","GODREJIND","GRANULES","GSPL","GUJGASLTD","HAPPSTMNDS",
        "HFCL","HONASA","HUDCO","IDFCFIRSTB","INDIANB","INDIGO","INDUSINDBK","INOXWIND",
        "INTELLECT","IOB","IPCALAB","IRFC","ISEC","J&KBANK","JBCHEPHARM","JKCEMENT",
        "JKPAPER","JPPOWER","JSL","JUBLINGREA","KAJARIACER","KALYANKJIL","KANSAINER",
        "KPIL","KPITTECH","KRBL","KRISHNADEF","LALPATHLAB","LAURUSLABS","LICHSGFIN",
        "LICI","LINDEINDIA","LUXIND","MAHARASHTRA","MANAPPURAM","MARICO","MFSL","MPHASIS",
        "MRF","NATCOPHARM","NBCC","NCC","NIACL","NOCIL","NUVOCO","OFSS","OIL","OLECTRA",
        "PERSISTENT","PETRONET","PFIZER","PHOENIXLTD","PIIND","POLYCAB","POONAWALLA",
        "PRESTIGE","PRINCEPIPE","PVRINOX","RADICO","RAJESHEXPO","RAMCOCEM","RITES",
        "RPOWER","SANOFI","SCHAEFFLER","SHYAMMETL","SOBHA","SOLARINDS","SONACOMS",
        "STARHEALTH","SUDARSCHEM","SUMICHEM","SUNTV","SUPREMEIND","SUZLON","SWSOLAR",
        "TANLA","TATAELXSI","TATAINVEST","TEAMLEASE","TIINDIA","TIMKEN","TITAGARH",
        "TORNTPOWER","TTKPRESTIG","UCOBANK","UJJIVANSFB","UNIONBANK","UPL","USHAMART",
        "VGUARD","VINATIORGA","VBL","WELCORP","WIPRO","XCHANGING","YESBANK","ZOMATO",
    ]

    all_syms = list(dict.fromkeys(NIFTY50 + NIFTY_NEXT50 + NIFTY_MIDCAP))
    metadata = {s: {"name": s, "sector": "—", "indices": []} for s in all_syms}

    return {
        "all_symbols": all_syms,
        "by_index": {
            "NIFTY 50":       NIFTY50,
            "NIFTY NEXT 50":  NIFTY_NEXT50,
            "NIFTY 100":      NIFTY50 + NIFTY_NEXT50,
            "NIFTY MIDCAP 100": NIFTY_MIDCAP,
            "NIFTY 200":      list(dict.fromkeys(NIFTY50 + NIFTY_NEXT50 + NIFTY_MIDCAP)),
            "NIFTY 500":      all_syms,
            "ALL NSE":        all_syms,
        },
        "metadata": metadata,
        "total": len(all_syms),
    }


def load_universe() -> dict:
    """Load cached universe or build fresh."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            data = json.load(f)
        print(f"  Universe loaded from cache: {data['total']} stocks")
        return data
    return build_and_save()


def build_and_save() -> dict:
    """Build universe and save to JSON cache."""
    universe = build_universe()
    with open(CACHE_FILE, "w") as f:
        json.dump(universe, f, indent=2)
    print(f"\n  ✓ Saved to {CACHE_FILE}")
    return universe


if __name__ == "__main__":
    if "--test" in sys.argv:
        import yfinance as yf
        u = load_universe()
        print(f"\nTesting 5 random symbols from universe...")
        import random
        for sym in random.sample(u["all_symbols"], 5):
            t = yf.Ticker(f"{sym}.NS")
            df = t.history(period="3d")
            status = f"✓ ₹{df['Close'].iloc[-1]:.2f}" if not df.empty else "❌ no data"
            print(f"  {sym:20s} {status}")
    else:
        build_and_save()
        u = load_universe()
        print(f"\nIndex breakdown:")
        for idx, syms in u["by_index"].items():
            print(f"  {idx:25s} {len(syms):4d} stocks")
