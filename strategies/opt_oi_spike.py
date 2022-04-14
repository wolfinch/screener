#
# Wolfinch Auto trading Bot screener
#  *** options Open interest going up 
#  *** option selling screener, maximum profit
#
#  Copyright: (c) 2017-2022 Joshith Rayaroth Koderi
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

# from decimal import Decimal
import traceback
from datetime import datetime
from utils import getLogger
from .screener_base import Screener
import time
import notifiers
from datetime import date

log = getLogger("OPT_OI_SPIKE")
log.setLevel(log.DEBUG)
MAX_SCREENED_TICKERS = 50
OI_MAX_DAYS = 180 #~6 months

# track change in OI from one screen to another. also track put/call spread. 
class OPT_OI_SPIKE(Screener):
    def __init__(self, name="OPT_OI_SPIKE", ticker_kind="ALL", interval=24*60*60, multiplier=1, options_data="", ticker_data="", notify=None, **kwarg):
        log.info("init: name: %s ticker_kind: %s interval: %d multiplier: %d data_src_name: %s" % (
            name, ticker_kind, interval, multiplier, options_data))
        super().__init__(name, ticker_kind, interval)
        self.multiplier = multiplier
        self.options_data_src_name = options_data
        self.ticker_data_src_name = ticker_data
        self.notify_kind = notify
        self.filtered_list = {}  # li

        #   o = {
        #         "expiry": expiry,
        #         "strike": strike_price,
        #         "price": 0,
        #         "oi": 0,
        #         "iv": 0,
        #         "ask": 0,
        #         "bid": 0,
        #         "volume": 0,
        #         "itm": False,
        #         "delta": 0,
        #         "theta": 0,
        #         "gamma": 0,
        #         "vega": 0
        #     }   
    def update(self, sym_list, ticker_stats_g):
        # we don't update data_src_name here. Rather self.data_src_name is our data_src_name source
        try:
            o_data = ticker_stats_g.get(self.options_data_src_name)
            if not o_data:
                log.error("ticker options_data_src_name from screener %s not updated" % (
                    self.options_data_src_name))
                return False
            t_data = ticker_stats_g.get(self.ticker_data_src_name)
            if not t_data:
                log.error("ticker ticker_data_src_name from screener %s not updated" % (
                    self.ticker_data_src_name))
                return False                
            # make sure all data_src_name available for our list
            if not t_data.updated or not o_data.updated:
                log.error("data_src_name is still being updated t_data.updated: %s not o_data.updated: %s"%(t_data.updated, o_data.updated))
                return False
            today = date.today()
            p_oi_data = ticker_stats_g.get(self.name)
            oi_data = {}
            for sym, o_l in o_data.items():
                num_puts = 0
                num_calls = 0
                high_p_s_oi = 0
                high_c_s = 0
                high_c_exp = ""
                high_c_s_oi = 0
                high_p_s = 0
                high_p_exp = ""
                if not o_l:
                    continue
                for o in o_l:
                    e = o["expiry"]
                    if (date(year=2000+int(e[:2]), month=int(e[2:4]), day=int(e[4:])) - today).days > OI_MAX_DAYS:
                        #ignore options beyond our interestd timeframe
                        continue
                    for p in o["puts"]:
                        p_n = int(p["oi"])
                        num_puts += p_n
                        if p_n > high_p_s_oi:
                            high_p_s_oi = p_n
                            high_p_s = p["strike"]
                            high_p_exp = e
                    for c in o["calls"]:
                        c_n = int(c["oi"])
                        num_calls += c_n
                        if c_n > high_c_s_oi:
                            high_c_s_oi = c_n
                            high_c_s = c["strike"]
                            high_c_exp = e
                o_d = {"num_puts": num_puts,
                        "high_puts_oi": high_p_s_oi, 
                        "high_puts_exp": high_p_exp,
                        "high_puts_strike": high_p_s,
                        "num_calls": num_calls,
                        "high_calls_oi": high_c_s_oi,
                        "high_calls_exp": high_c_exp,
                        "high_calls_strike": high_c_s }
                if not p_oi_data.get(sym):
                    p_oi_data[sym] = [o_d]
                else:
                    p_oi_data[sym].append(o_d)
                if len(p_oi_data[sym]) > 3:
                    del(p_oi_data[sym][0])
            return True
        except Exception as e:
            log.critical("exception while get data_src_name e: %s" %(traceback.format_exc()))
            return False

    def screen(self, sym_list, ticker_stats_g):
        # Screen: Total_cash_balance > cur_market_cap
        # 1.get data_src_name from self.data_src_name
        ticker_stats = ticker_stats_g.get(self.ticker_data_src_name)
        if not ticker_stats:
            raise
        options_stats = ticker_stats_g.get(self.name)
        if not options_stats:
            raise    
        # 2. for each sym, if cash_pos > market_cap -> add filtered l
        self.filtered_list = {}
        now = int(time.time())
        try:
            fs_l = []
            for sym in sym_list:
                #2.0 get curr price:
                tprice = 0
                fd = ticker_stats.get(sym)
                if not fd:
                    log.error ("unable to get fin data for sym %s"%(sym))
                    continue
                
                asset_prof = fd.get("assetProfile")
                if asset_prof:
                    industry = asset_prof.get("industry")
                    if industry:
                        industry = str(industry).lower()
                        if industry == "biotechnology":
                            log.info ("industry biotechnology symbol ignored - %s"%(sym))
                            continue                
                sum_det = fd.get("summaryDetail")
                if sum_det:
                    price_r=sum_det.get("previousClose")
                    if price_r:
                        tprice=round(float(price_r.get("raw")), 2)

                sym_d = options_stats.get(sym)
                # log.debug("screen : %s \n df %s"%(sym, sym_d))
                if tprice < 1 or not sym_d or len(sym_d) == 0:
                    log.error("unable to get options stats for sym %s" % (sym))
                    continue

                if len(sym_d) < 2:
                    log.error ("too short option stats history for sym %s"%(sym))
                    continue
                # o_d = {"num_puts": num_puts,
                #         "high_puts_oi": high_p_s_oi, 
                #         "high_puts_exp": high_p_exp,
                #         "high_puts_strike": high_p_s,
                #         "num_calls": num_calls,
                #         "high_calls_oi": high_c_s_oi,
                #         "high_calls_exp": high_c_exp,
                #         "high_calls_strike": high_c_s }
                os_c = sym_d[-1]
                os_p = sym_d[-2]

                oi_p_d = os_c["num_puts"] - os_p["num_puts"]
                oi_c_d = os_c["num_calls"] - os_p["num_calls"]
                num_oi = 0
                if oi_p_d > oi_c_d:
                    num_oi_d = str(oi_p_d)+" P"
                    num_oi = oi_p_d
                else:
                    num_oi_d = str(oi_c_d)+" C"
                    num_oi = oi_c_d
                high_calls_oi = str(os_c["high_calls_oi"])+"@"+str(os_c["high_calls_strike"])+"/"+str(os_c["high_calls_exp"])
                high_puts_oi = str(os_c["high_puts_oi"])+"@"+str(os_c["high_puts_strike"])+"/"+str(os_c["high_puts_exp"])

                os_s = {
                    "symbol": sym, "time": now,
                    "num_oi_d":  num_oi_d,
                    "num_oi": num_oi,
                    "high_calls_oi": high_calls_oi,
                    "high_puts_oi": high_puts_oi
                }

                log.info('new sym found by screener: %s info:  %s' %(sym, os_s))
                fs_l.append(os_s)
            # now that we have list of opt. sort the list and get only top 25
            fs_l.sort(reverse=True, key=lambda e: e["num_oi_d"])
            self.filtered_list = {}  # clear list
            for fs in fs_l[:MAX_SCREENED_TICKERS]:
                self.filtered_list[fs["symbol"]] = fs
        except Exception as e:
            log.critical("exception while screen e: %s exception: %s" % (e, traceback.format_exc()))

    def get_screened(self):
        fmt = {"symbol": "Symbol", "time": "Time", "num_oi_d": "∆OI",
               "high_calls_oi": "High Calls OI", "high_puts_oi": "High Puts OI"}
        return {"format": fmt, "sort": "num_oi", "data": list(self.filtered_list.values()), "hidden":["time", "num_oi"]}

# EOF
