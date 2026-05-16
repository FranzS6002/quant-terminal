import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 0. KONFIGURATION & STANDARDEINSTELLUNGEN
# ==========================================
st.set_page_config(page_title="Hybrid Quant Terminal", page_icon="🏛️", layout="wide")

# 🔥 NEU: DER TÜRSTEHER (PASSWORTSCHUTZ) 🔥
def check_password():
    def password_entered():
        # Vergleicht die Eingabe mit dem geheimen Passwort auf dem Server
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Passwort aus dem Zwischenspeicher löschen
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Ersteingabe
        st.text_input("🔒 Bitte Passwort eingeben, um das Terminal zu entsperren", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Falsches Passwort
        st.text_input("🔒 Bitte Passwort eingeben, um das Terminal zu entsperren", type="password", on_change=password_entered, key="password")
        st.error("😕 Falsches Passwort. Zugriff verweigert.")
        return False
    return True

if not check_password():
    st.stop()  # HIER STOPPT DAS SKRIPT! Alles darunter wird erst geladen, wenn das Passwort stimmt.

# ==========================================
# 🔥 DEIN KONTROLLZENTRUM FÜR DEN NEUSTART 🔥
# Ändere hier 'True' auf 'False', wenn etwas beim kompletten App-Start standardmäßig AUS sein soll.
# ==========================================
DEFAULT_SHOW_TODAY = True
DEFAULT_SHOW_TRACKING = True
DEFAULT_SHOW_PERF = True
DEFAULT_SHOW_SCREENER = True
DEFAULT_SHOW_CHART = False      # <--- Kapitalkurve beim Neustart dauerhaft AUS!
DEFAULT_SHOW_LOG = True
DEFAULT_SHOW_UNIVERSE = False
DEFAULT_SHOW_MANUAL = False

# ==========================================
# 1. UNIVERSEN DEFINIEREN
# ==========================================
sat_tickers = {
    "JEDI.DE": "Space Innovators", "HNSC.MI": "Semiconductors", "ETLX.DE": "L&G Gold Min.",
    "U3O8.DE": "Uranium Miners", "1IZ1.F": "Scottish Mortgage", "LYM9.DE": "MSCI New Energy",
    "GRID.DE": "Smart Grid Infrastr.", "4MMR.DE": "Glob.X Def.Tech", "DFEN.DE": "VanEck Defense",
    "ARAW.DE": "Raw Materials", "QUTM.DE": "Quantum Comp.", "MTVR.DE": "Metaverse",
    "IS0D.DE": "Oil & Gas E&P", "V9N.DE": "Data Centers", "IEVD.DE": "EV Driving Tech",
    "XMOV.DE": "Future Mobility", "XAIX.DE": "AI & Big Data", "ZPRR.DE": "Russell 2000",
    "EXSC.DE": "Europe Small", "2B76.DE": "Robo & Automation",  
    "WTAI.DE": "Applied AI", "EUFN": "Europe Financials", "GNOM.MI": "Genomics",
    "XDPE.DE": "Private Equity", "2B77.DE": "Ageing Pop", "GOAI.DE": "Robotics & AI",
    "IQQQ.DE": "Water", "REUSE.MI": "Circular Economy", "SNSR.MI": "IoT",
    "XUFN.DE": "USA Financials", "XNGI.DE": "Next Gen", "CLOU.MI": "Cloud Computing",
    "XFNT.DE": "Fintech Innovation", "BTC-USD": "Bitcoin", "IGV": "Software B2B",
    "HYCN.DE": "Global X Hydrogen", "BATE.DE": "Battery Value Chain", "AMEC.DE": "MSCI Smart Cities"
}

core_tickers = {
    "SXR8.DE": "S&P 500", 
    "EXSA.DE": "Europe 600",
    "EUNN.DE": "MSCI Japan", 
    "IS3N.DE": "Emerging Markets",
    "EUNA.DE": "Global Bonds (Hedged)", 
    "8PSG.DE": "Gold (Invesco)",
    "TRET.DE": "Global Real Estate", 
    "SXRS.DE": "Commodities"
}

bench_tickers = {
    "EUNL.DE": "MSCI World", 
    "EXXT.DE": "Nasdaq 100",
    "SXR8.DE": "S&P 500"
}

# ==========================================
# 2. ZENTRALER DATEN-LOADER
# ==========================================
@st.cache_data(ttl=3600)
def load_data(ticker_dict, is_benchmark=False, use_max=False):
    df_list = []
    for tkr, name in ticker_dict.items():
        try:
            if use_max:
                temp_df = yf.Ticker(tkr).history(period="max")
            else:
                temp_df = yf.Ticker(tkr).history(start="2014-01-01")
                
            if not temp_df.empty and len(temp_df) > 50:
                series = temp_df['Close']
                series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
                series = series[~series.index.duplicated(keep='last')]
                series.name = tkr if not is_benchmark else name
                df_list.append(series)
        except: pass
    if df_list:
        res = pd.concat(df_list, axis=1).ffill().dropna(how='all')
        return res[res.index.dayofweek < 5]
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_gpo_benchmark():
    today_str = datetime.today().strftime('%Y-%m-%d')
    start_date = "2014-01-01" 
    gpo_url = f"https://api.extraetf.com/customer-api/ic/chart/?isin=AT0000A2B4T3&data_type=nav&date_from={start_date}&date_to={today_str}"
    headers = {
        "User-Agent": "Mozilla/5.0", 
        "Referer": "https://www.globalportfolio-one.com/"
    }
    
    try:
        response = requests.get(gpo_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", {})
            
            if "nav" in results and isinstance(results["nav"], list):
                gpo_df = pd.DataFrame(results["nav"])
            elif "series" in results and isinstance(results["series"], list):
                gpo_df = pd.DataFrame(results["series"])
            else:
                gpo_df = pd.DataFrame.from_dict(results, orient='index').reset_index()

            date_col = next((col for col in gpo_df.columns if 'date' in str(col).lower() or 'time' in str(col).lower()), gpo_df.columns[0])
            val_col = next((col for col in gpo_df.columns if str(col).lower() in ['nav', 'value', 'price', 'close', 0]), gpo_df.columns[-1])
            
            gpo_df = gpo_df[[date_col, val_col]].copy()
            gpo_df.columns = ["Date", "Close"]
            
            if pd.api.types.is_numeric_dtype(gpo_df["Date"]):
                gpo_df["Date"] = pd.to_datetime(gpo_df["Date"], unit="ms")
            else:
                gpo_df["Date"] = pd.to_datetime(gpo_df["Date"])
                
            gpo_series = gpo_df.set_index("Date")["Close"]
            gpo_series.index = gpo_series.index.tz_localize(None).normalize()
            gpo_series = gpo_series[~gpo_series.index.duplicated(keep='last')]
            gpo_series.name = "GPO (AT...4T3)" 
            return gpo_series
    except Exception as e:
        pass
    return pd.Series(dtype=float)

with st.spinner('Lade Marktdaten im Hintergrund...'):
    data_sat = load_data(sat_tickers, use_max=True)
    data_core = load_data(core_tickers, use_max=False)
    data_bench = load_data(bench_tickers, is_benchmark=True, use_max=True)
    
    gpo_data = load_gpo_benchmark()
    if not gpo_data.empty:
        data_bench = pd.concat([data_bench, gpo_data], axis=1).ffill().dropna(how='all')

# ==========================================
# 3. NAVIGATION (Die Sidebar)
# ==========================================
st.sidebar.title("🏛️ Master Terminal")
app_mode = st.sidebar.radio("🧭 Modus wählen:", ["🚀 Satelliten (Offensive)", "🏦 Core (Fundament)"])
st.sidebar.markdown("---")

# ==========================================
# 4. SYSTEM-LOGIK & UI (Dynamisch nach Modus)
# ==========================================
if app_mode == "🚀 Satelliten (Offensive)":
    st.title("🚀 Satelliten Master-System")
    st.markdown("Quantitatives Management-Dashboard | Die 50% Offensive")
    data = data_sat
    test_tickers = sat_tickers
    def_buy = 2; def_hyst = 2; def_sma = 85; def_puffer = 3.2
    default_start_date = datetime(2024, 1, 1)

elif app_mode == "🏦 Core (Fundament)":
    st.title("🏦 Core Master-System")
    st.markdown("Quantitatives Management-Dashboard | Das 50% All-Weather Fundament")
    data = data_core
    test_tickers = core_tickers
    def_buy = 3; def_hyst = 1; def_sma = 200; def_puffer = 2.8
    default_start_date = datetime(2021, 1, 1)

# --- Sidebar Parameter für das aktive System ---
st.sidebar.header("⚙️ Strategie-Einstellungen")
BUY_RANK = st.sidebar.number_input("Anzahl ETFs (Buy Rank)", min_value=1, max_value=10, value=def_buy)
HOLD_RANK_BUFFER = st.sidebar.number_input("Hysterese-Puffer (+X)", min_value=0, max_value=5, value=def_hyst)
HOLD_RANK = BUY_RANK + HOLD_RANK_BUFFER

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Notbremsen-Setup")
SMA_DAYS = st.sidebar.number_input("SMA Zeitraum (Tage)", min_value=20, max_value=300, value=def_sma, step=1)
SMA_BUFFER_PCT = st.sidebar.number_input("SMA Notbremse-Puffer (%)", min_value=0.0, max_value=10.0, value=def_puffer, step=0.1)

st.sidebar.markdown("---")
st.sidebar.header("📅 Analyse-Zeitraum")
user_selected_date = st.sidebar.date_input("Startdatum der Performance-Messung", default_start_date)

eval_start_date = pd.to_datetime(user_selected_date)
perf_title = f"Seit {eval_start_date.strftime('%d.%m.%Y')}"

# --- Checkbox Session State greift jetzt auf deine Kontrollzentrum-Variablen zu ---
if "opt_today" not in st.session_state: st.session_state["opt_today"] = DEFAULT_SHOW_TODAY
if "opt_perf" not in st.session_state: st.session_state["opt_perf"] = DEFAULT_SHOW_PERF
if "opt_screener" not in st.session_state: st.session_state["opt_screener"] = DEFAULT_SHOW_SCREENER
if "opt_chart" not in st.session_state: st.session_state["opt_chart"] = DEFAULT_SHOW_CHART
if "opt_log" not in st.session_state: st.session_state["opt_log"] = DEFAULT_SHOW_LOG
if "opt_universe" not in st.session_state: st.session_state["opt_universe"] = DEFAULT_SHOW_UNIVERSE
if "opt_manual" not in st.session_state: st.session_state["opt_manual"] = DEFAULT_SHOW_MANUAL

st.sidebar.markdown("---")
st.sidebar.header("👁️ Anzeige-Optionen")
show_today = st.sidebar.checkbox("Tagesaktuelle Änderungen", key="opt_today")
show_perf = st.sidebar.checkbox(f"Performance ({perf_title})", key="opt_perf")
show_screener = st.sidebar.checkbox("Momentum Screener", key="opt_screener")
show_chart = st.sidebar.checkbox(f"Kapitalkurve ({perf_title})", key="opt_chart")
show_log = st.sidebar.checkbox("📋 System-Logbuch", key="opt_log")
show_universe = st.sidebar.checkbox("🌌 ETF-Universum", key="opt_universe")
show_manual = st.sidebar.checkbox("📘 System-Handbuch", key="opt_manual")

# --- Mathematische Kern-Maschine ---
if not data.empty:
    daily_returns = data.pct_change()
    sma = data.rolling(SMA_DAYS).mean()
    panic_level = sma * (1 - (SMA_BUFFER_PCT / 100))
    
    score = (data.pct_change(21) + data.pct_change(63) + data.pct_change(126) + data.pct_change(252)) / 4
    prev_ranks = score.shift(1).rank(axis=1, ascending=False, na_option='bottom')
    is_above_sma = (data.shift(1) > panic_level.shift(1))

    rebalance_days = data.iloc[::14].index
    
    daily_pos = pd.DataFrame(0.0, index=data.index, columns=data.columns)
    current_holdings = []

    for date in data.index:
        ranks = prev_ranks.loc[date]
        above = is_above_sma.loc[date]
        
        current_holdings = [tkr for tkr in current_holdings if above[tkr]]
        
        if date in rebalance_days:
            current_holdings = [tkr for tkr in current_holdings if ranks[tkr] <= HOLD_RANK]
            needed = BUY_RANK - len(current_holdings)
            if needed > 0:
                new_cands = [tkr for tkr in ranks.sort_values().index 
                             if tkr not in current_holdings 
                             and ranks[tkr] <= BUY_RANK 
                             and above[tkr]]
                current_holdings.extend(new_cands[:needed])
        
        if current_holdings:
            daily_pos.loc[date, current_holdings] = 1.0 / BUY_RANK

    final_pos = daily_pos
    last_date = data.index[-1]
    
    if eval_start_date < data.index[0]: eval_start_date = data.index[0]
    strat_returns = (daily_returns * final_pos).loc[eval_start_date:].sum(axis=1)
    equity = (1 + strat_returns).cumprod() * 100

    # --- UI Rendering ---
    col_status, col_dates = st.columns([2, 1])
    with col_status:
        st.subheader("💼 Aktuelles Depot")
        curr_pos = final_pos.iloc[-1]
        active_tkrs = curr_pos[curr_pos > 0].index.tolist()
        if not active_tkrs:
            st.error("PORTFOLIO IM CASH (Notbremsen aktiv)")
        else:
            p_list = []
            for tkr in active_tkrs:
                p, n = data.loc[last_date, tkr], panic_level.loc[last_date, tkr]
                p_list.append({"Asset": test_tickers.get(tkr, tkr), "Preis": f"{p:.2f} €", "Notbremse": f"{n:.2f} €", "Abstand": f"{((p/n)-1)*100:+.2f}%"})
            st.dataframe(pd.DataFrame(p_list), width='stretch')

    with col_dates:
        st.subheader("🗓️ Kommende Termine")
        last_reb = rebalance_days[rebalance_days <= last_date][-1]
        days_since = len(data.loc[last_reb:last_date]) - 1
        days_to_next = 14 - days_since
        if days_to_next <= 0:  
            days_to_next = 14
        target_date = datetime.now() + pd.offsets.BDay(days_to_next)
        st.write(f"**Nächstes Rebalancing:** {target_date.strftime('%d.%m.%Y')}")
        st.info(f"In {days_to_next} Handelstagen.")

    if show_today:
        st.markdown("---")
        st.subheader("🔔 Tagesaktuelle Änderungen")
        prev_pos_day = final_pos.iloc[-2]; curr_pos_day = final_pos.iloc[-1]
        changes = []
        for tkr in data.columns:
            name = test_tickers.get(tkr, tkr)
            if curr_pos_day[tkr] > 0 and prev_pos_day[tkr] == 0: changes.append(f"⭐ **KAUF:** {name}")
            elif curr_pos_day[tkr] == 0 and prev_pos_day[tkr] > 0: changes.append(f"🔴 **VERKAUF:** {name}")
        if not changes: st.write("⚪ Keine Änderungen heute.")
        else:
            for c in changes: st.write(c)

    if show_perf:
        st.markdown("---")
        st.subheader("📈 Performance-Vergleich")
        
        st.markdown("**⏱️ Kurzfristige Trend-Entwicklung (Rendite)**")
        track_kpis = []
        
        def get_track_kpis(eq_series, label):
            try:
                ret_1d = (eq_series.iloc[-1] / eq_series.iloc[-2]) - 1 if len(eq_series) >= 2 else np.nan
                ret_5d = (eq_series.iloc[-1] / eq_series.iloc[-6]) - 1 if len(eq_series) >= 6 else np.nan
                ret_21d = (eq_series.iloc[-1] / eq_series.iloc[-22]) - 1 if len(eq_series) >= 22 else np.nan
                return {
                    "Portfolio": label, 
                    "1 Tag": f"{ret_1d*100:+.2f} %" if pd.notna(ret_1d) else "---", 
                    "5 Tage": f"{ret_5d*100:+.2f} %" if pd.notna(ret_5d) else "---", 
                    "21 Tage": f"{ret_21d*100:+.2f} %" if pd.notna(ret_21d) else "---"
                }
            except:
                return {"Portfolio": label, "1 Tag": "---", "5 Tage": "---", "21 Tage": "---"}

        strat_returns_full = (daily_returns * final_pos).sum(axis=1)
        equity_full = (1 + strat_returns_full).cumprod() * 100
        
        track_kpis.append(get_track_kpis(equity_full, "🎯 System"))
        if not data_bench.empty:
            for col in data_bench.columns:
                if len(data_bench[col].dropna()) > 21:
                    track_kpis.append(get_track_kpis(data_bench[col].dropna(), f"🌍 {col}"))
        
        st.dataframe(pd.DataFrame(track_kpis), width='stretch')

        st.markdown(f"**📅 Langfristige KPIs & Drawdowns ({perf_title})**")
        pos_changes = final_pos.loc[eval_start_date:].diff().dropna()
        total_trades = (pos_changes.abs() > 0.01).sum().sum()
        
        def get_kpis(returns, eq, label, trades=None):
            ret_total = eq.iloc[-1] - 100
            vol = returns.std() * np.sqrt(252) * 100
            dd = (eq / eq.cummax() - 1).min() * 100
            annual = (1 + returns).groupby(returns.index.year).prod() - 1
            
            kpi = {"Portfolio": label, "Gesamt-Rendite": f"{ret_total:+.1f} %", "Vola p.a.": f"{vol:.1f} %", "Max DD": f"{dd:.1f} %"}
            if trades is not None: kpi["Trades (Total)"] = f"{int(trades)}"
            else: kpi["Trades (Total)"] = "---"
                
            for yr, val in annual.items(): kpi[f"Jahr {yr}"] = f"{val*100:+.1f} %"
            return kpi

        kpi_list = [get_kpis(strat_returns, equity, "🎯 System", total_trades)]
        if not data_bench.empty:
            bench_eval = data_bench.loc[eval_start_date:]
            for col in bench_eval.columns:
                b_ret = bench_eval[col].pct_change().dropna()
                if len(b_ret) > 10:
                    b_eq = (bench_eval[col] / bench_eval[col].iloc[0]) * 100
                    kpi_list.append(get_kpis(b_ret, b_eq, f"🌍 {col}"))
        
        st.dataframe(pd.DataFrame(kpi_list), width='stretch')   

    if show_screener:
        st.markdown("---")
        st.subheader("🏆 Momentum-Rangliste")
        
        current_scores = score.iloc[-1]
        
        # ==========================================
        # 🔥 GROßES MULTI-LINE-CHART FÜR DIE TOP 4 🔥
        # ==========================================
        st.markdown("**📈 Top 4 ETFs: 21-Tage Score-Trend**")
        
        # Die Ticker der Top 4 ETFs holen
        top_4_tkrs = current_scores.sort_values(ascending=False).index[:4]
        
        # Letzte 21 Tage des Scores extrahieren und in % umwandeln
        history_21d = score[top_4_tkrs].tail(21) * 100 
        
        # 1. Spaltennamen in lesbare Namen umwandeln (HIER WIRD CHART_DATA ERSTELLT)
        chart_data = history_21d.rename(columns=lambda x: test_tickers.get(x, x))
        
        # 2. Alle Datenpunkte im Chart auf 2 Nachkommastellen runden
        chart_data = chart_data.round(2)
        
        # 3. Den großen, interaktiven Chart zeichnen
        st.line_chart(chart_data)
        
        # ==========================================
        # BESTEHENDE RANGLISTE (inkl. 14 Tage)
        # ==========================================
        st.markdown("**📋 Komplette Score-Übersicht**")
        
        score_5d = score.iloc[-6] if len(score) >= 6 else pd.Series(np.nan, index=score.columns)
        score_14d = score.iloc[-15] if len(score) >= 15 else pd.Series(np.nan, index=score.columns)
        score_21d = score.iloc[-22] if len(score) >= 22 else pd.Series(np.nan, index=score.columns)
        
        top_all = current_scores.sort_values(ascending=False)
        scr_data = []
        for rank, (tkr, val) in enumerate(top_all.items(), 1):
            ok = data.loc[last_date, tkr] > panic_level.loc[last_date, tkr]
            scr_data.append({
                "Rang": rank, 
                "ETF": test_tickers.get(tkr, tkr), 
                "Score aktuell": val,
                "Score 5 Tage": score_5d[tkr],
                "Score 14 Tage": score_14d[tkr],
                "Score 21 Tage": score_21d[tkr],
                "Status": "🟢 OK" if ok else "🔴 SMA-Sperre"
            })
            
        df_scr = pd.DataFrame(scr_data)
        
        format_dict = {
            'Score aktuell': '{:.2%}',
            'Score 5 Tage': '{:.2%}',
            'Score 14 Tage': '{:.2%}',
            'Score 21 Tage': '{:.2%}'
        }
        
        styled_df = df_scr.style.format(format_dict, na_rep="---")
        st.dataframe(styled_df, width='stretch')

    if show_chart:
        st.markdown("---")
        st.subheader(f"📊 Kapitalkurve vs. Benchmarks ({perf_title})")
        chart_df = pd.DataFrame({"🎯 System": equity})
        if not data_bench.empty:
            bench_eval = data_bench.loc[eval_start_date:]
            for col in bench_eval.columns:
                chart_df[f"🌍 {col}"] = (bench_eval[col] / bench_eval[col].bfill().iloc[0]) * 100
        st.line_chart(chart_df.ffill())

    # ==========================================
    # 5. LOGBUCH, UNIVERSUM & HANDBUCH
    # ==========================================
    if show_log:
        st.markdown("---")
        st.subheader("📋 System-Logbuch (Letzte 12 Monate)")
        twelve_m = last_date - timedelta(days=365)
        p_pos = pd.Series(0.0, index=data.columns)
        
        for date in data.loc[twelve_m:].index:
            c_pos = final_pos.loc[date]
            if date in rebalance_days or not c_pos.equals(p_pos):
                event_type = "[REBALANCING]" if date in rebalance_days else "[SMA-NOTBREMSE]"
                with st.expander(f"📍 {date.strftime('%d.%m.%Y')} - {event_type} - Cash: {(1-c_pos.sum())*100:.0f}%"):
                    curr_ranks = prev_ranks.loc[date].sort_values().head(HOLD_RANK)
                    log_rows = []
                    for r, (tkr, rv) in enumerate(curr_ranks.items(), 1):
                        above = is_above_sma.loc[date, tkr]
                        log_rows.append({
                            "Rang": r, 
                            "Asset": test_tickers.get(tkr, tkr), 
                            "Trend": "✅" if above else "❌", 
                            "Depot": "🎯" if c_pos[tkr] > 0 else "---" 
                        })
                    st.table(pd.DataFrame(log_rows))
                    
                    actions_taken = False
                    for tkr in data.columns:
                        name = test_tickers.get(tkr, tkr)
                        if c_pos[tkr] > 0 and p_pos[tkr] == 0: 
                            st.write(f"⭐ **KAUF:** {name}")
                            actions_taken = True
                        elif c_pos[tkr] == 0 and p_pos[tkr] > 0: 
                            st.write(f"🔴 **VERKAUF:** {name}")
                            actions_taken = True
                    
                    if not actions_taken:
                        st.write("⚪ **Keine Änderung am Depot.**")
            p_pos = c_pos

    if show_universe:
        st.markdown("---")
        st.subheader("🌌 ETF-Universum & Historie")
        univ_list = []
        for tkr, name in test_tickers.items():
            if tkr in data.columns:
                fvd = score[tkr].first_valid_index()
                univ_list.append({
                    "Status": "🟢 Aktiv" if pd.notnull(fvd) else "⏳ Zu jung", 
                    "Asset": name, 
                    "Ticker": tkr, 
                    "Aktiviert am": fvd.strftime('%d.%m.%Y') if pd.notnull(fvd) else "---"
                })
        st.dataframe(pd.DataFrame(univ_list).sort_values("Status"), width='stretch')

    if show_manual:
        st.markdown("---")
        if app_mode == "🚀 Satelliten (Offensive)":
            st.header("📘 System-Handbuch: Satelliten-Strategie (Pro-Version)")
            st.markdown("""
            ### 1. Anlagephilosophie & Zielsetzung
            Das Satelliten-Portfolio bildet die **Offensive** deines Gesamtdepots (50 % Kapitalgewichtung). Das klare Ziel ist die **Alpha-Generierung** (Überrendite) durch das gezielte Ansteuern von hochvolatilen, trendstarken Sektoren, Ländern und Megatrends. Es handelt sich um ein aggressives Trendfolge-System, das Gewinner reitet und bei Schwäche gnadenlos in Cash geht.

            ### 2. Das Anlage-Universum
            Das System überwacht täglich 35 sorgfältig ausgewählte ETFs aus den Bereichen Technologie (KI, Halbleiter, Cloud), Rohstoffe (Uran, Goldminen), Krypto und spezifischen Länder-/Faktor-Indizes.

            ### 3. Die 4 Säulen der Quant-Logik
            * **Säule 1: Der Momentum-Score (Relative Stärke):** Die Rangliste wird täglich aus dem Durchschnitt der Renditen über 1, 3, 6 und 12 Monate berechnet. Nur die absolut stärksten Trends setzen sich hier durch.
            * **Säule 2: SMA 85 & 3,2 % Puffer (Die absolute Notbremse):** Da Satelliten massiv schwanken, fungiert die 85-Tage-Linie als schneller Trendfilter. Der 3,2 % Puffer ist der mathematische Sweet-Spot, um normale 2-Tages-Korrekturen auszusitzen, aber bei echten Trendbrüchen den Stecker zu ziehen. Fällt der Kurs auf Tagesschlussbasis unter dieses Puffer-Level, wird **sofort am nächsten Tag verkauft**.
            * **Säule 3: Die Hysterese (Halte-Zone zur Kostenreduktion):** Das System ist auf `Buy Rank 2` und `Hold Rank 4` (Hysterese 2) eingestellt. Es kauft streng nur die Top 2. Ist ein ETF aber einmal im Depot, darf er beim Rebalancing bis auf Platz 4 abrutschen, ohne verkauft zu werden. Das verhindert teures Hin- und Her-Traden ("Whipsaw").
            * **Säule 4: Strikte State-Machine (Der Cooldown):** Die wichtigste Fehlerbereinigung im Code! Fliegt ein ETF durch die Notbremse raus, ist er gesperrt. Er darf **nicht** sofort wieder gekauft werden, nur weil er am nächsten Tag über den SMA zuckt. Er muss auf der Strafbank bleiben, bis das nächste 14-Tage-Rebalancing ansteht UND er sich wieder regulär in die Top 2 hochgekämpft hat.

            ### 4. Der Workflow für den Anleger (Orderausführung)
            **A. Der tägliche 1-Minuten-Check (Defensive):**
            * Öffne das Dashboard jeden Morgen und prüfe die Sektion *'Tagesaktuelle Änderungen'*. 
            * Steht hier ein **VERKAUF**, hat die Notbremse am Vortag (Schlusskurs) ausgelöst. 
            * **Aktion:** Führe den Verkauf beim Broker **sofort nach Börseneröffnung** aus (Cash-Aufbau). Du stellst die Position glatt, um das Kapital zu schützen.

            **B. Das 14-tägige Rebalancing (Offensive):**
            * Alle 14 Handelstage (siehe Countdown) wird das Depot neu gemischt. 
            * Steht hier ein **KAUF**, ist ein neues Asset in die Top 2 aufgestiegen oder ein gesperrtes Asset (Cooldown beendet) hat wieder ein Kaufsignal generiert.
            * Steht hier ein **VERKAUF** (ohne Notbremsen-Signal), ist ein Asset aus der Halte-Zone gefallen (Platz 5 oder schlechter) und wird ausgetauscht.
            * **Aktion:** Führe die Käufe und Verkäufe am **Tag des Rebalancings (idealerweise gegen Handelsende)** oder direkt zur Eröffnung des folgenden Handelstages aus. Investiere das vorhandene Cash zu gleichen Teilen (je 50% der Satelliten-Zielallokation) in die beiden Top-Assets.
            """)
        else:
            st.header("📘 System-Handbuch: Core Master-Strategie (Pro-Version)")
            st.markdown("""
            ### 1. Anlagephilosophie & Zielsetzung
            Das Core-Portfolio bildet das **All-Weather Fundament** deines Gesamtdepots (50 % Kapitalgewichtung). Während die Satelliten für Rendite sorgen, hat der Core nur eine primäre Aufgabe: **Absoluten Kapitalschutz in Krisen**. Das System ist darauf optimiert, den Drawdown (Max DD) auf ca. -11 % bis -12 % zu begrenzen, selbst wenn Aktienmärkte um -30 % einbrechen (wie z.B. 2022).

            ### 2. Das Anlage-Universum
            Das System überwacht 8 hochliquide, wenig korrelierende Basis-Märkte: S&P 500, Europa 600, MSCI Japan, Emerging Markets, Globale Anleihen (Hedged), Gold, Immobilien und Rohstoffe. *(Hinweis: Der reine Euro-Bond ETF wurde bewusst entfernt, um gefährliche Klumpenrisiken in der Anleihen-Klasse zu vermeiden).*

            ### 3. Die 4 Säulen der Quant-Logik
            * **Säule 1: Der Momentum-Score (Relative Stärke):** Exakt wie bei den Satelliten werden die Renditen über 1, 3, 6 und 12 Monate gemittelt, um die Kapitalflüsse der großen Institutionellen zu tracken.
            * **Säule 2: SMA 200 & 2,8 % Puffer (Der Fels in der Brandung):** Für breite Indizes ist die 200-Tage-Linie der globale Goldstandard. Der 2,8 % Puffer ist dein fehlerbereinigter Sweet-Spot. Er gibt dem Markt genau genug Luft, um die berüchtigten "Bärenfallen" (False Breakdowns) an der 200-Tage-Linie zu ignorieren, zieht bei einem echten Crash aber verlässlich und unemotional die Reißleine.
            * **Säule 3: Die Hysterese (Halte-Zone zur Kostenreduktion):** Das System ist auf `Buy Rank 3` und `Hold Rank 4` (Hysterese 1) eingestellt. Es kauft die Top 3 Basis-Märkte. Ein Asset darf beim Rebalancing bis auf Platz 4 abrutschen, bevor es ausgetauscht wird. Dies sorgt für extrem niedrige Transaktionskosten (historisch unter 1 Trade pro Monat).
            * **Säule 4: Strikte State-Machine (Der Cooldown):** Einmal raus ist raus! Wird der 200-Tage-SMA inkl. Puffer nach unten durchbrochen, geht der Anteil unwiderruflich in Cash. Ein Wiedereinstieg ("Re-Entry") erfolgt erst beim nächsten offiziellen Rebalancing-Termin, falls das Asset dann wieder in den Top 3 steht. Das schützt den Core vor zermürbenden Seitwärtsphasen.

            ### 4. Der Workflow für den Anleger (Orderausführung)
            **A. Der tägliche 1-Minuten-Check (Defensive):**
            * Öffne das Dashboard jeden Morgen und prüfe die Sektion *'Tagesaktuelle Änderungen'*. 
            * Steht hier ein **VERKAUF**, hat die Notbremse am Vortag (Schlusskurs) ausgelöst.
            * **Aktion:** Verkaufe die Core-Position **sofort nach Börseneröffnung** in Cash. Da es sich hier um liquide Basis-Märkte handelt, ist ein zügiger Verkauf (Market Order oder Limit nahe Geldkurs) essenziell, um das Kapital in Bärenmärkten in Sicherheit zu bringen.

            **B. Das 14-tägige Rebalancing (Offensive/Anpassung):**
            * Alle 14 Handelstage schichtet das System um. 
            * **Aktion:** Führe die angezeigten Käufe und Verkäufe am **Tag des Rebalancings** aus. Die Zielallokation beträgt 33,3 % des Core-Gesamtkapitals pro Top-3-Asset. Investiere das angesammelte Cash in die neuen Momentum-Führer, sofern ihr Trend intakt ist.
            """)
