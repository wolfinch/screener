#
# Wolfinch Auto trading Bot screener
#  *** options iv under 5
#  *** option selling screener, maximum profit
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
import traceback
from datetime import datetime
from utils import getLogger
from .screener_base import Screener
import time
import notifiers

log = getLogger("OPT_IV")
log.setLevel(log.DEBUG)
MAX_SCREENED_TICKERS = 50

class OPT_IV(Screener):
    def __init__(self, name="OPT_IV", ticker_kind="ALL", interval=24*60*60, multiplier=1, options_data="", ticker_data="", notify=None, **kwarg):
        log.info("init: name: %s ticker_kind: %s interval: %d multiplier: %d data_src_name: %s" % (
            name, ticker_kind, interval, multiplier, options_data))
        super().__init__(name, ticker_kind, interval)
        self.multiplier = multiplier
        self.options_data_src_name = options_data
        self.ticker_data_src_name = ticker_data
        self.notify_kind = notify
        self.filtered_list = {}  # li

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
            # TODO: FIXME: optimize this
            if not t_data.updated or not o_data.updated:
                log.error("data_src_name is still being updated t_data.updated: %s not o_data.updated: %s"%(t_data.updated, o_data.updated))
                return False
            return True
        except Exception as e:
            log.critical("exception while get data_src_name e: %s" % (e))
            return False

    def screen(self, sym_list, ticker_stats_g):
        # Screen: Total_cash_balance > cur_market_cap
        # 1.get data_src_name from self.data_src_name
        ticker_stats = ticker_stats_g.get(self.ticker_data_src_name)
        if not ticker_stats:
            raise
        options_stats = ticker_stats_g.get(self.options_data_src_name)
        if not options_stats:
            raise    
        # 2. for each sym, if cash_pos > market_cap -> add filtered l
        self.filtered_list = {}
        now = int(time.time())
        try:
            fs_l = []
            for sym in sym_list:
                #2.0 get curr price:
                price = 0
                sum_det = ticker_stats[sym].get("summaryDetail")
                if sum_det:
                    price_r=sum_det.get("previousClose")
                    if price_r:
                        price=round(float(price_r.get("raw")), 2)             
                sym_d = options_stats.get(sym)
                # log.debug("screen : %s \n df %s"%(sym, sym_d))
                if not sym_d or len(sym_d) == 0 or price == 0:
                    log.error("unable to get options for sym %s" % (sym))
                    continue
                puts = sym_d[0].get("puts")
                if puts:
                    i = -1
                    for pc in puts:
                        # find the first in-the-money. and use the strike below that.
                        if pc["strike"] > price:
                            break
                        i += 1
                    if i == -1:
                        i = 0
                    # try to get the strike closer to the price
                    if i < len(puts)-1:
                        if abs(puts[i+1]["strike"] - price) < abs(puts[i]["strike"] - price):
                            i = i+1
                    pc = puts[i]
                    bid = pc.get("bid", 0)
                    ask = pc.get("ask", 0)
                    if  bid == 0:
                        #ignore ones with no bid
                        continue
                    #ignore wide bid-ask spread - 50c
                    # if ask - bid > 0.5:
                        # continue
                    iv = round(pc.get("iv", 0), 2)
                    #ignore low iv
                    if iv < 0.2:
                        continue
                    strike = pc["strike"]
                    oi = pc.get("oi", 0)
                    price = round(pc.get("price", 0), 2)
                    exp = pc.get("expiry", 0)
                    fs = {"symbol": sym, "time": now,
                          "strike": strike,
                          "price": price,
                          "iv": iv,
                          "expiry": exp,
                          "oi": oi,
                          }
                    log.info('new sym found by screener: %s info:  %s' %(sym, fs))
                    fs_l.append(fs)
                    # if self.notify_kind:
                    #     notify_msg = {"symbol": fs["symbol"],
                    #                     "cur_mcap": "%s)"%(mcap_s),
                    #                     "total_cash": "%s"%(tcash_s)}
                    # notifiers.notify(self.notify_kind, self.name, notify_msg)
            # now that we have list of opt. sort the list and get only top 25
            fs_l.sort(reverse=True, key=lambda e: e["oi"])
            self.filtered_list = {}  # clear list
            for fs in fs_l[:MAX_SCREENED_TICKERS]:
                self.filtered_list[fs["symbol"]] = fs
        except Exception as e:
            log.critical("exception while screen e: %s exception: %s" % (e, traceback.format_exc()))

    def get_screened(self):
        #         ft = [
        #          {"symbol": "aapl", "strike": 2.5, "price": 10.2, "iv": "1.4", "expiry": "200511", "oi": "20", "time": "4"},
        #              ]
        fmt = {"symbol": "Symbol", "time": "Time", "strike": "Strike",
               "price": "Price", "iv": "IV", "oi": "OI", "expiry": "Expiry"}
        return {"format": fmt, "sort": "oi", "data": list(self.filtered_list.values()), "hidden":["time"]}

# EOF
