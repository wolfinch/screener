#
# Collect all the options about tickers
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
from tkinter import E, N

from sqlalchemy import true
from .screener_base import Screener
import yahoofin as yf
import time
from datetime import datetime
import notifiers

from utils import getLogger

log = getLogger("OPTIONS")
log.setLevel(log.DEBUG)

class OPTIONS(Screener):
    def __init__(self, name="OPTIONS", ticker_kind="ALL", interval=24*60*60, **kwarg):
        log.info ("init: name: %s ticker_kind: %s interval: %d"%(name, ticker_kind, interval))
        super().__init__(name, ticker_kind, interval)
        self.YF = yf.Yahoofin ()
        self.filtered_list = {} #li
        self.i = 0
        self._e = 0
        self.delay = 0   #delay between each query on ticker
        self._d = 0
    def update(self, sym_list, ticker_stats_g):
        #if we hit an exception, wait xxx sec to clear and try again
        # sym_list = ["AAPL", "TSLA", "MSFT"]
        if self._e:
            if self._e + 300 < int(time.time()):
                self._e = None
            else:
                log.error ("exception context. retrying in %d sec"%(self._e + 300 - int(time.time())))
                return False
        if self._d:
            if self._d + self.delay < int(time.time()):
                self._d = None
            else:
                log.error ("delaying req. next in %d sec"%(self._d + self.delay - int(time.time())))
                return False
        symbol=sym_list[self.i]
        try:
            ticker_stats = ticker_stats_g.get(self.name)
            self._get_options(self.YF, symbol, ticker_stats)
            if self.i+1 >= len(sym_list):
                self.i=0
                log.info("retrieved options for all (%d) tickers"%(len(sym_list)))
                return True
            else:
                self.i+=1
                #add a delay between subsequent req
                self._d = int(time.time())
                return False
        except Exception as e:
            log.critical("exception while get data e: %s"%(e))
            self._e = int(time.time())
            return False
    def screen(self, sym_list, ticker_stats):
        # no-op , this is only a data collection 
        pass        
    def get_screened(self):
        return None

    def _get_options(self, yf, sym, ticker_stats):
        log.debug("get option chains for %s", sym)
        exp_date=None
        exp_dates=None
        i = 0
        oc=[]
        try:
            while True:
                oc_d, err =  yf.get_options(sym, exp_date)
                if err == None:
                    if exp_dates == None:
                        #first iteration. get option chain exp dates 
                        exp_dates = oc_d["expirationDates"]
                        if len(exp_dates) == 0 :
                            log.info("options unsupported for symbol %s", sym)
                            break
                    #get option chains for expdate (for the first iter, it will be nearest exp)
                    c_oc = oc_d["options"][0]
                    log.debug("exp: %d num_call: %d num_put: %d"%(c_oc["expirationDate"], len(c_oc["calls"]), len(c_oc["puts"])))
                    oc.append(c_oc)
                    i += 1
                    if i < len(exp_dates):
                        exp_date=exp_dates[i]
                    else:
                        log.debug ("got all option chains for %s. num_chains - %d", sym, len(oc))
                        break
                else:
                    log.critical ("yf api failed err: %s sym: %s"%(err, sym))
                    raise Exception ("yf API failed with error %s"%(err))
            ticker_stats[sym] = oc
        except Exception as e:
            log.critical (" Exception e: %s \n oc: %s sym: %s"%(e, oc, sym))
            raise e
        log.debug("(%s) options retrieved"%(sym))
        return ticker_stats
#EOF
