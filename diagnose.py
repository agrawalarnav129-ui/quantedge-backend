"""
Run this script on your machine to diagnose the live data issue.
python diagnose.py
"""
import yfinance as yf
import pandas as pd
import numpy as np

print("=" * 60)
print("QUANTEDGE — LIVE DATA DIAGNOSTICS")
print("=" * 60)

print(f"\nyfinance version: {yf.__version__}")
print(f"pandas version:   {pd.__version__}")

# ── Test 1: Raw fetch
print("\n[1] Fetching RELIANCE.NS (5 days)...")
t = yf.Ticker("RELIANCE.NS")
df = t.history(period="5d", auto_adjust=True)
print(f"    Rows returned: {len(df)}")
print(f"    Columns: {df.columns.tolist()}")
if not df.empty:
    print(f"    Last close: ₹{df['Close'].iloc[-1]:.2f}")
    print(f"    Index timezone: {df.index.tz}")
    print(f"    Last date: {df.index[-1]}")
else:
    print("    ❌ EMPTY — fetch failed")

# ── Test 2: Column name case
print("\n[2] Column name case check...")
cols = [c.lower() for c in df.columns]
print(f"    Lowercased: {cols}")
has_close = "close" in cols
print(f"    Has 'close': {has_close}")

# ── Test 3: NIFTY fetch
print("\n[3] Fetching ^NSEI (NIFTY 50)...")
n = yf.Ticker("^NSEI")
nf = n.history(period="5d", auto_adjust=True)
print(f"    Rows: {len(nf)}")
if not nf.empty:
    print(f"    Last NIFTY close: {nf['Close'].iloc[-1]:.2f}")

# ── Test 4: 1-year fetch (what scanner uses)
print("\n[4] Fetching INFY.NS (1 year)...")
t2 = yf.Ticker("INFY.NS")
df2 = t2.history(period="1y", auto_adjust=True)
print(f"    Rows: {len(df2)}")
if not df2.empty:
    print(f"    Date range: {df2.index[0].date()} → {df2.index[-1].date()}")
    print(f"    Last close: ₹{df2['Close'].iloc[-1]:.2f}")

    # ── Test 5: RS calculation
    print("\n[5] RS vs NIFTY calculation test...")
    nf2 = yf.Ticker("^NSEI").history(period="1y", auto_adjust=True)
    nifty_close = nf2["Close"].reindex(df2.index, method="ffill")
    c = df2["Close"]
    stock_norm = c / c.iloc[0]
    nifty_norm = nifty_close / nifty_close.iloc[0]
    rs = stock_norm / nifty_norm
    print(f"    RS start: {rs.iloc[0]:.4f} (should be ~1.0)")
    print(f"    RS latest: {rs.iloc[-1]:.4f}  (>1 = outperforming NIFTY)")
    print(f"    RS 5d change: {rs.pct_change(5).iloc[-1]*100:.2f}%")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
