#
# Wolfinch Auto trading Bot
# Desc:  Market Screener config
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

import importlib

# from .vol_spike import VOL_SPIKE

def import_strat(cls_name):
    strat_path = "."+cls_name.lower()
    try:
        mod = importlib.import_module(strat_path, package="strategies")
        return getattr(mod, cls_name.upper(), None)
    except ModuleNotFoundError as e:
        print("error loading module - %s"%(str(e)))
        raise e

def Configure (cfg_l):
    scrnr_list = []
    
    print (cfg_l)
    for cfg in cfg_l:
        strat = import_strat (cfg["strategy"])
        scrnr_list.append(strat(**cfg))
#     scrnr_list.append(VOL_SPIKE("VOL-SPIKE-MEGACAP1", ticker_kind="MEGACAP", vol_multiplier=2))
#     scrnr_list.append(VOL_SPIKE("VOL-SPIKE-ALL", ticker_kind="ALL"))
    # scrnr_list.append(VOL_SPIKE("VOL-SPIKE-GT50M", ticker_kind="GT50M500K", vol_multiplier=3))
    # scrnr_list.append(VOL_SPIKE("VOL-SPIKE-LT50M", ticker_kind="LT50M500K", vol_multiplier=4))
    return scrnr_list

#EOF