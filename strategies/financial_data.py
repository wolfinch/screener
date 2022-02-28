#
# Collect all the financial data about tickers
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
from tkinter import N
from .screener_base import Screener
import yahoofin as yf
import time
from datetime import datetime
import notifiers

from utils import getLogger

log = getLogger("FIN_DATA")
log.setLevel(log.DEBUG)

class FIN_DATA(Screener):
    def __init__(self, name="FIN_DATA", ticker_kind="ALL", interval=24*60*60):
        log.info ("init: name: %s ticker_kind: %s interval: %d"%(name, ticker_kind, interval))
        super().__init__(name, ticker_kind, interval)
        self.YF = yf.Yahoofin ()
        self.filtered_list = {} #li
    def update(self, sym_list, ticker_stats):
        #update stats only during ~12hrs, to cover pre,open,ah (5AM-5PM PST, 12-00UTC)
        if datetime.utcfromtimestamp(int(time.time())).hour <= 12 :
            log.debug("market closed")
            return False
        try:
            get_all_tickers_info(self.YF, sym_list, ticker_stats)
            return True
        except Exception as e:
            log.critical("exception while get data e: %s"%(e))
            return False
    def screen(self, sym_list, ticker_stats):
        # no-op , this is only a data collection 
                    
    def get_screened(self):
        return None

def get_all_tickers_info(yf, sym_list, ticker_stats):
    BATCH_SIZE = 400
#     log.debug("num tickers(%d)"%(len(sym_list)))
    s = None
    ss = None
    i = 0
    try:
        while i < len(sym_list):
            ts, err =  yf.get_quotes(sym_list[i: i+BATCH_SIZE])
            if err == None:
                for ti in ts:
                    s = ti.get("symbol")
                    ss = ticker_stats.get(s)
                    if ss == None:
                        ticker_stats[s] = {"info": ti, "time":[ti.get("regularMarketTime", 0)],
                                            "volume": [ti.get("regularMarketVolume", -1)], "price": [ti.get("regularMarketPrice", -1)]
                                            }
                    else:
                        ss ["info"] = ti
                        ss ["time"].append(ti.get("regularMarketTime", 0))
                        ss ["volume"].append(ti.get("regularMarketVolume", -1))
                        ss ["price"].append(ti.get("regularMarketPrice", -1))
                        #limit history
                        if len(ss["time"]) > 1024:
                            del(ss["time"][0])
                            del(ss["volume"][0])
                            del(ss["price"][0])                       
                i += BATCH_SIZE
            else:
                log.critical ("yf api failed err: %s i: %d num: %d"%(err, i, len(sym_list)))
                time.sleep(2)
    except Exception as e:
        log.critical (" Exception e: %s \n s: %s ss: %s i: %d len: %d"%(e, s, ss, i, len(sym_list)))
        raise e
    log.debug("(%d)ticker stats retrieved"%( len(ticker_stats)))
    return ticker_stats
#EOF
