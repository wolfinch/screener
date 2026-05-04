#! /usr/bin/env python3
'''
# Wolfinch Stock Screener
# Desc: Main File implements Screener Entry points
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
import time
import traceback
import argparse
from decimal import getcontext
import random
import logging
import gc
import json

# detect --sim early before heavy imports
g_sim_mode = '--sim' in sys.argv
g_options_only = '--options-only' in sys.argv

if not g_sim_mode:
    if not g_options_only:
        from strategies.screener_base import Tstats
        from strategies import Configure
        # import notifiers
        from db import ScreenerDb, clear_db
        from utils import getLogger, readConf
    else:
        from utils import getLogger
    import tdata
    log = getLogger("Screener")
    log.setLevel(logging.ERROR)
    # mpl_logger = logging.getLogger('matplotlib')
    # mpl_logger.setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(log.WARNING)
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
    log = logging.getLogger("Screener")

import ui

ScreenerConfig = None
ticker_import_time = 0

# global Variables
MAIN_TICK_DELAY = 1  # 500*4 milli

from strategies import option_strats

def screener_init():
    global ScreenerConfig
    # seed random
    random.seed()

    option_strats.load_watchlist()
    options_cb = option_strats.make_options_cb(sim_mode=g_sim_mode)

    if g_sim_mode:
        print("Running in SIMULATION mode with fake data")
        log.info("sim mode - skipping data init and screener registration")
        ui.ui_init(port=8080, get_data_cb=get_screener_data, options_cb=options_cb)
        return

    option_strats.init_options_db()

    #init data source
    tdata.init()

    if g_options_only:
        print("Running in OPTIONS-ONLY mode — main screeners disabled")
        log.info("options-only mode - skipping screener registration")
        ui.ui_init(port=8080, get_data_cb=get_screener_data, options_cb=options_cb)
        return

    # print ("config: %s"%(ScreenerConfig))
    notifier = ScreenerConfig.get("notifier")
    if notifier != None:
        if False == notifiers.init(notifier):
            log.critical("notifier init failed")
            return False
    register_screeners(ScreenerConfig.get("strategies"))
    
    # setup ui if required
    if ScreenerConfig["ui"]["enabled"]:
        log.info("ui init")
        if False == ui.ui_init(port=ScreenerConfig["ui"].get("port"), get_data_cb=get_screener_data, options_cb=options_cb) :
            log.critical("unable to setup ui!! ")
            print("unable to setup UI!!")
            sys.exit(1)

def screener_end():
    log.info("Finalizing Screener")

    # stop stats thread
    log.info("waiting to stop stats thread")
    # notifiers.end()
    ui.ui_end()
    log.info("all cleanup done.")

def screener_main():
    """
    Main Function for Screener
    """
    if g_sim_mode:
        log.info("sim mode - idle loop")
        while True:
            time.sleep(5)
        return

    sleep_time = MAIN_TICK_DELAY
    gc_time = 0
    while True:
        cur_time = time.time()
        try:
            tdata.ensure_session()
            if not g_options_only:
                update_data()
                process_screeners()
            option_strats.update_options_data()
        except Exception as e:
            log.critical("exception in main loop: %s" %(traceback.format_exc()))
            print("exception in main loop: %s" %(traceback.format_exc()), flush=True)
            time.sleep(10)
        if gc_time + 6*60*60 < int(time.time()):
            log.info("force garbage collect")
            gc.collect()
            gc_time = int(time.time())
        # '''Make sure each iteration take exactly LOOP_DELAY time'''
        sleep_time = (MAIN_TICK_DELAY -(time.time()- cur_time))
#         if sleep_time < 0 :
#             log.critical("******* TIMING SKEWED(%f)******"%(sleep_time))
        sleep_time = 0 if sleep_time < 0 else sleep_time
        time.sleep(sleep_time)
    # end While(true)

g_screeners = []
g_ticker_stats = {}
def register_screeners(cfg):
    global g_screeners
    log.debug("registering screeners")
    g_screeners = Configure(cfg)
    for scrn_obj in g_screeners:
        #create data holders for each screener
        db = ScreenerDb(Tstats, scrn_obj.name)
        t_stats = db.db_get_data()
        g_ticker_stats[scrn_obj.name] = Tstats(t_stats.data or {})
        g_ticker_stats[scrn_obj.name].db = db
        g_ticker_stats[scrn_obj.name].updated = scrn_obj.updated = t_stats.updated
        g_ticker_stats[scrn_obj.name].update_time = scrn_obj.update_time = t_stats.update_time
def update_data():
    #update stats only during ~12hrs, to cover pre,open,ah
    log.debug("updating data")
    sym_list = get_all_tickers()
    for scrn_obj in g_screeners:
        if scrn_obj.interval + scrn_obj.update_time < int(time.time()):
            s_list = sym_list.get(scrn_obj.ticker_kind)
            if not s_list :
                log.critical("unable to find ticker list kind %s"%(scrn_obj.ticker_kind))
                continue
            log.info ("updating screener data for %s num_sym: %d"%(scrn_obj.name, len(s_list)))                
            if scrn_obj.update(s_list, g_ticker_stats):
                scrn_obj.updated = True
                g_ticker_stats[scrn_obj.name].updated = True
                #update time. 
                # Sometimes, data not updated during market close etc. handle this in screener, update routine 
                scrn_obj.update_time = int(time.time())                
                g_ticker_stats[scrn_obj.name].update_time = scrn_obj.update_time
                g_ticker_stats[scrn_obj.name].db.db_save_data(g_ticker_stats[scrn_obj.name])
                log.info("screener data %s saved to db "%(scrn_obj.name))
            else:
                g_ticker_stats[scrn_obj.name].updated = False

def process_screeners ():
    log.debug("processing screeners")
    sym_list = get_all_tickers()    
    for scrn_obj in g_screeners:
        if scrn_obj.updated :
            s_list = sym_list.get(scrn_obj.ticker_kind)
            if not s_list :
                log.critical("unable to find ticker list kind %s"%(scrn_obj.ticker_kind))
                continue            
            log.info ("running screener - %s sym_num: %d"%(scrn_obj.name, len(s_list)))
            scrn_obj.screen(s_list, g_ticker_stats)
            scrn_obj.updated = False
            
def get_all_screener_data():
    #run thru all screeners and collect filtered data
    filtered_list = {}
    for scrn_obj in g_screeners:
        log.info("get screener data from %s"%(scrn_obj.name))
        filtered_list[scrn_obj.name] = scrn_obj.get_screened()
    return filtered_list

all_tickers = {"ALL":[], "MEGACAP":[], "GT50M": [], "LT50M": [], "OTC": [],
               "ALL500K":[], "MEGACAP500K":[], "GT50M500K": [], "LT50M500K": [], "OTC500K": [], "SPAC": []}
def get_all_tickers ():
    global ticker_import_time, all_tickers
    log.debug ("get all tickers")
    if ticker_import_time + 24*3600 < int(time.time()) :
        all_tickers = tdata.get_all_ticker_lists()
        ticker_import_time = int(time.time())
    return all_tickers
    
def get_sim_screener_data():
    now = int(time.time())
    sim_tickers = [
        {"symbol": "AAPL",  "last_price": 189.45, "price_change": 2.31,  "cur_price_change": 2.55,  "vol_change": 145.2, "cur_vol_change": 150.1, "time": now - 300},
        {"symbol": "TSLA",  "last_price": 248.10, "price_change": -1.82, "cur_price_change": -1.50, "vol_change": 210.5, "cur_vol_change": 215.3, "time": now - 900},
        {"symbol": "NVDA",  "last_price": 135.72, "price_change": 5.14,  "cur_price_change": 5.40,  "vol_change": 320.0, "cur_vol_change": 330.8, "time": now - 60},
        {"symbol": "AMD",   "last_price": 164.33, "price_change": 3.67,  "cur_price_change": 3.90,  "vol_change": 180.3, "cur_vol_change": 185.0, "time": now - 1800},
        {"symbol": "MSFT",  "last_price": 425.88, "price_change": 0.95,  "cur_price_change": 1.10,  "vol_change": 110.7, "cur_vol_change": 112.4, "time": now - 5400},
        {"symbol": "GOOGL", "last_price": 176.20, "price_change": -0.45, "cur_price_change": -0.30, "vol_change": 95.1,  "cur_vol_change": 98.2,  "time": now - 7200},
        {"symbol": "META",  "last_price": 510.34, "price_change": 1.78,  "cur_price_change": 2.00,  "vol_change": 155.6, "cur_vol_change": 160.0, "time": now - 3600},
        {"symbol": "AMZN",  "last_price": 186.50, "price_change": -2.10, "cur_price_change": -1.80, "vol_change": 200.4, "cur_vol_change": 205.1, "time": now - 600},
        {"symbol": "NFLX",  "last_price": 628.90, "price_change": 4.22,  "cur_price_change": 4.50,  "vol_change": 275.0, "cur_vol_change": 280.3, "time": now - 120},
        {"symbol": "SOFI",  "last_price": 8.75,   "price_change": 6.50,  "cur_price_change": 7.10,  "vol_change": 450.2, "cur_vol_change": 460.0, "time": now - 180},
    ]
    sim_tickers_2 = [
        {"symbol": "PLTR",  "last_price": 24.15,  "price_change": 3.10,  "cur_price_change": 3.40,  "vol_change": 190.5, "cur_vol_change": 195.0, "time": now - 400},
        {"symbol": "RIVN",  "last_price": 11.82,  "price_change": -4.50, "cur_price_change": -4.10, "vol_change": 310.2, "cur_vol_change": 315.0, "time": now - 2400},
        {"symbol": "COIN",  "last_price": 225.60, "price_change": 7.20,  "cur_price_change": 7.80,  "vol_change": 380.1, "cur_vol_change": 390.5, "time": now - 90},
        {"symbol": "MARA",  "last_price": 19.44,  "price_change": 12.30, "cur_price_change": 13.00, "vol_change": 520.0, "cur_vol_change": 540.2, "time": now - 45},
        {"symbol": "SNAP",  "last_price": 11.20,  "price_change": -3.20, "cur_price_change": -2.90, "vol_change": 160.8, "cur_vol_change": 165.0, "time": now - 86000},
    ]
    fmt = {"symbol": "symbol", "last_price": "last price",
           "price_change": "% price", "cur_price_change": "% cur price",
           "vol_change": "% vol", "cur_vol_change": "% cur vol", "time": "time"}
    return {
        "SIM-VOL-SPIKE-MEGACAP": {"format": fmt, "data": sim_tickers, "sort": "time"},
        "SIM-VOL-SPIKE-SMALL": {"format": fmt, "data": sim_tickers_2, "sort": "time"}
    }

def get_screener_data():
#     log.info("msg %s"%(msg))
    if g_sim_mode:
        return get_sim_screener_data()
    data_set = get_all_screener_data()
    return data_set

def clean_states():
    ''' 
    clean states
    '''
    log.info("Clearing Db")
    clear_db()
def load_config (cfg_file):
    global ScreenerConfig
    ScreenerConfig = readConf(cfg_file)
    
def arg_parse():
    '''
    arg parse
    '''
    parser = argparse.ArgumentParser(description='Wolfinch Screener')

    parser.add_argument('--version', action='version', version='%(prog)s 1.0.1')
    parser.add_argument("--clean",
                        help='Clean states,dbs and exit. Clear all the existing states',
                        action='store_true')
    parser.add_argument("--config", help='Wolfinch Screener config file')    
    parser.add_argument("--port", help='API Port')
    parser.add_argument("--restart", help='restart from the previous state', action='store_true')
    parser.add_argument("--sim", help='Run in simulation mode with fake data (no config needed)', action='store_true')
    parser.add_argument("--options-only", help='Run options UI only, skip main dashboard screeners (no config needed)', action='store_true')

    args = parser.parse_args()

    if args.sim:
        log.info("sim mode enabled")
        return

    if args.options_only:
        log.info("options-only mode enabled")
        return
    
    if args.config:
        log.debug("config file: %s" % (str(args.config)))
        if False == load_config(args.config):
            log.critical("Config parse error!!")
            parser.print_help()
            exit(1)
        else:
            log.debug("config loaded successfully!")
#             exit(0)
    else:
        parser.print_help()
        exit(1)    

    if args.clean:
        clean_states()
        exit(0)

    if args.port:
        log.debug("port: %s" % (str(args.port)))
        ui.port = args.port
    else:
        pass
#         parser.print_help()
#         exit(1)

    if args.restart:
        log.debug("restart enabled")
        print("Restarting from previous state")
    else:
        log.debug("restart disabled")

######### ******** MAIN ****** #########
if __name__ == '__main__':
    '''
    main entry point
    '''
    arg_parse()
    getcontext().prec = 8  # decimal precision
    print("Starting Wolfinch Screener..")
    try:
        screener_init()
        log.info("Starting Main forever loop")
        print("Starting Main forever loop")
        screener_main()
    except(KeyboardInterrupt, SystemExit):
        screener_end()
        sys.exit()
    except Exception as e:
        log.critical("Unexpected error: exception: %s" %(traceback.format_exc()))
        print("Unexpected error: exception: %s" %(traceback.format_exc()), flush=True)
        screener_end()
        raise
#         traceback.print_exc()
#         os.abort()
    # '''Not supposed to reach here'''
    print("\nScreener end")

# EOF