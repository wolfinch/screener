#! /usr/bin/env python3
'''
# Wolfinch Stock Screener
# Desc: File implements Screener ticker list and data collection
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
'''

import sys
import os

import traceback
import time
from decimal import getcontext
import logging
import requests
import pprint
from .tdata import log, _get_YF, _get_RH


def get_options(sym, exp_date=None, kind=None):
    return get_options_RH (sym, exp_date)

def get_options_RH(sym, exp_dt=None):
    start_date=None
    end_date=exp_dt
    oc_d =  _get_RH().get_option_chains(sym, start_date, end_date, None)
    if  oc_d:
        return _normalize_oc_rh(oc_d)
def _normalize_oc_rh(oc_l):
    def _norm_oc_fn(pc):
        strike_price = 0
        v = pc.get("strike_price")
        if  v != None:
            strike_price = round(float(v), 2)        
        q = pc.get("quote")        
        if not q:
            o = {
                "expiry": expiry,
                "strike": strike_price,
                "price": 0,
                "oi": 0,
                "iv": 0,
                "ask": 0,
                "bid": 0,
                "volume": 0,
                "itm": False,
                "delta": 0,
                "theta": 0,
                "gamma": 0,
                "vega": 0
            }            
        else:           
            v = q.get("mark_price", 0)
            mark_price = 0
            if  v != None:
                mark_price = round(float(v), 2)            
            v = q.get("open_interest", 0)
            oi = 0
            if  v != None:
                oi = int(v)
            v = q.get("implied_volatility")
            iv = 0
            if  v != None:
                iv = round(float(v), 2)                  
            v = q.get("ask_price", 0)
            ask = 0
            if  v != None:
                ask = round(float(v), 2)            
            v = q.get("bid_price", 0)
            bid = 0
            if  v != None:
                bid = round(float(v), 2)            
            v = q.get("volume", 0)
            vol = 0
            if  v != None:
                vol = round(float(v), 2)            
            v = q.get("delta")
            delta = 0
            if  v != None:
                delta = round(float(v), 4)
            v = q.get("delta")
            theta = 0
            if  v != None:
                theta = round(float(v), 4)       
            v = q.get("gamma")
            gamma = 0
            if  v != None:
                gamma = round(float(v), 4)       
            v = q.get("vega")
            vega = 0
            if  v != None:
                vega = round(float(v), 4)                          
            o = {
                "expiry": expiry,
                "strike": strike_price,
                "price": mark_price,
                "oi": oi,
                "iv": iv,
                "ask": ask,
                "bid": bid,
                "volume": vol,
                "itm": pc.get("inTheMoney", False),
                "delta": delta,
                "theta": theta,
                "gamma": gamma,
                "vega": vega
            }
        return o
    #loop on strikes
    n_o_l = []
    for exp, oc in oc_l.items():
        # exp -- 2022-03-12, change to 220312
        e_l = exp.split("-")
        expiry = e_l[0][2:]+e_l[1]+e_l[2]
        n_o = {"expiry": expiry,
                "calls":  list(map (_norm_oc_fn, filter(lambda o:  o["type"] == "call", oc))),
                "puts": list(map (_norm_oc_fn, filter(lambda o:  o["type"] == "put", oc)))}
        if len(n_o["calls"]) == 0 and len(n_o["puts"]) == 0:
            continue
        n_o["calls"].sort(key=lambda o: o["strike"])
        n_o["puts"].sort(key=lambda o: o["strike"])
        n_o_l.append(n_o)
    n_o_l.sort(key=lambda o: o["expiry"])
    return n_o_l

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
            oc.append(_normalize_oc_yf(c_oc))
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
def _normalize_oc_yf(oc):
    def _norm_oc_fn(pc):       
        o = {
            "expiry": expiry,
            "strike": pc["strike"],
            "price": round(pc.get("lastPrice", 0), 2),
            "oi": pc.get("openInterest", 0),
            "iv": round(pc.get("impliedVolatility", 0), 2),
            "ask": pc.get("ask", 0),
            "bid": pc.get("bid", 0),
            "volume": pc.get("volume", 0),
            "itm": pc.get("inTheMoney", False),
            "delta": 0,
            "theta": 0,
            "gamma":0
        }
        return o
    #loop on strikes
    o_e, c =  (oc["puts"], 'P') if len( oc["puts"]) else (oc["calls"], 'C')
    c_sym =o_e[0].get("contractSymbol", "")
    expiry = c_sym[c_sym.rindex(c)-6: c_sym.rindex(c)]         
    n_o = {"expiry": expiry,
            "calls":  list(map (_norm_oc_fn, oc["calls"])),
            "puts": list(map (_norm_oc_fn, oc["puts"]))}
    return n_o
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