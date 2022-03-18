#
# Wolfinch Auto trading Bot screener
#  *** Total Cash Balance Vs. Market Cap difference. 
#
#  Copyright: (c) 2017-2021 Joshith Rayaroth Koderi
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
import re
from .screener_base import Screener
import time
from datetime import datetime
import notifiers

from utils import getLogger

log = getLogger("CASH_MCAP")
log.setLevel(log.DEBUG)

class CASH_MCAP(Screener):
    def __init__(self, name="CASH_MCAP", ticker_kind="ALL", interval=24*60*60, multiplier=1, data="", notify=None, **kwarg):
        log.info ("init: name: %s ticker_kind: %s interval: %d multiplier: %d data_src_name: %s"%(name, ticker_kind, interval, multiplier, data))
        super().__init__(name, ticker_kind, interval)
        self.multiplier = multiplier
        self.data_src_name = data
        self.notify_kind = notify
        self.filtered_list = {} #li
    def update(self, sym_list, ticker_stats_g):
        #we don't update data_src_name here. Rather self.data_src_name is our data_src_name source
        try:
            t_data = ticker_stats_g.get(self.data_src_name)
            if not t_data:
                log.error ("ticker data_src_name from screener %s not updated"%(self.data_src_name))
                return False
            #make sure all data_src_name available for our list 
            ## TODO: FIXME: optimize this
            for sym in sym_list:
                if not t_data.get(sym):
                    log.error ("data_src_name for ticker %s not updated"%(sym))
                    return False
            return True
        except Exception as e:
            log.critical("exception while get data_src_name e: %s"%(e))
            return False
    def screen(self, sym_list, ticker_stats_g):
        # Screen: Total_cash_balance > cur_market_cap
        #1.get data_src_name from self.data_src_name 
        ticker_stats = ticker_stats_g.get(self.data_src_name)
        if not ticker_stats:
            raise

        #2. for each sym, if cash_pos > market_cap -> add filtered l
        self.filtered_list = {}
        now = int(time.time())
        tcash = 0
        mcap = 0
        high =0
        low =0
        price =0
        try:
            for sym in sym_list:
                sym_d = ticker_stats[sym]
                # log.info("sym_d: %s \n"%(sym_d))
                sum_prof = sym_d.get("summaryProfile")
                if sum_prof:
                    if sum_prof.get("sector") == "Financial Services":
                        continue
                sum_det = sym_d.get("summaryDetail")
                if sum_det:
                    # log.info("sum_d %s"%(sum_det))
                    mcap_r=sum_det.get("marketCap")
                    if mcap_r:
                        mcap=int(mcap_r.get("raw"))
                    price_r=sum_det.get("previousClose")
                    if price_r:
                        price=round(float(price_r.get("raw")), 2)
                    high_r=sum_det.get("fiftyTwoWeekHigh")
                    if high_r:
                        high=round(float(high_r.get("raw")), 2)
                    low_r=sum_det.get("fiftyTwoWeekLow")
                    if low_r:
                        low=round(float(low_r.get("raw")), 2)                                    
                fin_d = sym_d.get("financialData")
                if fin_d:
                    # log.info("find_d %s"%(fin_d))
                    tcash_r=fin_d.get("totalCash")
                    if tcash_r:
                        tcash=int(tcash_r.get("raw"))
                    tdebt = 0
                    tdebt_r=fin_d.get("totalDebt")
                    if tdebt_r:
                        tdebt=int(tdebt_r.get("raw"))
                    #get net cash balance
                    tcash = tcash - tdebt           
                # log.info ("mcap %d tcash: %d"%(mcap, tcash))
                if tcash > mcap:
                    if tcash//1000000000 > 0 :
                        tcash_s = str(round(tcash /1000000000, 2))+"B"
                    elif tcash//1000000 > 0 :
                        tcash_s = str(round(tcash /1000000, 2))+"M"
                    elif tcash//1000 > 0 :
                        tcash_s = str(round(tcash /1000, 2))+"K"                    
                    else:
                        tcash_s = str(tcash)
                    if mcap//1000000000 > 0 :
                        mcap_s = str(round(mcap /1000000000, 2))+"B"
                    elif mcap//1000000 > 0 :
                        mcap_s = str(round(mcap /1000000, 2))+"M"
                    elif mcap//1000 > 0 :
                        mcap_s = str(round(mcap /1000, 2))+"K"                    
                    else:
                        mcap_s = str(mcap)
                    #get % over tcash 
                    tcash_pct = round((tcash/mcap)*100, 2)
                    #get pricetoBook value
                    key_stats = sym_d.get("defaultKeyStatistics")
                    if key_stats:
                        # log.info("sum_d %s"%(sum_det))
                        ptb_r=key_stats.get("priceToBook")
                        if ptb_r:
                            ptb=round(ptb_r.get("raw"), 2)
                    fs  = {"symbol": sym, "time": now,
                            "cur_mcap": mcap_s,
                            "total_cash": tcash_s,
                            "cash": tcash,
                            "mcap": mcap,
                            "price": price,
                            "ftwh": high,
                            "ftwl": low,
                            "tcash_pct": tcash_pct,
                            "ptb": ptb
                            }
                    log.info ('new sym found by screener: %s info:  %s'%(sym, fs))
                    self.filtered_list [sym] = fs
                    if self.notify_kind:
                        notify_msg = {"symbol": fs["symbol"],
                                        "cur_mcap": "%s)"%(mcap_s),
                                        "total_cash": "%s"%(tcash_s)}
                        notifiers.notify(self.notify_kind, self.name, notify_msg)
        except Exception as e:
            log.critical("exception while get screen e: %s"%(e))
    def get_screened(self):
#         ft = [
#          {"symbol": "aapl", "time": 1616585400, "last_price": 10.2, "price_change": "10", "vol_change": "2", "cur_price_change": "20", "cur_vol_change": "4"},
#          {"symbol": "codx", "time": 1616595400, "last_price": "13.2", "price_change": "20", "vol_change": "20", "cur_price_change": "30", "cur_vol_change": "30"}            
#              ]
        fmt = {"symbol": "Symbol", "time": "Time", "cur_mcap": "Market Cap",
         "total_cash": "Total Cash", "tcash_pct": "Cash %", "price": "Price", "ftwh": "High", "ftwl": "Low", "ptb": "Price2Book"}
        return [fmt]+list(self.filtered_list.values())

#EOF
