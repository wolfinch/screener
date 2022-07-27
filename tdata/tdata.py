#! /usr/bin/env python3
'''
# Wolfinch Stock Screener
# Desc: File implements Screener ticker list and data collection
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
'''

import sys
import os
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), "../../wolfinch/pkgs"))
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), "../../wolfinch/exchanges"))

import traceback
import time
from decimal import getcontext
import logging
import requests
import pprint

import robinhood 
import yahoofin as yf
from utils import getLogger
import nasdaq

log = getLogger("DATA")
log.setLevel(logging.DEBUG)

YF = None
RH = None
### init data  src module ### 
def init():
    global YF
    if not YF:
        log.info("init yahoo fin")
        YF = yf.Yahoofin ()
    if not RH:
        log.info("init robinhood exchange")
        init_rh()
def init_rh():
    global RH
    ROBINHOOD_CONF = 'config/robinhood.yml'    
    config = {"config": ROBINHOOD_CONF,
                "products" : [],
                "candle_interval" : 300,
                'backfill': {
                    'enabled'  : True,
                    'period'   : 5,  # in Days
                    'interval' : 300,  # 300s == 5m  
                }
            }
    RH = robinhood.Robinhood(config, stream=False, auth=True)

    
### init complete ### 
def _get_YF():
    return YF
def _get_RH():
    return RH
def get_financial_data(sym):
    #modules - defaultkeyStatistics,assetProfile,topHoldings,fundPerformance,fundProfile,financialData,summaryDetail
    modules="defaultkeyStatistics,assetProfile,topHoldings,fundPerformance,fundProfile,financialData,summaryDetail,summaryProfile"
    return YF.get_financial_data(sym, modules)
def get_quotes(sym_list):
    return YF.get_quotes(sym_list)
# def get_options(sym):
    # return RH.get_option_chains(sym, None, None, None)
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
        init()
        # d = get_all_spac_tickers()
        # d = get_financial_data("TSLA")
        d = get_options("UPH")
        print("fin data %s"%(pprint.pformat(d)))
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