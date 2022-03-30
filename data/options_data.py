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

import traceback
import time
from decimal import getcontext
import logging
import requests
import pprint
from .data import log, _get_YF, _get_RH


def get_options(sym, exp_date=None, kind=None):
    return get_options_yf (sym, exp_date)
def get_options_RH(sym, exp_dt=None):
    start_date=None
    end_date=exp_date
    kind = "call"
    oc_d, err =  _get_RH().get_option_chains(sym, start_date, end_date, kind)

def get_options_yf(sym, exp_dt=None):
    oc = []
    exp_dates = None
    exp_date = None
    i = 0
    while True:
        oc_d, err =  _get_YF().get_options(sym, date=exp_date)
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
    return oc

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