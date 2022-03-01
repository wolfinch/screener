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
    def __init__(self, name="FIN_DATA", ticker_kind="ALL", interval=24*60*60, **kwarg):
        log.info ("init: name: %s ticker_kind: %s interval: %d"%(name, ticker_kind, interval))
        super().__init__(name, ticker_kind, interval)
        self.YF = yf.Yahoofin ()
        self.filtered_list = {} #li
        self.i = 0
    def update(self, sym_list, ticker_stats):
        symbol=sym_list[self.i]
        try:
            _get_fin_data(self.YF, symbol, ticker_stats)
            if self.i+1 >= len(sym_list):
                self.i=0
                log.info("retrieved fin data for all (%d) tickers"%(len(sym_list)))
                return True
            else:
                self.i+=1
                return False
        except Exception as e:
            log.critical("exception while get data e: %s"%(e))
            return False
    def screen(self, sym_list, ticker_stats):
        # no-op , this is only a data collection 
        pass        
    def get_screened(self):
        return None

def _get_fin_data(yf, sym, ticker_stats):
#     log.debug("num tickers(%d)"%(len(sym_list)))
    #modules - defaultkeyStatistics,assetProfile,topHoldings,fundPerformance,fundProfile,financialData,summaryDetail
    modules="defaultkeyStatistics,assetProfile,topHoldings,fundPerformance,fundProfile,financialData,summaryDetail"
    ss = None
    try:
        ts, err =  yf.get_financial_data(sym, modules)
        if err == None:
            ss = ticker_stats.get(sym)
            if ss == None:
                ticker_stats[sym] = {"data": ts}
            else:
                ss ["data"] = ts                     
        else:
            log.critical ("yf api failed err: %s num: %d"%(err, sym))
    except Exception as e:
        log.critical (" Exception e: %s \n ss: %s len: %d"%(e, ss, sym))
        raise e
    log.debug("(%s) fin data retrieved"%(sym))
    return ticker_stats
#EOF
