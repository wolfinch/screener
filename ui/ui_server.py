#! /usr/bin/env python3
#
# Wolfinch Auto trading Bot
# Desc: Screener UI impl
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

import sys
from decimal import getcontext
import argparse
import os
import json
from flask import Flask, request, jsonify
import threading

from utils import getLogger

log = getLogger("UI")
log.setLevel(log.DEBUG)

static_file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data/')

UI_CODES_FILE = "data/ui_codes.json"
UI_TRADE_SECRET = None
UI_PAGE_SECRET = None

g_options_cb = None

def server_main (port=8080):
    global g_options_cb
        
    app = Flask(__name__, static_folder='web/', static_url_path='/web/')
    
    def get_ui_secret():
        return str(UI_PAGE_SECRET) if UI_PAGE_SECRET != None else None
        
    @app.route('/wolfinch/screener/js/<path>')    
    @app.route('/<secret>/wolfinch/screener/js/<path>')
    def send_js_api(path, secret=None):
        return app.send_static_file('js/'+path)

    @app.route('/screener/stylesheet.css')
    @app.route('/wolfinch/screener/stylesheet.css')
    @app.route('/<secret>/wolfinch/screener/stylesheet.css')
    def stylesheet_page_api(secret=None):
        if secret != get_ui_secret():
            log.error ("wrong code: " + str(secret))
            return ""
        return app.send_static_file('stylesheet.css')

    @app.route('/')
    @app.route('/wolfinch/screener')
    @app.route('/<secret>/wolfinch/screener')
    def root_page_api(secret=None):
        if secret != get_ui_secret():
            log.error ("wrong code: " + str(secret))
            return ""
        return app.send_static_file('index.html')
        
    @app.route('/wolfinch/screener/api/data')
    @app.route('/screener/api/data')
    def get_screener_data_api():     
        try:         
            log.debug("get data")
            screener_data = g_get_data_cb()
            return json.dumps(screener_data)
        except Exception as e:
            log.error ("Unable to get screener data. Exception: %s", e)
            return "[]"
            
    @app.route('/screener/api/options/tickers', methods=['GET'])
    @app.route('/wolfinch/screener/api/options/tickers', methods=['GET'])
    def get_options_tickers_api():
        if g_options_cb and g_options_cb.get('get_tickers'):
            return jsonify({"tickers": g_options_cb['get_tickers']()})
        return jsonify({"tickers": []})

    @app.route('/screener/api/options/tickers', methods=['POST'])
    @app.route('/wolfinch/screener/api/options/tickers', methods=['POST'])
    def add_options_ticker_api():
        try:
            data = request.get_json()
            ticker = data.get('ticker', '').strip().upper()
            if ticker and g_options_cb and g_options_cb.get('add_ticker'):
                tickers = g_options_cb['add_ticker'](ticker)
                log.debug("added options ticker: %s", ticker)
                return jsonify({"tickers": tickers})
        except Exception as e:
            log.error("failed to add options ticker: %s", e)
        return jsonify({"tickers": []})

    @app.route('/screener/api/options/tickers', methods=['DELETE'])
    @app.route('/wolfinch/screener/api/options/tickers', methods=['DELETE'])
    def remove_options_ticker_api():
        try:
            data = request.get_json()
            ticker = data.get('ticker', '').strip().upper()
            if ticker and g_options_cb and g_options_cb.get('remove_ticker'):
                tickers = g_options_cb['remove_ticker'](ticker)
                log.debug("removed options ticker: %s", ticker)
                return jsonify({"tickers": tickers})
        except Exception as e:
            log.error("failed to remove options ticker: %s", e)
        return jsonify({"tickers": []})

    @app.route('/screener/api/options/data', methods=['GET'])
    @app.route('/wolfinch/screener/api/options/data', methods=['GET'])
    def get_options_data_api():
        try:
            log.debug("get options data")
            if g_options_cb and g_options_cb.get('get_data'):
                data = g_options_cb['get_data']()
                return json.dumps(data)
        except Exception as e:
            log.error("Unable to get options data. Exception: %s", e)
        return "{}"

    @app.route('/screener/api/options/ticker/<sym>', methods=['GET'])
    @app.route('/wolfinch/screener/api/options/ticker/<sym>', methods=['GET'])
    def get_options_ticker_data_api(sym):
        try:
            log.debug("get options ticker data: %s", sym)
            if g_options_cb and g_options_cb.get('get_ticker_data'):
                data = g_options_cb['get_ticker_data'](sym)
                return json.dumps(data)
        except Exception as e:
            log.error("Unable to get options ticker data. Exception: %s", e)
        return "{}"

    log.debug("static_dir: %s root: %s" % (static_file_dir, app.root_path))
    
    log.debug ("starting server..")
    app.run(host='0.0.0.0', port=port, debug=False)
    log.error ("server finished!")
def ui_main (port=8080):
    try:
        log.info ("init UI server")
        server_main(port=port)
    except Exception as e:
        log.critical("ui excpetion e: %s" % (e))

g_get_data_cb = None
g_ui_thread = None
def ui_init(port=8080, get_data_cb=None, options_cb=None):
    global g_get_data_cb, g_options_cb, g_ui_thread
    g_get_data_cb = get_data_cb
    g_options_cb = options_cb
    g_ui_thread = threading.Thread(target=ui_main, args=(port,))
    g_ui_thread.daemon = True
    g_ui_thread.start()

def ui_end():
#     g_ui_thread.join()
    pass

def arg_parse ():
    parser = argparse.ArgumentParser(description='Wolfinch screener UI Server')

    parser.add_argument('--version', action='version', version='%(prog)s 0.0.1')
    parser.add_argument("--clean", help='Clean states and exit. Clear all the existing states', action='store_true')
    
    args = parser.parse_args()
    
    if (args.clean):
        exit (0)

######### ******** MAIN ****** #########
if __name__ == '__main__':
    
    arg_parse()
    
    getcontext().prec = 8  # decimal precision
    
    print("Starting Wolfinch screener UI server..")
    
    try:
        log.debug ("Starting screener UI forever loop")
        server_main ()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
    except:
        print ("Unexpected error: ", sys.exc_info())
        raise
    # '''Not supposed to reach here'''
    print("\nWolfinch screener UI Server end")

# EOF