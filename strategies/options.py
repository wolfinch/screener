#
# Collect all the options about tickers
#
#  Copyright: (c) 2017-2022 Wolfinch Inc.
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
import traceback
from sqlalchemy import true
from .screener_base import Screener
import tdata
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
        self.filtered_list = {} #li
        self.i = 0
        self._e = 0
        self.delay = 3   #delay between each query on ticker
        self._d = 0
    def update(self, sym_list, ticker_stats_g):
        #if we hit an exception, wait xxx sec to clear and try again
        # sym_list = ["UPH", "CLOV", "MILE"]
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
            self._get_options(symbol, ticker_stats)
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
            log.critical("exception while get data e: %s exception: %s" % (e, traceback.format_exc()))
            self._e = int(time.time())
            return False
    def screen(self, sym_list, ticker_stats):
        # no-op , this is only a data collection 
        pass        
    def get_screened(self):
        return None

    def _get_options(self, sym, ticker_stats):
        log.debug("get option chains for %s", sym)
        exp_date=None
        try:
            ticker_stats[sym] = tdata.get_options(sym, exp_date)
        except Exception as e:
            log.critical (" Exception e: %s \n sym: %s"%(e, sym))
            raise e
        log.debug("(%s) options retrieved"%(sym))
        return ticker_stats
#EOF
