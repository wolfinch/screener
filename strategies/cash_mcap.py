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
        log.info ("init: name: %s ticker_kind: %s interval: %d multiplier: %d data: %s"%(name, ticker_kind, interval, multiplier, data))
        super().__init__(name, ticker_kind, interval)
        self.multiplier = multiplier
        self.data = data
        self.notify_kind = notify
        self.filtered_list = {} #li
    def update(self, sym_list, ticker_stats_g):
        #we don't update data here. Rather self.data is our data source
        try:
            t_data = ticker_stats_g.get(self.data)
            if not t_data:
                log.error ("ticker data from screener %s not updated"%(self.data))
                return False
            #make sure all data available for our list 
            ## TODO: FIXME: optimize this
            for sym in sym_list:
                if not t_data.get(sym):
                    log.error ("data for ticker %s not updated"%(sym))
                    return False
            return True
        except Exception as e:
            log.critical("exception while get data e: %s"%(e))
            return False
    def screen(self, sym_list, ticker_stats_g):
        # Screen: Total_cash_balance > cur_market_cap
        #1.get data from self.data 
        ticker_stats = ticker_stats_g.get(self.data)
        if not ticker_stats:
            raise

        #2. for each sym, if cash_pos > market_cap -> add filtered l
        self.filtered_list = {}
        now = int(time.time())
        for sym in sym_list:
            sum_det = ticker_stats.get("summaryDetail")
            if sum_det:
                mcap_r=sum_det.get("marketCap")
                if mcap_r:
                    mcap=int(mcap_r.get("raw"))
            fin_d = ticker_stats.get("financialData")
            if fin_d:
                tcash_r=fin_d.get("totalCash")
                if tcash_r:
                    tcash=int(tcash_r.get("raw"))
            if tcash > mcap:
                log.debug ("identified sym - %s"%(sym))
                fs  = {"symbol": sym, "time": now,
                           "cur_mcap": round(mcap, 2),
                           "total_cash": round(tcash, 2)
                           }
                log.info ('new sym found by screener: %s info:  %s'%(sym, fs))
                self.filtered_list [sym] = fs
                if self.notify_kind:
                    notify_msg = {"symbol": fs["symbol"],
                                    "cur_mcap": "%s)"%(mcap),
                                    "total_cash": "%s"%(tcash)}
                    notifiers.notify(self.notify_kind, self.name, notify_msg)
                    
    def get_screened(self):
#         ft = [
#          {"symbol": "aapl", "time": 1616585400, "last_price": 10.2, "price_change": "10", "vol_change": "2", "cur_price_change": "20", "cur_vol_change": "4"},
#          {"symbol": "codx", "time": 1616595400, "last_price": "13.2", "price_change": "20", "vol_change": "20", "cur_price_change": "30", "cur_vol_change": "30"}            
#              ]
        fmt = {"symbol": "symbol", "time": "time", "cur_mcap": "market cap", "tcash": "total cash"}
        return [fmt]+list(self.filtered_list.values())

#EOF
