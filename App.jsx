import { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

// ═══════════════════════ CONFIG — update API_BASE when deployed ═══════════════════════
// Local dev:   "http://localhost:5000"
// Render:      "https://your-app-name.onrender.com"
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";

// Passwords — add/remove as needed (stored only in frontend, no server round-trip)
const PASSWORDS = ["quantedge2026", "arnav@qe", "trader99"];

const apiFetch = (path, options = {}) =>
  fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });

const useIsMobile = () => {
  const [mobile, setMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const h = () => setMobile(window.innerWidth < 768);
    window.addEventListener("resize", h);
    return () => window.removeEventListener("resize", h);
  }, []);
  return mobile;
};

const C = {
  bg:'#070B14', sf:'#0D1117', sf2:'#161B22', bd:'#21262D',
  acc:'#00D68F', up:'#3FB950', dn:'#F85149', wa:'#D29922', pu:'#A371F7',
  tx:'#E6EDF3', mu:'#7D8590',
  fn:"'Outfit',sans-serif", mo:"'JetBrains Mono',monospace"
};

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
html,body{overflow-x:hidden;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:#0D1117;}
::-webkit-scrollbar-thumb{background:#30363D;border-radius:2px;}
.hov:hover{background:rgba(0,214,143,0.05)!important;}
.card:hover{border-color:#30363D!important;transform:translateY(-1px);}
.card{transition:all 0.15s ease;}
.btn{transition:all 0.12s;}
.btn:hover{opacity:0.85;}
.delbtn{opacity:0;transition:opacity 0.12s;}
.condrow:hover .delbtn{opacity:1;}
select,input[type=number],input[type=text],input[type=date],input[type=password]{appearance:none;-webkit-appearance:none;outline:none;}
select option{background:#161B22;color:#E6EDF3;}

/* ── Mobile bottom nav ── */
.mobile-nav{display:none;}
@media(max-width:767px){
  .desktop-sidebar{display:none!important;}
  .mobile-nav{display:flex;position:fixed;bottom:0;left:0;right:0;z-index:200;
    background:#0D1117;border-top:1px solid #21262D;height:56px;}
  .main-content{padding-bottom:64px!important;}
  .header-ticker{display:none!important;}
  .header-brand span.subtitle{display:none!important;}
  .scan-grid{grid-template-columns:1fr!important;}
  .stat-grid{grid-template-columns:1fr 1fr!important;}
  .scan-builder-grid{grid-template-columns:1fr!important;}
  .bt-config-grid{grid-template-columns:1fr 1fr!important;}
  .bt-stats-grid{grid-template-columns:1fr 1fr 1fr!important;}
  .condrow-wrap{flex-wrap:wrap;gap:5px!important;}
  .results-table{font-size:10px!important;}
  .results-table td,.results-table th{padding:6px 8px!important;}
  .hide-mobile{display:none!important;}
}
@media(min-width:768px) and (max-width:1024px){
  .desktop-sidebar{width:170px!important;}
  .scan-grid{grid-template-columns:1fr 1fr!important;}
  .stat-grid{grid-template-columns:repeat(2,1fr)!important;}
}

/* ── Login ── */
.login-btn{width:100%;padding:12px;background:#00D68F;border:none;border-radius:6px;
  cursor:pointer;font-family:'Outfit',sans-serif;font-size:14px;font-weight:800;
  color:#000;letter-spacing:0.5px;transition:opacity 0.12s;}
.login-btn:hover{opacity:0.87;}
`;


// ═══════════════════════ INDICATOR CONFIG ═══════════════════════
const INDICATOR_GROUPS = [
  { g:'Price', items:[
    {l:'Close',v:'close',t:'price'},{l:'Open',v:'open',t:'price'},
    {l:'High',v:'high',t:'price'},{l:'Low',v:'low',t:'price'},
    {l:'% Change',v:'pct_chg',t:'num'},{l:'% from 52W High',v:'pct52h',t:'num'},
    {l:'% from 52W Low',v:'pct52l',t:'num'},
  ]},
  { g:'Moving Averages', items:[
    {l:'EMA(9)',v:'ema9',t:'price'},{l:'EMA(20)',v:'ema20',t:'price'},
    {l:'EMA(50)',v:'ema50',t:'price'},{l:'EMA(200)',v:'ema200',t:'price'},
    {l:'SMA(20)',v:'sma20',t:'price'},{l:'SMA(50)',v:'sma50',t:'price'},
  ]},
  { g:'Momentum', items:[
    {l:'RSI(14)',v:'rsi14',t:'num'},{l:'RSI(9)',v:'rsi9',t:'num'},
    {l:'MACD Line',v:'macd',t:'num'},{l:'MACD Signal',v:'macd_sig',t:'num'},
    {l:'MACD Histogram',v:'macd_hist',t:'num'},
  ]},
  { g:'Trend', items:[
    {l:'ADX(14)',v:'adx14',t:'num'},{l:'+DI(14)',v:'di_plus',t:'num'},
    {l:'-DI(14)',v:'di_minus',t:'num'},
  ]},
  { g:'Volatility', items:[
    {l:'ATR(14)',v:'atr14',t:'price'},{l:'ATR % (14)',v:'atr_pct',t:'num'},
    {l:'BB Upper',v:'bb_up',t:'price'},{l:'BB Lower',v:'bb_lo',t:'price'},
    {l:'BB Middle',v:'bb_mid',t:'price'},{l:'BB %B',v:'bb_pctb',t:'num'},
    {l:'BB Bandwidth',v:'bb_bw',t:'num'},
  ]},
  { g:'Volume', items:[
    {l:'Volume',v:'vol',t:'num'},{l:'Avg Volume (20)',v:'avg_vol20',t:'num'},
    {l:'Volume Ratio (20)',v:'vol_ratio',t:'num'},{l:'OBV',v:'obv',t:'num'},
  ]},
  { g:'Relative Strength', items:[
    {l:'RS vs NIFTY',v:'rs_nifty',t:'num'},{l:'RS vs NIFTY (5d Δ)',v:'rs_nifty5d',t:'num'},
    {l:'RS vs Sector',v:'rs_sector',t:'num'},
  ]},
  { g:'Patterns', items:[
    {l:'Candle Pattern',v:'pattern',t:'pattern'},{l:'NR4',v:'nr4',t:'bool'},
    {l:'NR7',v:'nr7',t:'bool'},{l:'Inside Bar',v:'inside_bar',t:'bool'},
  ]},
];
const ALL_IND = INDICATOR_GROUPS.flatMap(g => g.items);
const getInd = v => ALL_IND.find(i => i.v === v) || {l:v, t:'num'};

const OPS = [
  {l:'>',v:'gt'},{l:'<',v:'lt'},{l:'≥',v:'gte'},{l:'≤',v:'lte'},
  {l:'=',v:'eq'},{l:'Crosses ↑',v:'x_above'},{l:'Crosses ↓',v:'x_below'},
];
const PATTERNS = ['Inside Bar','NR4','NR7','Bullish Engulfing','Bearish Engulfing','Hammer','Shooting Star','Doji','Morning Star','Evening Star'];
const UNIVERSES = ['NIFTY 50','NIFTY 100','NIFTY 200','NIFTY 500','ALL NSE'];
const TIMEFRAMES = ['Daily','15 Minute','Daily + 15 Min'];
const EXIT_RULES = ['After N Days','RSI Overbought (>70)','ATR Trailing Stop','EMA Cross Down'];

// ═══════════════════════ MOCK DATA ═══════════════════════
const STOCKS = [
  {s:'DIXON',n:'Dixon Tech',p:14820,c:5.1,rsi:76.8,adx:42.1,vr:3.14,rs:1.22,bw:0.03,sec:'Electronics',setup:'Breakout'},
  {s:'ASTRAL',n:'Astral Ltd',p:2187,c:4.2,rsi:74.1,adx:38.2,vr:2.87,rs:1.18,bw:0.04,sec:'Building Mat',setup:'Breakout'},
  {s:'POLYCAB',n:'Polycab India',p:5892,c:3.5,rsi:71.6,adx:33.4,vr:2.32,rs:1.15,bw:0.05,sec:'Electricals',setup:'Breakout'},
  {s:'ICICIBANK',n:'ICICI Bank',p:1289,c:3.1,rsi:72.3,adx:35.7,vr:2.14,rs:1.14,bw:0.06,sec:'Banking',setup:'Breakout'},
  {s:'PERSISTENT',n:'Persistent Sys',p:5641,c:3.8,rsi:69.4,adx:30.8,vr:1.96,rs:1.13,bw:0.07,sec:'IT',setup:'Momentum'},
  {s:'TITAN',n:'Titan Company',p:3421,c:2.9,rsi:68.9,adx:29.3,vr:1.91,rs:1.11,bw:0.07,sec:'Consumer',setup:'Breakout'},
  {s:'RELIANCE',n:'Reliance Ind.',p:2847,c:2.3,rsi:67.2,adx:28.4,vr:1.82,rs:1.09,bw:0.08,sec:'Energy',setup:'Continuation'},
  {s:'TATAELXSI',n:'Tata Elxsi',p:7234,c:2.7,rsi:65.3,adx:27.6,vr:1.72,rs:1.08,bw:0.09,sec:'IT',setup:'Momentum'},
  {s:'HDFCBANK',n:'HDFC Bank',p:1642,c:1.8,rsi:64.5,adx:31.2,vr:1.65,rs:1.06,bw:0.12,sec:'Banking',setup:'Momentum'},
  {s:'MARUTI',n:'Maruti Suzuki',p:12456,c:1.6,rsi:63.2,adx:26.8,vr:1.54,rs:1.05,bw:0.11,sec:'Auto',setup:'Continuation'},
  {s:'BAJFINANCE',n:'Bajaj Finance',p:7234,c:1.4,rsi:61.8,adx:22.9,vr:1.38,rs:1.03,bw:0.15,sec:'NBFC',setup:'Momentum'},
  {s:'CAMS',n:'CAMS',p:3892,c:2.1,rsi:62.7,adx:24.3,vr:1.48,rs:1.04,bw:0.13,sec:'Financial',setup:'Continuation'},
];

const INIT_SCANS = [
  {
    id:1, name:'Momentum Breakout', color:'#00D68F',
    desc:'Price above EMA20/50, RSI > 60, Volume surge, ADX > 25',
    uni:'NIFTY 200', tf:'Daily', lastRun:'27 Apr, 09:15', cnt:14,
    conds:[
      {id:1,ind:'close',op:'gt',vt:'ind',val:'',vi:'ema20',lg:'AND'},
      {id:2,ind:'close',op:'gt',vt:'ind',val:'',vi:'ema50',lg:'AND'},
      {id:3,ind:'rsi14',op:'gt',vt:'num',val:'60',vi:null,lg:'AND'},
      {id:4,ind:'vol_ratio',op:'gt',vt:'num',val:'1.5',vi:null,lg:'AND'},
      {id:5,ind:'adx14',op:'gt',vt:'num',val:'25',vi:null,lg:'AND'},
    ]
  },
  {
    id:2, name:'RS Leaders', color:'#A371F7',
    desc:'Outperforming NIFTY with rising relative strength',
    uni:'NIFTY 100', tf:'Daily', lastRun:'27 Apr, 09:15', cnt:22,
    conds:[
      {id:1,ind:'rs_nifty',op:'gt',vt:'num',val:'1.05',vi:null,lg:'AND'},
      {id:2,ind:'rs_nifty5d',op:'gt',vt:'num',val:'0',vi:null,lg:'AND'},
      {id:3,ind:'rsi14',op:'gt',vt:'num',val:'55',vi:null,lg:'AND'},
      {id:4,ind:'adx14',op:'gt',vt:'num',val:'20',vi:null,lg:'AND'},
    ]
  },
  {
    id:3, name:'BB Squeeze Breakout', color:'#D29922',
    desc:'Low volatility squeeze + price above BB Upper + volume',
    uni:'NIFTY 200', tf:'Daily', lastRun:'26 Apr, 15:30', cnt:6,
    conds:[
      {id:1,ind:'bb_bw',op:'lt',vt:'num',val:'0.1',vi:null,lg:'AND'},
      {id:2,ind:'close',op:'gt',vt:'ind',val:'',vi:'bb_up',lg:'AND'},
      {id:3,ind:'vol_ratio',op:'gt',vt:'num',val:'2.0',vi:null,lg:'AND'},
    ]
  },
  {
    id:4, name:'NR7 + Strong Trend', color:'#F85149',
    desc:'Narrow Range 7-bar with ADX > 25 and RSI > 50',
    uni:'NIFTY 500', tf:'Daily', lastRun:'26 Apr, 15:30', cnt:9,
    conds:[
      {id:1,ind:'nr7',op:'eq',vt:'bool',val:'true',vi:null,lg:'AND'},
      {id:2,ind:'adx14',op:'gt',vt:'num',val:'25',vi:null,lg:'AND'},
      {id:3,ind:'rsi14',op:'gt',vt:'num',val:'50',vi:null,lg:'AND'},
    ]
  },
];

// Deterministic equity curve
const EQ_D = [2.1,-1.3,3.4,-0.8,1.9,2.7,-1.1,3.8,1.5,-0.5,2.3,4.1,-0.9,1.8,2.6,-1.4,3.2,0.8,2.5,-0.7,1.6,3.9,-0.6,2.8,1.4,-1.0,3.6,0.9,2.2,-0.8,4.3,-1.2,2.0,3.1,-0.4,1.7,2.9,-0.9,3.5,1.3,-0.6,2.4,1.9,3.0,-0.8,2.6,1.5,-0.5,3.8,2.1,-1.1,3.4,1.8,-0.7,2.5,3.2,-0.9,1.6,2.8,4.0];
const MO = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const EQUITY = (() => {
  let v = 100000;
  return EQ_D.map((r, i) => {
    v = Math.round(v * (1 + r / 100));
    const d = new Date(2025, 0, 1 + i * 5);
    return { date:`${d.getDate()} ${MO[d.getMonth()]}`, value: v };
  });
})();

const TRADES = [
  {dt:'03 Jan',sym:'DIXON',entry:13200,exit:14820,pnl:12.3,rr:2.8,days:8,res:'WIN'},
  {dt:'07 Jan',sym:'ASTRAL',entry:2050,exit:1994,pnl:-2.7,rr:0.6,days:3,res:'LOSS'},
  {dt:'12 Jan',sym:'POLYCAB',entry:5420,exit:5892,pnl:8.7,rr:2.1,days:6,res:'WIN'},
  {dt:'15 Jan',sym:'TITAN',entry:3180,exit:3421,pnl:7.6,rr:1.9,days:5,res:'WIN'},
  {dt:'18 Jan',sym:'ICICIBANK',entry:1210,exit:1172,pnl:-3.1,rr:0.8,days:2,res:'LOSS'},
  {dt:'22 Jan',sym:'PERSISTENT',entry:5180,exit:5641,pnl:8.9,rr:2.3,days:7,res:'WIN'},
  {dt:'28 Jan',sym:'TATAELXSI',entry:6820,exit:7234,pnl:6.1,rr:1.7,days:4,res:'WIN'},
  {dt:'03 Feb',sym:'RELIANCE',entry:2680,exit:2592,pnl:-3.3,rr:0.7,days:3,res:'LOSS'},
  {dt:'08 Feb',sym:'BAJFINANCE',entry:6890,exit:7234,pnl:5.0,rr:1.4,days:5,res:'WIN'},
  {dt:'14 Feb',sym:'CAMS',entry:3620,exit:3892,pnl:7.5,rr:2.0,days:6,res:'WIN'},
  {dt:'19 Feb',sym:'DIXON',entry:14100,exit:14980,pnl:6.2,rr:1.8,days:4,res:'WIN'},
  {dt:'25 Feb',sym:'HDFCBANK',entry:1590,exit:1538,pnl:-3.3,rr:0.7,days:2,res:'LOSS'},
  {dt:'03 Mar',sym:'MARUTI',entry:11800,exit:12456,pnl:5.6,rr:1.6,days:5,res:'WIN'},
  {dt:'09 Mar',sym:'ASTRAL',entry:2100,exit:2380,pnl:13.3,rr:3.2,days:9,res:'WIN'},
];
const WINS = TRADES.filter(t => t.res==='WIN');
const LOSSES = TRADES.filter(t => t.res==='LOSS');
const FINAL_VAL = EQUITY[EQUITY.length - 1].value;
const STATS = {
  winRate: ((WINS.length / TRADES.length) * 100).toFixed(1),
  avgRR: (TRADES.reduce((a,t) => a + t.rr, 0) / TRADES.length).toFixed(2),
  expectancy: (TRADES.reduce((a,t) => a + (t.res==='WIN' ? t.pnl : -Math.abs(t.pnl)), 0) / TRADES.length).toFixed(1),
  maxDD: '-8.4', sharpe: '1.87',
  wins: WINS.length, losses: LOSSES.length, total: TRADES.length,
};

// ═══════════════════════ CONDITION ID COUNTER ═══════════════════════
let _id = 500;
const mkCond = () => ({ id: _id++, ind:'rsi14', op:'gt', vt:'num', val:'60', vi:'ema20', lg:'AND' });

// ═══════════════════════ SHARED STYLES ═══════════════════════
const selSt = { padding:'7px 11px', background:'#161B22', border:'1px solid #21262D', borderRadius:6, color:C.tx, fontFamily:C.mo, fontSize:11, cursor:'pointer', outline:'none' };
const inpSt = { ...selSt, width:'100%' };

// ═══════════════════════ MICRO COMPONENTS ═══════════════════════
const Chip = ({ label, color }) => (
  <span style={{ fontFamily:C.mo, fontSize:10, padding:'2px 7px', borderRadius:3, background:`${color}18`, color, border:`1px solid ${color}35`, letterSpacing:0.4, whiteSpace:'nowrap' }}>{label}</span>
);

const Lbl = ({ children }) => (
  <div style={{ fontFamily:C.mo, fontSize:9, color:C.mu, letterSpacing:1.2, textTransform:'uppercase', marginBottom:6 }}>{children}</div>
);

const EqTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.[0]) return null;
  const v = payload[0].value;
  const pct = ((v - 100000) / 100000 * 100).toFixed(1);
  return (
    <div style={{ background:'#0D1117', border:'1px solid #21262D', borderRadius:6, padding:'8px 12px' }}>
      <div style={{ fontFamily:C.mo, fontSize:9, color:C.mu, marginBottom:4 }}>{label}</div>
      <div style={{ fontFamily:C.mo, fontSize:14, fontWeight:600, color: v >= 100000 ? C.up : C.dn }}>₹{v.toLocaleString('en-IN')}</div>
      <div style={{ fontFamily:C.mo, fontSize:10, color: v >= 100000 ? C.up : C.dn }}>{pct >= 0 ? '+' : ''}{pct}%</div>
    </div>
  );
};

// ═══════════════════════ HEADER ═══════════════════════
function Header({ onLogout }) {
  const [live, setLive] = useState(null);
  const isMobile = useIsMobile();

  useEffect(() => {
    const check = async () => {
      try {
        const r = await apiFetch('/api/status');
        if (r.ok) { const d = await r.json(); setLive(d.live === true); }
        else setLive(false);
      } catch { setLive(false); }
    };
    check();
    const iv = setInterval(check, 30000);
    return () => clearInterval(iv);
  }, []);

  const badge = live === null
    ? { color:C.mu, dot:C.mu, label:'CONNECTING...' }
    : live
    ? { color:C.up, dot:C.up, label: isMobile ? 'LIVE' : 'LIVE · NSE DATA' }
    : { color:C.wa, dot:C.wa, label: isMobile ? 'DEMO' : 'DEMO — start backend' };

  return (
    <div style={{ background:C.sf, borderBottom:'1px solid #21262D', padding:'0 16px', height:50, display:'flex', alignItems:'center', justifyContent:'space-between', position:'sticky', top:0, zIndex:100 }}>
      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
        <div style={{ width:26, height:26, background:C.acc, borderRadius:5, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
          <span style={{ fontFamily:C.fn, fontWeight:800, fontSize:12, color:'#000' }}>Q</span>
        </div>
        <span style={{ fontFamily:C.fn, fontWeight:800, fontSize:15, color:C.tx, letterSpacing:0.3, whiteSpace:'nowrap' }}>
          QuantEdge <span style={{ color:C.acc }}>NSE</span>
        </span>
      </div>

      {!isMobile && (
        <div style={{ display:'flex', alignItems:'center', gap:20 }}>
          {[{l:'NIFTY 50',v:'24,187',c:'▲ 0.82%',cl:C.up},{l:'BANK NIFTY',v:'52,340',c:'▲ 1.14%',cl:C.up},{l:'VIX',v:'12.34',c:'▼ 2.1%',cl:C.dn}].map((x,i)=>(
            <div key={i} style={{ display:'flex', alignItems:'center', gap:6 }}>
              <span style={{ fontFamily:C.mo, fontSize:9, color:C.mu }}>{x.l}</span>
              <span style={{ fontFamily:C.mo, fontSize:11, color:C.tx, fontWeight:500 }}>{x.v}</span>
              <span style={{ fontFamily:C.mo, fontSize:10, color:x.cl }}>{x.c}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
        <div style={{ display:'flex', alignItems:'center', gap:5, padding:'3px 8px', background:'#161B22', borderRadius:4, border:'1px solid #21262D' }}>
          <div style={{ width:5, height:5, borderRadius:'50%', background:badge.dot, boxShadow:live?`0 0 6px ${C.up}`:'none' }} />
          <span style={{ fontFamily:C.mo, fontSize:9, color:badge.color, letterSpacing:0.5 }}>{badge.label}</span>
        </div>
        <button onClick={onLogout} className="btn" style={{ padding:'4px 10px', background:'transparent', border:'1px solid #21262D', borderRadius:4, cursor:'pointer', fontFamily:C.mo, fontSize:9, color:C.mu }}>
          {isMobile ? '⏻' : 'LOGOUT'}
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════ SIDEBAR ═══════════════════════
function Sidebar({ scans, activeId, onSelect, onNew, tab, setTab }) {
  const nav = [
    { id:'dashboard', icon:'▪', label:'Dashboard' },
    { id:'scanner', icon:'◈', label:'Scanner Builder' },
    { id:'backtest', icon:'◉', label:'Backtester' },
  ];
  return (
    <div className="desktop-sidebar" style={{ width:210, background:C.sf, borderRight:'1px solid #21262D', height:'calc(100vh - 50px)', display:'flex', flexDirection:'column', flexShrink:0, overflowY:'auto', position:'sticky', top:50 }}>
      <div style={{ padding:'12px 0' }}>
        {nav.map(n => (
          <button key={n.id} onClick={() => setTab(n.id)}
            style={{ width:'100%', padding:'9px 18px', background:tab===n.id ? `${C.acc}12` : 'transparent', border:'none', borderLeft:`3px solid ${tab===n.id ? C.acc : 'transparent'}`, cursor:'pointer', display:'flex', alignItems:'center', gap:10, transition:'all 0.1s' }}>
            <span style={{ fontSize:11, color:tab===n.id ? C.acc : C.mu }}>{n.icon}</span>
            <span style={{ fontFamily:C.fn, fontSize:13, fontWeight:tab===n.id ? 700 : 400, color:tab===n.id ? C.acc : C.mu }}>{n.label}</span>
          </button>
        ))}
      </div>

      <div style={{ borderTop:'1px solid #21262D', margin:'0 14px' }} />

      <div style={{ padding:'12px 0', flex:1 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'0 14px 8px' }}>
          <span style={{ fontFamily:C.mo, fontSize:8, color:C.mu, letterSpacing:1.5, textTransform:'uppercase' }}>Saved Scans</span>
          <button onClick={onNew} style={{ background:'none', border:'none', cursor:'pointer', color:C.acc, fontSize:18, lineHeight:1, padding:0 }}>+</button>
        </div>
        {scans.map(sc => (
          <button key={sc.id} onClick={() => { onSelect(sc); setTab('scanner'); }}
            style={{ width:'100%', padding:'8px 14px', background:activeId===sc.id ? `${sc.color}10` : 'transparent', border:'none', borderLeft:`3px solid ${activeId===sc.id ? sc.color : 'transparent'}`, cursor:'pointer', textAlign:'left', transition:'all 0.1s' }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
              <span style={{ fontFamily:C.fn, fontSize:12, fontWeight:600, color:activeId===sc.id ? sc.color : C.tx, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', maxWidth:130 }}>{sc.name}</span>
              <span style={{ fontFamily:C.mo, fontSize:11, color:sc.color, fontWeight:600 }}>{sc.cnt}</span>
            </div>
            <span style={{ fontFamily:C.mo, fontSize:8, color:C.mu }}>{sc.uni} · {sc.tf}</span>
          </button>
        ))}
      </div>

      <div style={{ padding:'12px 14px', borderTop:'1px solid #21262D' }}>
        <button onClick={onNew} className="btn" style={{ width:'100%', padding:'8px 0', background:`${C.acc}12`, border:`1px solid ${C.acc}25`, borderRadius:5, cursor:'pointer', fontFamily:C.fn, fontSize:12, fontWeight:700, color:C.acc }}>
          + NEW SCAN
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════ DASHBOARD ═══════════════════════
function Dashboard({ scans, onSelect, onNew, setTab }) {
  const total = scans.reduce((a, s) => a + s.cnt, 0);
  return (
    <div style={{ padding:24, maxWidth:1100 }}>
      {/* Stat Cards */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:14, marginBottom:24 }}>
        {[
          { l:'Total Signals Today', v:total, cl:C.acc },
          { l:'Active Scanners', v:scans.length, cl:C.pu },
          { l:'NIFTY RS (5d)', v:'+1.24%', cl:C.up },
          { l:'Market Regime', v:'TRENDING ↑', cl:C.up },
        ].map((s, i) => (
          <div key={i} style={{ background:C.sf, border:'1px solid #21262D', borderRadius:8, padding:'16px 18px' }}>
            <div style={{ fontFamily:C.mo, fontSize:9, color:C.mu, letterSpacing:1, textTransform:'uppercase', marginBottom:8 }}>{s.l}</div>
            <div style={{ fontFamily:C.mo, fontSize:26, fontWeight:600, color:s.cl }}>{s.v}</div>
          </div>
        ))}
      </div>

      {/* Scan Cards */}
      <div style={{ fontFamily:C.mo, fontSize:9, color:C.mu, letterSpacing:1.5, textTransform:'uppercase', marginBottom:14 }}>Active Scanners</div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(240px,1fr))', gap:14, marginBottom:28 }}>
        {scans.map(sc => (
          <div key={sc.id} className="card" onClick={() => { onSelect(sc); setTab('scanner'); }}
            style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, padding:18, cursor:'pointer' }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:10 }}>
              <div>
                <div style={{ width:7, height:7, borderRadius:'50%', background:sc.color, marginBottom:8 }} />
                <div style={{ fontFamily:C.fn, fontSize:14, fontWeight:700, color:C.tx }}>{sc.name}</div>
              </div>
              <span style={{ fontFamily:C.mo, fontSize:30, fontWeight:700, color:sc.color, lineHeight:1 }}>{sc.cnt}</span>
            </div>
            <p style={{ fontFamily:C.fn, fontSize:11, color:C.mu, lineHeight:1.5, marginBottom:12 }}>{sc.desc}</p>
            <div style={{ display:'flex', gap:6, flexWrap:'wrap', marginBottom:12 }}>
              <Chip label={sc.uni} color={sc.color} />
              <Chip label={sc.tf} color={C.mu} />
              <Chip label={`${sc.conds.length} filters`} color={C.mu} />
            </div>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
              <span style={{ fontFamily:C.mo, fontSize:8, color:C.mu }}>{sc.lastRun}</span>
              <span style={{ fontFamily:C.fn, fontSize:11, fontWeight:700, color:sc.color }}>Edit →</span>
            </div>
          </div>
        ))}
        <div className="card" onClick={onNew}
          style={{ background:'transparent', border:'1px dashed #21262D', borderRadius:10, padding:18, cursor:'pointer', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', minHeight:170 }}>
          <div style={{ fontSize:24, color:C.mu, marginBottom:6 }}>+</div>
          <div style={{ fontFamily:C.fn, fontSize:12, color:C.mu }}>New Scanner</div>
        </div>
      </div>

      {/* Signals Table */}
      <div style={{ fontFamily:C.mo, fontSize:9, color:C.mu, letterSpacing:1.5, textTransform:'uppercase', marginBottom:14 }}>Top Signals Today</div>
      <div style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, overflow:'hidden' }}>
        <table style={{ width:'100%', borderCollapse:'collapse' }}>
          <thead>
            <tr style={{ borderBottom:'1px solid #21262D' }}>
              {['Symbol','Price','Chg %','RSI','ADX','Vol ×','RS/N','BB BW','Setup',''].map(h => (
                <th key={h} style={{ padding:'9px 14px', fontFamily:C.mo, fontSize:8, color:C.mu, textAlign:'left', fontWeight:400, letterSpacing:1 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {STOCKS.map((r, i) => (
              <tr key={i} className="hov" style={{ borderBottom:'1px solid #21262D50' }}>
                <td style={{ padding:'9px 14px' }}>
                  <div style={{ fontFamily:C.fn, fontSize:13, fontWeight:700, color:C.tx }}>{r.s}</div>
                  <div style={{ fontFamily:C.mo, fontSize:8, color:C.mu }}>{r.sec}</div>
                </td>
                <td style={{ padding:'9px 14px', fontFamily:C.mo, fontSize:11, color:C.tx }}>₹{r.p.toLocaleString('en-IN')}</td>
                <td style={{ padding:'9px 14px', fontFamily:C.mo, fontSize:11, color:r.c>=0?C.up:C.dn }}>{r.c>=0?'▲':'▼'}{Math.abs(r.c)}%</td>
                <td style={{ padding:'9px 14px', fontFamily:C.mo, fontSize:11, color:r.rsi>70?C.wa:C.tx }}>{r.rsi.toFixed(1)}</td>
                <td style={{ padding:'9px 14px', fontFamily:C.mo, fontSize:11, color:r.adx>30?C.acc:C.tx }}>{r.adx.toFixed(1)}</td>
                <td style={{ padding:'9px 14px', fontFamily:C.mo, fontSize:11, color:r.vr>2?C.acc:C.tx }}>{r.vr.toFixed(2)}×</td>
                <td style={{ padding:'9px 14px', fontFamily:C.mo, fontSize:11, color:r.rs>1.1?C.up:r.rs>1?C.acc:C.mu }}>{r.rs.toFixed(3)}</td>
                <td style={{ padding:'9px 14px', fontFamily:C.mo, fontSize:11, color:r.bw<0.06?C.wa:C.mu }}>{r.bw.toFixed(3)}</td>
                <td style={{ padding:'9px 14px' }}><Chip label={r.setup} color={r.setup==='Breakout'?C.acc:r.setup==='Momentum'?C.pu:C.mu} /></td>
                <td style={{ padding:'9px 14px' }}>
                  <button className="btn" style={{ padding:'3px 10px', background:`${C.acc}12`, border:`1px solid ${C.acc}25`, borderRadius:4, cursor:'pointer', fontFamily:C.mo, fontSize:8, color:C.acc }}>TRADE</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ═══════════════════════ CONDITION ROW ═══════════════════════
function CondRow({ cond, onChange, onDel, isFirst }) {
  const info = getInd(cond.ind);
  const isPattern = info.t === 'pattern';
  const isBool = info.t === 'bool';
  const isPrice = info.t === 'price';

  const IndSel = ({ val, onCh, w = 150 }) => (
    <select value={val} onChange={e => onCh(e.target.value)} style={{ ...selSt, width:w }}>
      {INDICATOR_GROUPS.map(g => [
        <option key={`d_${g.g}`} disabled style={{ color:C.mu }}>─ {g.g} ─</option>,
        ...g.items.map(i => <option key={i.v} value={i.v}>{i.l}</option>)
      ])}
    </select>
  );

  return (
    <div className="condrow" style={{ display:'flex', alignItems:'center', gap:7, marginBottom:8, flexWrap:'wrap' }}>
      {isFirst
        ? <div style={{ width:38 }} />
        : <button onClick={() => onChange({ ...cond, lg: cond.lg==='AND' ? 'OR' : 'AND' })}
            style={{ width:38, padding:'5px 0', background:'#161B22', border:'1px solid #21262D', borderRadius:5, cursor:'pointer', fontFamily:C.mo, fontSize:10, fontWeight:700, color:cond.lg==='AND'?C.acc:C.wa }}>
            {cond.lg}
          </button>
      }

      <IndSel val={cond.ind} onCh={v => onChange({ ...cond, ind:v, vt:getInd(v).t==='price' ? cond.vt : 'num' })} />

      {!isBool && (
        <select value={cond.op} onChange={e => onChange({ ...cond, op:e.target.value })} style={{ ...selSt, width:108 }}>
          {OPS.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
        </select>
      )}

      {isBool
        ? <span style={{ fontFamily:C.mo, fontSize:10, color:C.acc }}>= TRUE</span>
        : isPattern
        ? <select value={cond.val || PATTERNS[0]} onChange={e => onChange({ ...cond, val:e.target.value })} style={{ ...selSt, width:160 }}>
            {PATTERNS.map(p => <option key={p}>{p}</option>)}
          </select>
        : <div style={{ display:'flex', gap:6, alignItems:'center' }}>
            {isPrice && (
              <button onClick={() => onChange({ ...cond, vt: cond.vt==='ind' ? 'num' : 'ind' })}
                style={{ padding:'5px 8px', background:'#161B22', border:'1px solid #21262D', borderRadius:5, cursor:'pointer', fontFamily:C.mo, fontSize:8, color:C.mu }}>
                {cond.vt==='ind' ? 'IND' : 'NUM'}
              </button>
            )}
            {cond.vt==='ind' && isPrice
              ? <IndSel val={cond.vi || 'ema20'} onCh={v => onChange({ ...cond, vi:v })} w={140} />
              : <input type="number" value={cond.val} onChange={e => onChange({ ...cond, val:e.target.value })} style={{ ...selSt, width:90 }} />
            }
          </div>
      }

      <button className="delbtn" onClick={onDel}
        style={{ background:'none', border:'none', cursor:'pointer', color:C.dn, fontSize:16, padding:'2px 5px', lineHeight:1 }}>×</button>
    </div>
  );
}

// ═══════════════════════ SCANNER VIEW ═══════════════════════
const TEMPLATES = [
  { name:'EMA Crossover', desc:'EMA9 crosses above EMA20 with volume', conds:[
    {id:_id++,ind:'ema9',op:'x_above',vt:'ind',val:'',vi:'ema20',lg:'AND'},
    {id:_id++,ind:'vol_ratio',op:'gt',vt:'num',val:'1.2',vi:null,lg:'AND'},
  ]},
  { name:'RSI Momentum', desc:'RSI > 60 + ADX > 25 + above EMA20', conds:[
    {id:_id++,ind:'rsi14',op:'gt',vt:'num',val:'60',vi:null,lg:'AND'},
    {id:_id++,ind:'adx14',op:'gt',vt:'num',val:'25',vi:null,lg:'AND'},
    {id:_id++,ind:'close',op:'gt',vt:'ind',val:'',vi:'ema20',lg:'AND'},
  ]},
  { name:'Volume Surge', desc:'Vol Ratio > 2.5x with price up > 2%', conds:[
    {id:_id++,ind:'vol_ratio',op:'gt',vt:'num',val:'2.5',vi:null,lg:'AND'},
    {id:_id++,ind:'pct_chg',op:'gt',vt:'num',val:'2',vi:null,lg:'AND'},
    {id:_id++,ind:'close',op:'gt',vt:'ind',val:'',vi:'ema20',lg:'AND'},
  ]},
  { name:'BB Squeeze', desc:'Bandwidth < 0.08 with ADX trending', conds:[
    {id:_id++,ind:'bb_bw',op:'lt',vt:'num',val:'0.08',vi:null,lg:'AND'},
    {id:_id++,ind:'adx14',op:'gt',vt:'num',val:'20',vi:null,lg:'AND'},
  ]},
  { name:'RS Leader', desc:'RS vs NIFTY > 1.05 with rising RS', conds:[
    {id:_id++,ind:'rs_nifty',op:'gt',vt:'num',val:'1.05',vi:null,lg:'AND'},
    {id:_id++,ind:'rs_nifty5d',op:'gt',vt:'num',val:'0',vi:null,lg:'AND'},
    {id:_id++,ind:'rsi14',op:'gt',vt:'num',val:'55',vi:null,lg:'AND'},
  ]},
  { name:'Inside Bar Trend', desc:'Inside bar with ADX > 25 above EMA50', conds:[
    {id:_id++,ind:'inside_bar',op:'eq',vt:'bool',val:'true',vi:null,lg:'AND'},
    {id:_id++,ind:'adx14',op:'gt',vt:'num',val:'25',vi:null,lg:'AND'},
    {id:_id++,ind:'close',op:'gt',vt:'ind',val:'',vi:'ema50',lg:'AND'},
  ]},
];

function ScannerView({ initScan, scans, setScans, setActiveId }) {
  const isNew = !initScan?.id;
  const [name, setName] = useState(initScan?.name || 'New Scan');
  const [desc, setDesc] = useState(initScan?.desc || '');
  const [uni, setUni] = useState(initScan?.uni || 'NIFTY 200');
  const [tf, setTf] = useState(initScan?.tf || 'Daily');
  const [conds, setConds] = useState(() => initScan?.conds ? initScan.conds.map(c => ({...c})) : [mkCond()]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [sortBy, setSortBy] = useState('rs');
  const [color] = useState(initScan?.color || C.acc);

  const upd = (id, u) => setConds(cs => cs.map(c => c.id===id ? u : c));
  const del = id => setConds(cs => cs.filter(c => c.id !== id));
  const addCond = () => setConds(cs => [...cs, mkCond()]);

  const run = async () => {
    setLoading(true); setResults(null);
    try {
      const res = await apiFetch('/api/scan/run', {
        method:'POST',
        body: JSON.stringify({ name, universe:uni, timeframe:tf, conditions:conds }),
      });
      if (res.ok) { const d = await res.json(); setResults(d.results); }
      else throw new Error();
    } catch {
      await new Promise(r => setTimeout(r, 1800));
      const n = Math.min(4 + (conds.length % 5) + 3, STOCKS.length);
      setResults([...STOCKS].slice(0, n));
    }
    setLoading(false);
  };

  const save = () => {
    const sc = { id:initScan?.id || Date.now(), name, desc, uni, tf, conds, color, lastRun:'Just now', cnt:results?.length || initScan?.cnt || 0 };
    setScans(prev => isNew ? [...prev, sc] : prev.map(s => s.id===sc.id ? sc : s));
    setActiveId(sc.id); setSaved(true); setTimeout(() => setSaved(false), 2500);
  };

  const applyTemplate = (t) => {
    setConds(t.conds.map(c => ({...c, id:_id++})));
    setResults(null);
  };

  const sorted = results
    ? [...results].sort((a, b) => {
        const get = (r, live, mock) => r[live] ?? r[mock] ?? 0;
        if (sortBy === 'rs')  return get(b,'rs_nifty','rs')   - get(a,'rs_nifty','rs');
        if (sortBy === 'rsi') return get(b,'rsi14','rsi')     - get(a,'rsi14','rsi');
        if (sortBy === 'vr')  return get(b,'vol_ratio','vr')  - get(a,'vol_ratio','vr');
        return get(b,'change','c') - get(a,'change','c');
      })
    : null;

  const Inp = ({ val, setter, ph='' }) => (
    <input value={val} onChange={e => setter(e.target.value)} placeholder={ph}
      style={{ ...inpSt, fontFamily:C.fn, fontSize:13 }} />
  );
  const Sel = ({ val, opts, setter }) => (
    <select value={val} onChange={e => setter(e.target.value)} style={{ ...inpSt, cursor:'pointer', fontFamily:C.fn, fontSize:13 }}>
      {opts.map(o => <option key={o}>{o}</option>)}
    </select>
  );

  return (
    <div style={{ padding:24, maxWidth:1100 }}>
      {/* Top bar */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:22 }}>
        <div>
          <h1 style={{ fontFamily:C.fn, fontSize:20, fontWeight:800, color:C.tx }}>{isNew ? 'New Scanner' : `Edit: ${name}`}</h1>
          <p style={{ fontFamily:C.mo, fontSize:10, color:C.mu, marginTop:4 }}>Build conditions · Run scan · Save to dashboard</p>
        </div>
        <div style={{ display:'flex', gap:10 }}>
          <button onClick={save} className="btn"
            style={{ padding:'8px 18px', background:saved?`${C.up}18`:'#161B22', border:`1px solid ${saved?C.up:'#21262D'}`, borderRadius:6, cursor:'pointer', fontFamily:C.fn, fontSize:12, fontWeight:700, color:saved?C.up:C.tx }}>
            {saved ? '✓ Saved' : '↑ Save'}
          </button>
          <button onClick={run} disabled={loading} className="btn"
            style={{ padding:'8px 22px', background:loading?`${C.acc}25`:C.acc, border:'none', borderRadius:6, cursor:'pointer', fontFamily:C.fn, fontSize:12, fontWeight:800, color:loading?C.acc:'#000' }}>
            {loading ? '◌ Scanning...' : '▶ Run Scan'}
          </button>
        </div>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 295px', gap:18 }}>
        {/* Left: Config + Conditions */}
        <div>
          {/* Metadata */}
          <div style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, padding:18, marginBottom:16 }}>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:12 }}>
              <div><Lbl>Scan Name</Lbl><Inp val={name} setter={setName} ph="e.g. Momentum Breakout" /></div>
              <div><Lbl>Description</Lbl><Inp val={desc} setter={setDesc} ph="Optional description" /></div>
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
              <div><Lbl>Universe</Lbl><Sel val={uni} opts={UNIVERSES} setter={setUni} /></div>
              <div><Lbl>Timeframe</Lbl><Sel val={tf} opts={TIMEFRAMES} setter={setTf} /></div>
            </div>
          </div>

          {/* Condition Builder */}
          <div style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, padding:18 }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
              <span style={{ fontFamily:C.fn, fontSize:13, fontWeight:700, color:C.tx }}>Filter Conditions</span>
              <span style={{ fontFamily:C.mo, fontSize:9, color:C.mu }}>{conds.length} condition{conds.length !== 1 ? 's' : ''}</span>
            </div>
            {conds.map((c, i) => (
              <CondRow key={c.id} cond={c} isFirst={i===0}
                onChange={u => upd(c.id, u)}
                onDel={() => del(c.id)} />
            ))}
            <button onClick={addCond}
              style={{ marginTop:10, width:'100%', padding:'7px 0', background:'transparent', border:'1px dashed #21262D', borderRadius:6, cursor:'pointer', fontFamily:C.mo, fontSize:10, color:C.mu }}>
              + Add Condition
            </button>
          </div>
        </div>

        {/* Right: Logic Preview + Templates */}
        <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
          {/* Logic Preview */}
          <div style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, padding:16 }}>
            <Lbl>Logic Preview</Lbl>
            <div style={{ fontFamily:C.mo, fontSize:10, lineHeight:1.9 }}>
              {conds.map((c, i) => {
                const ind = getInd(c.ind);
                const op = OPS.find(o => o.v === c.op);
                const vi = getInd(c.vi);
                return (
                  <div key={c.id}>
                    {i > 0 && <span style={{ color:c.lg==='AND'?C.acc:C.wa }}>{c.lg} </span>}
                    <span style={{ color:C.acc }}>{ind.l}</span>
                    {!['bool'].includes(ind.t) && <> <span style={{ color:C.wa }}>{op?.l||c.op}</span> <span style={{ color:C.pu }}>{c.vt==='ind' ? vi.l : (c.val || '...')}</span></>}
                    {ind.t === 'bool' && <span style={{ color:C.pu }}> = TRUE</span>}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Templates */}
          <div style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, padding:16, flex:1 }}>
            <Lbl>Quick Templates</Lbl>
            {TEMPLATES.map((t, i) => (
              <button key={i} onClick={() => applyTemplate(t)} className="btn"
                style={{ display:'block', width:'100%', textAlign:'left', padding:'8px 10px', background:'transparent', border:'none', borderRadius:6, cursor:'pointer', marginBottom:2 }}>
                <div style={{ fontFamily:C.fn, fontSize:12, fontWeight:600, color:C.tx }}>{t.name}</div>
                <div style={{ fontFamily:C.mo, fontSize:9, color:C.mu, marginTop:2 }}>{t.desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Scanning indicator */}
      {loading && (
        <div style={{ marginTop:20, padding:28, background:C.sf, border:'1px solid #21262D', borderRadius:10, textAlign:'center' }}>
          <div style={{ fontFamily:C.mo, fontSize:12, color:C.acc, marginBottom:8 }}>◌ Scanning {uni}...</div>
          <div style={{ fontFamily:C.mo, fontSize:9, color:C.mu }}>Fetching OHLCV → Computing indicators → Applying {conds.length} filter{conds.length!==1?'s':''}</div>
        </div>
      )}

      {/* Results Table */}
      {sorted && !loading && (
        <div style={{ marginTop:20 }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
            <span style={{ fontFamily:C.fn, fontSize:14, fontWeight:700, color:C.tx }}>
              Results — <span style={{ color:C.acc }}>{sorted.length} stocks matched</span>
            </span>
            <div style={{ display:'flex', alignItems:'center', gap:8 }}>
              <span style={{ fontFamily:C.mo, fontSize:9, color:C.mu }}>Sort by:</span>
              {[['rs','RS/N'],['rsi','RSI'],['vr','Vol×'],['c','Chg%']].map(([v,l]) => (
                <button key={v} onClick={() => setSortBy(v)} className="btn"
                  style={{ padding:'3px 10px', background:sortBy===v?`${C.acc}18`:'transparent', border:`1px solid ${sortBy===v?C.acc:'#21262D'}`, borderRadius:4, cursor:'pointer', fontFamily:C.mo, fontSize:9, color:sortBy===v?C.acc:C.mu }}>
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, overflow:'hidden' }}>
            <table style={{ width:'100%', borderCollapse:'collapse' }}>
              <thead>
                <tr style={{ borderBottom:'1px solid #21262D' }}>
                  {['#','Symbol','Price','Chg %','RSI(14)','ADX(14)','Vol ×','RS/NIFTY','BB BW','Setup'].map(h => (
                    <th key={h} style={{ padding:'8px 12px', fontFamily:C.mo, fontSize:8, color:C.mu, textAlign:'left', fontWeight:400, letterSpacing:1 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => {
                  const sym   = r.symbol    ?? r.s   ?? '—';
                  const sec   = r.sector    ?? r.sec  ?? '—';
                  const price = r.price     ?? r.p   ?? 0;
                  const chg   = r.change    ?? r.c   ?? 0;
                  const rsi   = r.rsi14     ?? r.rsi  ?? 0;
                  const adx   = r.adx14     ?? r.adx  ?? 0;
                  const vr    = r.vol_ratio ?? r.vr  ?? 0;
                  const rs    = r.rs_nifty  ?? r.rs  ?? 0;
                  const bw    = r.bb_bw     ?? r.bw  ?? 0;
                  const setup = r.setup     ?? 'Signal';
                  return (
                    <tr key={i} className="hov" style={{ borderBottom:'1px solid #21262D40' }}>
                      <td style={{ padding:'8px 12px', fontFamily:C.mo, fontSize:10, color:C.mu }}>{i + 1}</td>
                      <td style={{ padding:'8px 12px' }}>
                        <div style={{ fontFamily:C.fn, fontSize:13, fontWeight:700, color:C.tx }}>{sym}</div>
                        <div style={{ fontFamily:C.mo, fontSize:8, color:C.mu }}>{sec}</div>
                      </td>
                      <td style={{ padding:'8px 12px', fontFamily:C.mo, fontSize:11, color:C.tx }}>₹{Number(price).toLocaleString('en-IN')}</td>
                      <td style={{ padding:'8px 12px', fontFamily:C.mo, fontSize:11, color:chg>=0?C.up:C.dn }}>{chg>=0?'▲':'▼'}{Math.abs(Number(chg)).toFixed(2)}%</td>
                      <td style={{ padding:'8px 12px', fontFamily:C.mo, fontSize:11, color:rsi>70?C.wa:C.tx }}>{Number(rsi).toFixed(1)}</td>
                      <td style={{ padding:'8px 12px', fontFamily:C.mo, fontSize:11, color:adx>30?C.acc:C.tx }}>{Number(adx).toFixed(1)}</td>
                      <td style={{ padding:'8px 12px', fontFamily:C.mo, fontSize:11, color:vr>2?C.acc:C.tx }}>{Number(vr).toFixed(2)}×</td>
                      <td style={{ padding:'8px 12px', fontFamily:C.mo, fontSize:11, color:rs>1.1?C.up:rs>1?C.acc:C.mu }}>{rs ? Number(rs).toFixed(3) : '—'}</td>
                      <td style={{ padding:'8px 12px', fontFamily:C.mo, fontSize:11, color:bw<0.06&&bw>0?C.wa:C.mu }}>{bw ? Number(bw).toFixed(3) : '—'}</td>
                      <td style={{ padding:'8px 12px' }}><Chip label={setup} color={setup==='Breakout'?C.acc:setup==='Momentum'?C.pu:C.mu} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════ BACKTEST VIEW ═══════════════════════
function BacktestView({ scans }) {
  const [scanId, setScanId] = useState(scans[0]?.id || 1);
  const [from, setFrom] = useState('2024-01-01');
  const [to, setTo] = useState('2025-04-01');
  const [exitRule, setExitRule] = useState('After N Days');
  const [exitDays, setExitDays] = useState('8');
  const [sl, setSl] = useState('3');
  const [rrMin, setRrMin] = useState('2');
  const [ran, setRan] = useState(false);
  const [running, setRunning] = useState(false);
  const [filter, setFilter] = useState('ALL');

  const runBT = async () => {
    setRunning(true); setRan(false);
    try {
      const res = await apiFetch('/api/backtest/run', {
        method:'POST',
        body: JSON.stringify({ scan_id:scanId, from, to, exit_rule:exitRule, exit_days:exitDays, stop_loss:sl, min_rr:rrMin }),
      });
      if (!res.ok) throw new Error();
    } catch { /* fall through to mock */ }
    await new Promise(r => setTimeout(r, 2200));
    setRunning(false); setRan(true);
  };

  const visibleTrades = filter === 'ALL' ? TRADES : TRADES.filter(t => t.res === filter);

  const Inp = ({ val, setter, type='number', w='100%' }) => (
    <input type={type} value={val} onChange={e => setter(e.target.value)}
      style={{ ...inpSt, width:w, fontFamily:C.mo, fontSize:12 }} />
  );

  return (
    <div style={{ padding:24, maxWidth:1100 }}>
      <div style={{ marginBottom:22 }}>
        <h1 style={{ fontFamily:C.fn, fontSize:20, fontWeight:800, color:C.tx }}>Strategy Backtester</h1>
        <p style={{ fontFamily:C.mo, fontSize:10, color:C.mu, marginTop:4 }}>Simulate any saved scanner on historical NSE data</p>
      </div>

      {/* Config */}
      <div style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, padding:20, marginBottom:20 }}>
        <Lbl>Configuration</Lbl>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:14, marginTop:10 }}>
          <div>
            <Lbl>Scanner to Test</Lbl>
            <select value={scanId} onChange={e => setScanId(Number(e.target.value))} style={{ ...inpSt, cursor:'pointer', fontFamily:C.fn, fontSize:13 }}>
              {scans.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div><Lbl>From Date</Lbl><Inp val={from} setter={setFrom} type="date" /></div>
          <div><Lbl>To Date</Lbl><Inp val={to} setter={setTo} type="date" /></div>
          <div>
            <Lbl>Exit Rule</Lbl>
            <select value={exitRule} onChange={e => setExitRule(e.target.value)} style={{ ...inpSt, cursor:'pointer', fontFamily:C.fn, fontSize:13 }}>
              {EXIT_RULES.map(r => <option key={r}>{r}</option>)}
            </select>
          </div>
          <div><Lbl>Stop Loss (%)</Lbl><Inp val={sl} setter={setSl} /></div>
          <div><Lbl>Min R:R Required</Lbl><Inp val={rrMin} setter={setRrMin} /></div>
        </div>
        <div style={{ marginTop:18, display:'flex', alignItems:'center', gap:14 }}>
          <button onClick={runBT} disabled={running} className="btn"
            style={{ padding:'9px 28px', background:running?`${C.acc}25`:C.acc, border:'none', borderRadius:6, cursor:'pointer', fontFamily:C.fn, fontSize:13, fontWeight:800, color:running?C.acc:'#000' }}>
            {running ? '◌ Running Backtest...' : '▶ Run Backtest'}
          </button>
          {ran && <span style={{ fontFamily:C.mo, fontSize:10, color:C.up }}>✓ Complete — {TRADES.length} trades analyzed</span>}
        </div>
      </div>

      {ran && (
        <>
          {/* Performance Stats */}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(6,1fr)', gap:12, marginBottom:20 }}>
            {[
              { l:'Win Rate', v:`${STATS.winRate}%`, cl:C.up },
              { l:'Avg R:R', v:STATS.avgRR, cl:C.acc },
              { l:'Expectancy', v:`${STATS.expectancy}%`, cl:C.acc },
              { l:'Max Drawdown', v:`${STATS.maxDD}%`, cl:C.dn },
              { l:'Sharpe Ratio', v:STATS.sharpe, cl:C.pu },
              { l:'Total Trades', v:STATS.total, cl:C.tx },
            ].map((s, i) => (
              <div key={i} style={{ background:C.sf, border:'1px solid #21262D', borderRadius:8, padding:'12px 14px' }}>
                <div style={{ fontFamily:C.mo, fontSize:8, color:C.mu, letterSpacing:1, textTransform:'uppercase', marginBottom:6 }}>{s.l}</div>
                <div style={{ fontFamily:C.mo, fontSize:22, fontWeight:600, color:s.cl }}>{s.v}</div>
              </div>
            ))}
          </div>

          {/* Equity Curve */}
          <div style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, padding:20, marginBottom:20 }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
              <span style={{ fontFamily:C.fn, fontSize:13, fontWeight:700, color:C.tx }}>Equity Curve</span>
              <div style={{ display:'flex', gap:20 }}>
                <span style={{ fontFamily:C.mo, fontSize:10, color:C.mu }}>Capital: <span style={{ color:C.tx }}>₹1,00,000</span></span>
                <span style={{ fontFamily:C.mo, fontSize:10, color:C.mu }}>Final: <span style={{ color:C.up }}>₹{FINAL_VAL.toLocaleString('en-IN')}</span></span>
                <span style={{ fontFamily:C.mo, fontSize:10, color:C.mu }}>Return: <span style={{ color:C.up }}>+{((FINAL_VAL-100000)/100000*100).toFixed(1)}%</span></span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={EQUITY} margin={{ top:5, right:5, bottom:0, left:10 }}>
                <defs>
                  <linearGradient id="eq_grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={C.acc} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={C.acc} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262D" />
                <XAxis dataKey="date" tick={{ fontFamily:C.mo, fontSize:8, fill:C.mu }} tickLine={false} axisLine={false} interval={9} />
                <YAxis tick={{ fontFamily:C.mo, fontSize:8, fill:C.mu }} tickLine={false} axisLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                <Tooltip content={<EqTooltip />} />
                <ReferenceLine y={100000} stroke="#21262D" strokeDasharray="4 4" />
                <Area type="monotone" dataKey="value" stroke={C.acc} strokeWidth={2} fill="url(#eq_grad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Trade Log */}
          <div style={{ background:C.sf, border:'1px solid #21262D', borderRadius:10, overflow:'hidden' }}>
            <div style={{ padding:'14px 18px', borderBottom:'1px solid #21262D', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
              <div style={{ display:'flex', alignItems:'center', gap:12 }}>
                <span style={{ fontFamily:C.fn, fontSize:13, fontWeight:700, color:C.tx }}>Trade Log</span>
                <span style={{ fontFamily:C.mo, fontSize:9, color:C.mu }}>{STATS.wins}W / {STATS.losses}L</span>
              </div>
              <div style={{ display:'flex', gap:6 }}>
                {['ALL','WIN','LOSS'].map(f => (
                  <button key={f} onClick={() => setFilter(f)} className="btn"
                    style={{ padding:'3px 10px', background:filter===f?`${f==='WIN'?C.up:f==='LOSS'?C.dn:C.acc}18`:'transparent', border:`1px solid ${filter===f?f==='WIN'?C.up:f==='LOSS'?C.dn:C.acc:'#21262D'}`, borderRadius:4, cursor:'pointer', fontFamily:C.mo, fontSize:9, color:filter===f?f==='WIN'?C.up:f==='LOSS'?C.dn:C.acc:C.mu }}>
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <table style={{ width:'100%', borderCollapse:'collapse' }}>
              <thead>
                <tr style={{ borderBottom:'1px solid #21262D' }}>
                  {['Date','Symbol','Entry','Exit','P&L %','R:R','Days Held','Result'].map(h => (
                    <th key={h} style={{ padding:'8px 16px', fontFamily:C.mo, fontSize:8, color:C.mu, textAlign:'left', fontWeight:400, letterSpacing:1 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleTrades.map((t, i) => (
                  <tr key={i} className="hov" style={{ borderBottom:'1px solid #21262D35' }}>
                    <td style={{ padding:'8px 16px', fontFamily:C.mo, fontSize:10, color:C.mu }}>{t.dt}</td>
                    <td style={{ padding:'8px 16px', fontFamily:C.fn, fontSize:13, fontWeight:700, color:C.tx }}>{t.sym}</td>
                    <td style={{ padding:'8px 16px', fontFamily:C.mo, fontSize:11, color:C.tx }}>₹{t.entry.toLocaleString()}</td>
                    <td style={{ padding:'8px 16px', fontFamily:C.mo, fontSize:11, color:C.tx }}>₹{t.exit.toLocaleString()}</td>
                    <td style={{ padding:'8px 16px', fontFamily:C.mo, fontSize:12, fontWeight:600, color:t.pnl>=0?C.up:C.dn }}>{t.pnl>=0?'+':''}{t.pnl}%</td>
                    <td style={{ padding:'8px 16px', fontFamily:C.mo, fontSize:11, color:t.rr>=2?C.acc:t.rr>=1.5?C.tx:C.dn }}>{t.rr}:1</td>
                    <td style={{ padding:'8px 16px', fontFamily:C.mo, fontSize:11, color:C.mu }}>{t.days}d</td>
                    <td style={{ padding:'8px 16px' }}><Chip label={t.res} color={t.res==='WIN'?C.up:C.dn} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// ═══════════════════════ LOGIN GATE ═══════════════════════
// Add / remove users here. Passwords are hashed in prod via backend.
// For now: simple client-side check — good enough for private tools.
const USERS = {
  "arnav":  "quantedge2024",   // change these
  "guest":  "nse@readonly",
};

const LOGIN_CSS = `
.login-input { width:100%; padding:11px 14px; background:#0D1117; border:1px solid #21262D;
  border-radius:7px; color:#E6EDF3; font-family:'JetBrains Mono',monospace; font-size:13px;
  outline:none; transition:border 0.15s; box-sizing:border-box; }
.login-input:focus { border-color:#00D68F; }
.login-btn { width:100%; padding:12px; background:#00D68F; border:none; border-radius:7px;
  color:#000; font-family:'Outfit',sans-serif; font-size:14px; font-weight:800;
  cursor:pointer; transition:opacity 0.12s; margin-top:8px; }
.login-btn:hover { opacity:0.87; }
.shake { animation: shake 0.35s ease; }
@keyframes shake {
  0%,100%{transform:translateX(0)} 20%{transform:translateX(-8px)}
  40%{transform:translateX(8px)} 60%{transform:translateX(-6px)} 80%{transform:translateX(4px)}
}
`;

function LoginGate({ onLogin }) {
  const [user, setUser]   = useState('');
  const [pass, setPass]   = useState('');
  const [err,  setErr]    = useState('');
  const [shake, setShake] = useState(false);
  const [show, setShow]   = useState(false);

  const attempt = () => {
    const u = user.trim().toLowerCase();
    if (USERS[u] && USERS[u] === pass) {
      sessionStorage.setItem('qe_auth', u);
      onLogin(u);
    } else {
      setErr('Invalid username or password');
      setShake(true);
      setTimeout(() => setShake(false), 400);
    }
  };

  const onKey = e => { if (e.key === 'Enter') attempt(); };

  return (
    <div style={{ minHeight:'100vh', background:'#070B14', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:"'Outfit',sans-serif" }}>
      <style>{CSS + LOGIN_CSS}</style>
      <div style={{ width:360 }}>
        {/* Logo */}
        <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:36 }}>
          <div style={{ width:36, height:36, background:'#00D68F', borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center' }}>
            <span style={{ fontWeight:800, fontSize:16, color:'#000' }}>Q</span>
          </div>
          <div>
            <div style={{ fontSize:20, fontWeight:800, color:'#E6EDF3', letterSpacing:0.3 }}>
              QuantEdge <span style={{ color:'#00D68F' }}>NSE</span>
            </div>
            <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:9, color:'#7D8590', letterSpacing:1 }}>INSTITUTIONAL TRADING TERMINAL</div>
          </div>
        </div>

        {/* Card */}
        <div className={shake ? 'shake' : ''} style={{ background:'#0D1117', border:'1px solid #21262D', borderRadius:12, padding:28 }}>
          <div style={{ fontSize:15, fontWeight:700, color:'#E6EDF3', marginBottom:4 }}>Sign In</div>
          <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:9, color:'#7D8590', marginBottom:24 }}>Private access only</div>

          <div style={{ marginBottom:14 }}>
            <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:9, color:'#7D8590', letterSpacing:1, marginBottom:7 }}>USERNAME</div>
            <input className="login-input" value={user} onChange={e => { setUser(e.target.value); setErr(''); }}
              onKeyDown={onKey} placeholder="your username" autoComplete="username" />
          </div>

          <div style={{ marginBottom:20 }}>
            <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:9, color:'#7D8590', letterSpacing:1, marginBottom:7 }}>PASSWORD</div>
            <div style={{ position:'relative' }}>
              <input className="login-input" type={show?'text':'password'} value={pass}
                onChange={e => { setPass(e.target.value); setErr(''); }}
                onKeyDown={onKey} placeholder="••••••••" autoComplete="current-password"
                style={{ paddingRight:44 }} />
              <button onClick={() => setShow(s => !s)}
                style={{ position:'absolute', right:12, top:'50%', transform:'translateY(-50%)', background:'none', border:'none', cursor:'pointer', fontFamily:"'JetBrains Mono',monospace", fontSize:9, color:'#7D8590' }}>
                {show ? 'HIDE' : 'SHOW'}
              </button>
            </div>
          </div>

          {err && (
            <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:10, color:'#F85149', marginBottom:14, padding:'8px 12px', background:'#F8514912', borderRadius:5, border:'1px solid #F8514930' }}>
              ✕ {err}
            </div>
          )}

          <button className="login-btn" onClick={attempt}>ENTER TERMINAL →</button>
        </div>

        <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:8, color:'#7D8590', textAlign:'center', marginTop:20, letterSpacing:0.8 }}>
          ACCESS RESTRICTED · AUTHORISED USERS ONLY
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════ MAIN APP ═══════════════════════
export default function App() {
  const saved   = sessionStorage.getItem('qe_auth');
  const [authed, setAuthed] = useState(!!saved);
  const [tab, setTab] = useState('dashboard');
  const [scans, setScans] = useState(INIT_SCANS);
  const [activeScan, setActiveScan] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const isMobile = useIsMobile();

  if (!authed) return <LoginGate onLogin={() => setAuthed(true)} />;

  const handleNew    = () => { setActiveScan(null); setActiveId(null); setTab('scanner'); };
  const handleSelect = sc => { setActiveScan(sc); setActiveId(sc.id); };
  const handleLogout = () => { sessionStorage.removeItem('qe_auth'); setAuthed(false); };

  const NAV = [
    {id:'dashboard', icon:'▪', label:'Dashboard'},
    {id:'scanner',   icon:'◈', label:'Scanner'},
    {id:'backtest',  icon:'◉', label:'Backtest'},
  ];

  return (
    <div style={{ fontFamily:C.fn, background:C.bg, minHeight:'100vh', color:C.tx }}>
      <style>{CSS}</style>
      <Header onLogout={handleLogout} />
      <div style={{ display:'flex' }}>
        <Sidebar scans={scans} activeId={activeId} onSelect={handleSelect} onNew={handleNew} tab={tab} setTab={setTab} />
        <main className="main-content" style={{ flex:1, overflowY:'auto', maxHeight:'calc(100vh - 50px)', minWidth:0 }}>
          {tab === 'dashboard' && <Dashboard scans={scans} onSelect={handleSelect} onNew={handleNew} setTab={setTab} />}
          {tab === 'scanner'   && <ScannerView key={activeScan?.id || 'new'} initScan={activeScan} scans={scans} setScans={setScans} setActiveId={setActiveId} />}
          {tab === 'backtest'  && <BacktestView scans={scans} />}
        </main>
      </div>

      {/* Mobile bottom navigation */}
      {isMobile && (
        <div className="mobile-nav">
          {NAV.map(n => (
            <button key={n.id} onClick={() => setTab(n.id)}
              style={{ flex:1, background:'none', border:'none', cursor:'pointer', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:3,
                borderTop:`2px solid ${tab===n.id ? C.acc : 'transparent'}`, paddingTop:2 }}>
              <span style={{ fontSize:14, color:tab===n.id ? C.acc : C.mu }}>{n.icon}</span>
              <span style={{ fontFamily:C.mo, fontSize:8, color:tab===n.id ? C.acc : C.mu, letterSpacing:0.5 }}>{n.label}</span>
            </button>
          ))}
          <button onClick={handleNew}
            style={{ flex:1, background:'none', border:'none', cursor:'pointer', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:3 }}>
            <span style={{ fontSize:20, color:C.acc, lineHeight:1 }}>+</span>
            <span style={{ fontFamily:C.mo, fontSize:8, color:C.acc, letterSpacing:0.5 }}>NEW SCAN</span>
          </button>
        </div>
      )}
    </div>
  );
}
