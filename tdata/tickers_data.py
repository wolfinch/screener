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
from .tdata import log, get_quotes
import nasdaq


# logging.getLogger("urllib3").setLevel(log.WARNING)
AVG_VOL_FILTER = 500000
MCAP_100M_FILTER = 100000000
PRICE_LT10_FILTER = 10
ticker_import_time = 0

all_tickers = {"ALL":[], "MEGACAP":[], "GT50M": [], "LT50M": [], "OTC": [], "SPAC": []}
def get_all_ticker_lists ():
    global ticker_import_time, all_tickers
    # log.debug ("get all tickers")
    if ticker_import_time + 24*3600 < int(time.time()) :
        log.info ("renew tickers list")
#         t_l = nasdaq.get_all_tickers_gt50m()
        try:
            #import all tickers
            t_l = nasdaq.get_all_tickers()
            if t_l:
                allt = []
                for ticker in t_l:
                    allt.append(ticker["symbol"].strip())
                log.info("ALL (%d) tickers imported"%(len(allt)))
                all_tickers["ALL"] = allt
            #import megacap only
            t_l = nasdaq.get_all_tickers_megacap()
            if t_l:
                mcap = []
                for ticker in t_l:
                    mcap.append(ticker["symbol"].strip())
                log.info("MEGACAP (%d) tickers imported"%(len(mcap)))
                all_tickers["MEGACAP"] = mcap
            #import gt50m
            t_l = nasdaq.get_all_tickers_gt50m()
            if t_l:
                gt50 = []
                for ticker in t_l:
                    gt50.append(ticker["symbol"].strip())
                log.info("GT50M (%d) tickers imported"%(len(gt50)))
                all_tickers["GT50M"] = gt50
            #import lt50m
            t_l = nasdaq.get_all_tickers_lt50m()
            if t_l:
                lt50 = []
                for ticker in t_l:
                    lt50.append(ticker["symbol"].strip())
                all_tickers["LT50M"] = lt50
                log.info("LT50M (%d) tickers imported"%(len(lt50)))
            #import spacs
            t_l = get_all_spac_tickers()
            if t_l:
                all_tickers["SPAC"] = t_l
                log.info("SPAC (%d) tickers imported"%(len(t_l)))
            #get filtered list based on vol
            # tl = ["UPH", "ARVL"]
            # all_tickers["GT100M500KLT10"] = tl
            # all_tickers["GT100M500K"] = tl
            get_filtered_ticker_list()            
            ticker_import_time = int(time.time())
        except Exception :
            log.critical("exception occured while getting filtered list")
    return all_tickers

def get_filtered_ticker_list():
    global all_tickers
    BATCH_SIZE = 400
#     log.debug("num tickers(%d)"%(len(sym_list)))
    s = None
    ss = None
    i = 0
    try:
        ticker_stats = {}
        sym_list = all_tickers["ALL"]
        while i < len(sym_list):
            ts, err =  get_quotes(sym_list[i: i+BATCH_SIZE])
            log.info("got %d syms out of %s", i+BATCH_SIZE, len(all_tickers["ALL"]))
            if err == None:
                for ti in ts:
                    s = ti.get("symbol")
                    ss = ticker_stats.get(s)
                    if ss == None:
                        ticker_stats[s] = ti
                i += BATCH_SIZE
            else:
                log.critical ("yf api failed err: %s i: %d num: %d"%(err, i, len(sym_list)))
                time.sleep(2)
        #find all tickers >100M market cap
        tl = []
        for s in all_tickers["ALL"]:
            st = ticker_stats.get(s)
            if st and st.get("marketCap", 0) >= MCAP_100M_FILTER and st.get("quoteType") == "EQUITY":
                tl.append(s)
        all_tickers["GT100M"] = tl
        log.info ("# GT100M tickers %s", len(tl))
        #find all tickers >100M market cap and 500K avg volume
        tl = []
        for s in all_tickers["GT100M"]:
            st = ticker_stats.get(s)
            if st and st.get("averageDailyVolume3Month", 0) >= AVG_VOL_FILTER :
                tl.append(s)
        # tl = ["TSLA", "NIO", "MSFT", "INO", "ARVL"]
        all_tickers["GT100M500K"] = tl
        log.info ("# GT100M500K tickers %s", len(tl))
        ## find all tickers less than $5 and GT 100M mcap and 500K volume
        tl = []
        for s in all_tickers["GT100M500K"]:
            st = ticker_stats.get(s)
            if st and st.get("regularMarketPrice", 0) <= PRICE_LT10_FILTER and st.get("quoteType") == "EQUITY":
                tl.append(s)
        # tl = ["TSLA", "NIO", "MSFT", "INO", "ARVL"]
        all_tickers["GT100M500KLT10"] = tl
        log.info ("# GT100M500KLT10 tickers %s \n tl- %s", len(tl), tl)
                
        #get all tickers >500K volume 
        tl = []
        for s in all_tickers["ALL"]:
            st = ticker_stats.get(s)
            if st and st.get("averageDailyVolume3Month", 0) >= AVG_VOL_FILTER:
                tl.append(s)
        all_tickers["ALL500K"] = tl
        log.info ("# ALL500K tickers %s", len(tl))
        tl = []
        for s in all_tickers["GT50M"]:
            st = ticker_stats.get(s)
            if st and st.get("averageDailyVolume3Month", 0) >= AVG_VOL_FILTER:
                tl.append(s)
        all_tickers["GT50M500K"] = tl
        log.info ("# GT50M500K tickers %s", len(tl))
        tl = []
        for s in all_tickers["LT50M"]:
            st = ticker_stats.get(s)
            if st and st.get("averageDailyVolume3Month", 0) >= AVG_VOL_FILTER:
                tl.append(s)
        all_tickers["LT50M500K"] = tl
        log.info ("# LT50M500K tickers %s", len(tl))
        tl = []
        for s in all_tickers["MEGACAP"]:
            st = ticker_stats.get(s)
            if st and st.get("averageDailyVolume3Month", 0) >= AVG_VOL_FILTER:
                tl.append(s)
        all_tickers["MEGACAP500K"] = tl
        log.info ("# MEGACAP500K tickers %s", len(tl))
        tl = []
        for s in all_tickers["OTC"]:
            st = ticker_stats.get(s)
            if st and st.get("averageDailyVolume3Month", 0) >= AVG_VOL_FILTER:
                tl.append(s)
        all_tickers["OTC500K"] = tl
        log.info ("# OTC500K tickers %s", len(tl))
    except Exception as e:
        log.critical (" Exception e: %s \n s: %s ss: %s i: %d len: %d"%(e, s, ss, i, len(sym_list)))
        raise e

Session = None
def get_url(url):
    global Session
    if Session == None:
        Session = requests.session()
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en;q=1, fr;q=0.9, de;q=0.8, ja;q=0.7, nl;q=0.6, it;q=0.5",  # noqa: E501
#             "sec-ch-ua": "Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99",
            "Connection": "keep-alive",
            "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
        }
        Session.headers = headers
        log.info("initialized Session")
    log.debug ("get url: %s"%(url))
    r = Session.get(url, timeout=15)
    if r.status_code == requests.codes.ok:
        return r.json()
    else:
        log.error ("bad response code: %s resp: %s"%(str(r.status_code), r))
        return None

SPAC_TICKERS_SPACTRACK_URL = "https://spreadsheets.google.com/feeds/list/1F7gLiGZP_F4tZgQXgEhsHMqlgqdSds3vO0-4hoL6ROQ/o41rryg/public/values?alt=json"
def get_all_spac_tickers():
    log.debug ("get all tickers")
    spacs = []    
    spacs_d = get_url(SPAC_TICKERS_SPACTRACK_URL)
    if spacs_d: 
        feed = spacs_d.get("feed")
        if feed:
            spacs_l = feed.get("entry")
#             log.debug ("entry : %s"%(spacs_l[0]))
            for k,v in spacs_l[0].items():
#                 print(k, v)
                if isinstance(v, dict):
                    for _, v1 in v.items():
                        if v1 == 'SPAC Ticker-Filter':
#                             print("commons %s"%k)
                            ticker_key = k
            for spac in spacs_l:
                ticker = spac[ticker_key]["$t"]
                if ticker == "SPAC Ticker-Filter" or ticker == "XXXX":
                    continue
                spacs.append(ticker)
#         for ticker in spacs_l:
    return spacs

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