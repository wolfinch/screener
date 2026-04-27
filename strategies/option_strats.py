#
# Wolfinch Auto trading Bot screener
#  *** Options Watchlist Strategies
#  *** Manages watchlist persistence, sim data generation,
#  *** and per-ticker daily aggregated options history.
#
#  Copyright: (c) 2017-2026 Wolfinch Inc.
#  This file is part of Wolfinch.
#
#  Wolfinch is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wolfinch is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wolfinch.  If not, see <https://www.gnu.org/licenses/>.

import os
import json
import random
import datetime
import logging

log = logging.getLogger("OPTION_STRATS")

# ── Watchlist persistence ──────────────────────────────
WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                              "data", "options_watchlist.json")

_tickers = []

def load_watchlist():
    global _tickers
    try:
        with open(WATCHLIST_FILE, 'r') as f:
            _tickers = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _tickers = []

def save_watchlist():
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(_tickers, f)

def get_tickers():
    return list(_tickers)

def add_ticker(ticker):
    global _tickers
    ticker = ticker.strip().upper()
    if ticker and ticker not in _tickers:
        _tickers.append(ticker)
        save_watchlist()
    return list(_tickers)

def remove_ticker(ticker):
    global _tickers
    ticker = ticker.strip().upper()
    if ticker in _tickers:
        _tickers.remove(ticker)
        save_watchlist()
    return list(_tickers)

# ── Simulated per-ticker daily history ─────────────────
SIM_TICKER_SEEDS = {
    "AAPL":  {"call_oi": 820000, "put_oi": 670000, "call_vol": 125000, "put_vol": 98000,  "call_prem": 4200000, "put_prem": 3100000},
    "TSLA":  {"call_oi": 1500000,"put_oi": 1650000,"call_vol": 310000, "put_vol": 285000, "call_prem": 9800000, "put_prem": 10500000},
    "NVDA":  {"call_oi": 1100000,"put_oi": 820000, "call_vol": 280000, "put_vol": 195000, "call_prem": 6500000, "put_prem": 4800000},
    "AMD":   {"call_oi": 650000, "put_oi": 580000, "call_vol": 145000, "put_vol": 120000, "call_prem": 3200000, "put_prem": 2700000},
    "MSFT":  {"call_oi": 450000, "put_oi": 310000, "call_vol": 98000,  "put_vol": 65000,  "call_prem": 5500000, "put_prem": 3800000},
    "GOOGL": {"call_oi": 380000, "put_oi": 290000, "call_vol": 88000,  "put_vol": 62000,  "call_prem": 2900000, "put_prem": 2100000},
    "META":  {"call_oi": 520000, "put_oi": 350000, "call_vol": 150000, "put_vol": 95000,  "call_prem": 7200000, "put_prem": 4500000},
    "AMZN":  {"call_oi": 410000, "put_oi": 350000, "call_vol": 110000, "put_vol": 88000,  "call_prem": 3800000, "put_prem": 3000000},
    "SOFI":  {"call_oi": 900000, "put_oi": 1120000,"call_vol": 220000, "put_vol": 260000, "call_prem": 1200000, "put_prem": 1500000},
    "PLTR":  {"call_oi": 700000, "put_oi": 640000, "call_vol": 175000, "put_vol": 155000, "call_prem": 2100000, "put_prem": 1800000},
    "COIN":  {"call_oi": 350000, "put_oi": 370000, "call_vol": 95000,  "put_vol": 92000,  "call_prem": 5100000, "put_prem": 5400000},
    "MARA":  {"call_oi": 600000, "put_oi": 780000, "call_vol": 180000, "put_vol": 210000, "call_prem": 850000,  "put_prem": 1100000},
}
SIM_DEFAULT_SEED = {"call_oi": 300000, "put_oi": 250000, "call_vol": 50000, "put_vol": 42000, "call_prem": 1500000, "put_prem": 1200000}

SIM_PRICES = {
    "AAPL": 189.0, "TSLA": 248.0, "NVDA": 136.0, "AMD": 164.0,
    "MSFT": 426.0, "GOOGL": 176.0, "META": 510.0, "AMZN": 187.0,
    "SOFI": 8.75, "PLTR": 24.0, "COIN": 226.0, "MARA": 19.5,
}

def _gen_sim_top_strikes(sym, rng, days=7):
    price = SIM_PRICES.get(sym, 50.0)
    today = datetime.date.today()
    dates = [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
             for i in range(days - 1, -1, -1)]
    expiries = []
    d = today
    for _ in range(4):
        d += datetime.timedelta(days=(4 - d.weekday()) % 7 or 7)
        expiries.append(d.strftime("%m/%d"))

    step = max(1, round(price * 0.025))
    n_candidates = 15
    strikes_call = [price + step * i for i in range(1, n_candidates + 1)]
    strikes_put  = [price - step * i for i in range(1, n_candidates + 1)]

    def _make_series(strikes, opt_char, base_oi, base_vol, base_prem):
        series = []
        for s in strikes:
            exp = rng.choice(expiries)
            label = "%g%s %s" % (s, opt_char, exp)
            oi_base = int(base_oi * rng.uniform(0.2, 1.0))
            vol_base = int(base_vol * rng.uniform(0.2, 1.0))
            prem_base = int(base_prem * rng.uniform(0.2, 1.0))
            oi_vals, vol_vals, prem_vals = [], [], []
            ob, vb, pb = oi_base, vol_base, prem_base
            for _ in range(days):
                oi_vals.append(int(ob * (1 + rng.uniform(-0.06, 0.06))))
                vol_vals.append(int(vb * (1 + rng.uniform(-0.10, 0.10))))
                prem_vals.append(int(pb * (1 + rng.uniform(-0.08, 0.08))))
                ob = int(ob * (1 + rng.uniform(-0.03, 0.04)))
                vb = int(vb * (1 + rng.uniform(-0.05, 0.06)))
                pb = int(pb * (1 + rng.uniform(-0.04, 0.05)))
            avg_oi = sum(oi_vals) / days
            series.append({"label": label, "oi": oi_vals, "vol": vol_vals,
                           "prem": prem_vals, "avg_oi": avg_oi})
        series.sort(key=lambda x: x["avg_oi"], reverse=True)
        top = series[:10]
        return [{"label": s["label"], "oi": s["oi"], "vol": s["vol"],
                 "prem": s["prem"]} for s in top]

    seed = SIM_TICKER_SEEDS.get(sym, SIM_DEFAULT_SEED)
    calls = _make_series(strikes_call, "C", seed["call_oi"] // 10,
                         seed["call_vol"] // 10, seed["call_prem"] // 10)
    puts = _make_series(strikes_put, "P", seed["put_oi"] // 10,
                        seed["put_vol"] // 10, seed["put_prem"] // 10)
    return {"dates": dates, "calls": calls, "puts": puts}

def _gen_sim_ticker_history(sym, days=7):
    seed = dict(SIM_TICKER_SEEDS.get(sym, SIM_DEFAULT_SEED))
    rng = random.Random(hash(sym))
    today = datetime.date.today()
    dates, call_oi, put_oi, call_vol, put_vol, call_prem, put_prem = [], [], [], [], [], [], []
    for i in range(days - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
        jitter = lambda base: int(base * (1 + rng.uniform(-0.08, 0.08)))
        call_oi.append(jitter(seed["call_oi"]))
        put_oi.append(jitter(seed["put_oi"]))
        call_vol.append(jitter(seed["call_vol"]))
        put_vol.append(jitter(seed["put_vol"]))
        call_prem.append(jitter(seed["call_prem"]))
        put_prem.append(jitter(seed["put_prem"]))
        seed = {k: int(v * (1 + rng.uniform(-0.03, 0.04))) for k, v in seed.items()}
    result = {
        "dates": dates,
        "call_oi": call_oi, "put_oi": put_oi,
        "call_vol": call_vol, "put_vol": put_vol,
        "call_prem": call_prem, "put_prem": put_prem,
    }
    result["top"] = _gen_sim_top_strikes(sym, rng)
    return result

# ── Real data: RH fetch, aggregate, history ───────────
# _history[sym] = [{"date": "2026-04-26", "call_oi": N, "put_oi": N, ...
#                    "strikes": {"calls": [...], "puts": [...]}}, ...]
_history = {}
_last_fetch = {}  # sym -> epoch of last fetch
FETCH_INTERVAL = 12 * 3600  # refresh once every 12 hours
_db = None  # OptionsDb instance, set by init_options_db()

def init_options_db():
    """Initialize options DB and restore history from previous runs."""
    global _db, _history, _last_fetch
    from db.options_db import OptionsDb
    _db = OptionsDb()
    _history = _db.load_all()
    total = sum(len(v) for v in _history.values())
    log.info("restored %d options snapshots for %d symbols from DB",
             total, len(_history))
    # Mark symbols that have today's snapshot as recently fetched
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    now = int(datetime.datetime.now().timestamp())
    for sym, snaps in _history.items():
        if snaps and snaps[-1].get("date") == today_str:
            _last_fetch[sym] = now
            log.info("skipping re-fetch for %s (already have %s)", sym, today_str)

def _parse_expiry(exp_str):
    """Parse expiry string like '260501' -> datetime.date(2026,5,1)"""
    try:
        y = 2000 + int(exp_str[:2])
        m = int(exp_str[2:4])
        d = int(exp_str[4:6])
        return datetime.date(y, m, d)
    except (ValueError, IndexError):
        return None

def _is_expired(exp_str):
    """Return True if the expiry date is in the past."""
    d = _parse_expiry(exp_str)
    if d is None:
        return False
    return d < datetime.date.today()

def _fetch_and_store(sym):
    """Fetch options chain from RH, aggregate, and append to _history."""
    try:
        import tdata
        chains = tdata.get_options(sym)
    except Exception as e:
        log.error("failed to fetch options for %s: %s", sym, e)
        return

    if not chains:
        log.warning("no options data returned for %s", sym)
        return

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    call_oi = 0; put_oi = 0; call_vol = 0; put_vol = 0
    call_prem = 0; put_prem = 0
    call_strikes = []
    put_strikes = []

    for exp_group in chains:
        exp_str = exp_group.get("expiry", "")
        if _is_expired(exp_str):
            continue
        exp_label = exp_str[2:4] + "/" + exp_str[4:6]
        for c in exp_group.get("calls", []):
            oi = c.get("oi", 0) or 0
            vol = c.get("volume", 0) or 0
            price = c.get("price", 0) or 0
            call_oi += oi
            call_vol += vol
            call_prem += int(price * oi * 100)
            if oi > 0:
                call_strikes.append({
                    "label": "%gC %s" % (c.get("strike", 0), exp_label),
                    "oi": oi, "vol": vol,
                    "prem": int(price * oi * 100),
                    "expiry": exp_str
                })
        for p in exp_group.get("puts", []):
            oi = p.get("oi", 0) or 0
            vol = p.get("volume", 0) or 0
            price = p.get("price", 0) or 0
            put_oi += oi
            put_vol += vol
            put_prem += int(price * oi * 100)
            if oi > 0:
                put_strikes.append({
                    "label": "%gP %s" % (p.get("strike", 0), exp_label),
                    "oi": oi, "vol": vol,
                    "prem": int(price * oi * 100),
                    "expiry": exp_str
                })

    call_strikes.sort(key=lambda x: x["oi"], reverse=True)
    put_strikes.sort(key=lambda x: x["oi"], reverse=True)

    snap = {
        "date": today_str,
        "call_oi": call_oi, "put_oi": put_oi,
        "call_vol": call_vol, "put_vol": put_vol,
        "call_prem": call_prem, "put_prem": put_prem,
        "strikes": {
            "calls": call_strikes[:15],
            "puts": put_strikes[:15]
        }
    }

    if sym not in _history:
        _history[sym] = []
    hist = _history[sym]
    if hist and hist[-1]["date"] == today_str:
        hist[-1] = snap
    else:
        hist.append(snap)
    _last_fetch[sym] = int(datetime.datetime.now().timestamp())
    log.info("fetched options data for %s: %d call strikes, %d put strikes",
             sym, len(call_strikes), len(put_strikes))
    if _db:
        _db.save_snapshot(sym, today_str, snap)

def update_options_data():
    """Called from the main screener loop. Refreshes options data for all
    watchlist tickers respecting FETCH_INTERVAL."""
    now = int(datetime.datetime.now().timestamp())
    for sym in list(_tickers):
        last = _last_fetch.get(sym, 0)
        if now - last >= FETCH_INTERVAL:
            log.info("refreshing options data for %s", sym)
            _fetch_and_store(sym)

def _build_ticker_response(sym):
    """Build the API response from stored _history for a ticker."""
    hist = _history.get(sym, [])
    if not hist:
        return {}

    dates = [h["date"] for h in hist]
    result = {
        "dates": dates,
        "call_oi": [h["call_oi"] for h in hist],
        "put_oi": [h["put_oi"] for h in hist],
        "call_vol": [h["call_vol"] for h in hist],
        "put_vol": [h["put_vol"] for h in hist],
        "call_prem": [h["call_prem"] for h in hist],
        "put_prem": [h["put_prem"] for h in hist],
    }

    latest = hist[-1]
    today = datetime.date.today()
    top_calls = [s for s in latest["strikes"]["calls"] if not _is_expired(s["expiry"])][:10]
    top_puts  = [s for s in latest["strikes"]["puts"]  if not _is_expired(s["expiry"])][:10]

    def _build_strike_series(top_strikes, side):
        series = []
        for s in top_strikes:
            label = s["label"]
            oi_vals, vol_vals, prem_vals = [], [], []
            for h in hist:
                matched = None
                for hs in h["strikes"].get(side, []):
                    if hs["label"] == label:
                        matched = hs
                        break
                oi_vals.append(matched["oi"] if matched else 0)
                vol_vals.append(matched["vol"] if matched else 0)
                prem_vals.append(matched["prem"] if matched else 0)
            series.append({"label": label, "oi": oi_vals, "vol": vol_vals, "prem": prem_vals})
        return series

    result["top"] = {
        "dates": dates,
        "calls": _build_strike_series(top_calls, "calls"),
        "puts": _build_strike_series(top_puts, "puts"),
    }
    return result

# ── Public data accessors ─────────────────────────────
def get_ticker_data(sym, sim_mode=False):
    sym = sym.strip().upper()
    if sim_mode:
        if sym not in _tickers:
            return {}
        return _gen_sim_ticker_history(sym)
    if sym not in _tickers:
        return {}
    return _build_ticker_response(sym)

def get_screener_data(sim_mode=False):
    tickers = get_tickers()
    if not tickers:
        return {}
    if sim_mode:
        return {sym: _gen_sim_ticker_history(sym) for sym in tickers}
    result = {}
    for sym in tickers:
        result[sym] = _build_ticker_response(sym)
    return result

def make_options_cb(sim_mode=False):
    return {
        'get_tickers': get_tickers,
        'add_ticker': add_ticker,
        'remove_ticker': remove_ticker,
        'get_data': lambda: get_screener_data(sim_mode),
        'get_ticker_data': lambda sym: get_ticker_data(sym, sim_mode),
    }

# EOF
