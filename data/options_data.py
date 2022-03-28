#! /usr/bin/env python3
'''
# Wolfinch Stock Screener
# Desc: File implements Screener ticker list and data collection
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
'''

import sys
import os
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), "../pkgs"))

import traceback
import time
from decimal import getcontext
import logging
import requests
import pprint

import yahoofin as yf
from utils import getLogger
import nasdaq

log = getLogger("DATA")
log.setLevel(logging.INFO)

# logging.getLogger("urllib3").setLevel(log.WARNING)
AVG_VOL_FILTER = 500000
MCAP_100M_FILTER = 100000000
PRICE_LT5_FILTER = 5
ticker_import_time = 0

all_tickers = {"ALL":[], "MEGACAP":[], "GT50M": [], "LT50M": [], "OTC": [], "SPAC": []}


def get_option_chain(sym, date=None, kind=None):
    

######### ******** MAIN ****** #########
if __name__ == '__main__':
    '''
    main entry point
    '''
    getcontext().prec = 8  # decimal precision
    print("Starting Wolfinch Screener..")
    try:
        log.info("Starting Main")
        print("Starting Main")
        # d = get_all_spac_tickers()
        d = get_all_ticker_lists()
        for k, v in d.items():
            print("%s #sym: %s"%( k, len(v)))
        #print("d : %s"%(pprint.pformat(d)))
    except(KeyboardInterrupt, SystemExit):
        sys.exit()
    except Exception as e:
        log.critical("Unexpected error: exception: %s" %(traceback.format_exc()))
        print("Unexpected error: exception: %s" %(traceback.format_exc()))
        raise
#         traceback.print_exc()
#         os.abort()
    # '''Not supposed to reach here'''
    print("\n end")

# EOF