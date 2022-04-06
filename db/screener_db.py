#
# wolfinch Auto trading Bot
# Desc: order_db impl
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



from utils import getLogger
from .db import init_db
from sqlalchemy import *
from sqlalchemy.orm import mapper 
import json

log = getLogger ('SCREENER-DB')
log.setLevel (log.DEBUG)

class ScreenerDb(object):
    def __init__ (self, screenerCls, screener_name, read_only=False):
        self.screenerCls = screenerCls
        self.db = init_db(read_only)
        log.info ("init screenerDb : %s "%(screener_name))
        
        self.table_name = "screener_%s"%(screener_name)
        if not self.db.engine.dialect.has_table(self.db.engine, self.table_name):  # If table don't exist, Create.
            # Create a table with the appropriate Columns
            log.info ("creating table: %s"%(self.table_name))            
            self.table = Table(self.table_name, self.db.metadata,
                Column('updated', Boolean, primary_key=True, nullable=False),
                Column('update_time', Numeric),
                Column('data', Text))
            # Implement the creation
            self.db.metadata.create_all(self.db.engine, checkfirst=True)   
        else:
            log.info ("table %s exists already"%self.table_name)
            self.table = self.db.metadata.tables[self.table_name]
        try:
            # HACK ALERT: to support multi-table with same class on sqlalchemy mapping
            class T (screenerCls):
                def __init__ (self, d=None):
                    if d != None:
                        self.updated = d.updated
                        self.update_time = d.update_time
                        self.data = json.dumps(d)
                    else:
                        self.updated = False
                        self.update_time = 0
            self.screenerCls = T
            self.mapping = mapper(self.screenerCls, self.table)
        except Exception as e:
            log.debug ("mapping failed with except: %s \n trying once again with non_primary mapping"%(e))
#             self.mapping = mapper(screenerCls, self.table, non_primary=True)            
            raise e
    def __str__ (self):
        return "{updated_time: %s, data: %s}"%(
            str(self.updated_time), str(self.data))
    def db_save_data (self, d):
        log.info ("Adding screener to db ")
        c = self.screenerCls(d)
        self.db.session.merge (c)
        self.db.session.commit()
    def db_save_all_data (self, data_l):
        log.debug ("Adding data_l list to db")
        for s, d in data_l.items():
            c = self.screenerCls(s, d)
            self.db.session.merge (c)
        self.db.session.commit()
    def db_get_data (self):
        log.debug ("retrieving data from db")
        try:
            ResultSet = self.db.session.query(self.mapping).order_by(self.screenerCls.update_time).all()
            log.info ("Retrieved %d screener data for table: %s"%(len(ResultSet), self.table_name))
            if ResultSet and len(ResultSet):
                for c in ResultSet:                
                    res = self.screenerCls()
                    if c.data:
                        res.data = json.loads(c.data)
                    res.update_time = c.update_time
                    res.updated = c.updated
            else:
                res = self.screenerCls()
                # res_list = [self.screenerCls(c.symbol, c.data) for c in ResultSet]
            #clear cache now
            self.db.session.expire_all()
            return res
        except Exception as e:
            print(str(e))     
            raise e     
    def db_get_all_data (self):
        log.debug ("retrieving data from db")
        try:
            ResultSet = self.db.session.query(self.mapping).order_by(self.screenerCls.symbol).all()
            log.info ("Retrieved %d screener data for table: %s"%(len(ResultSet), self.table_name))
            res_list = {}            
            if (len(ResultSet)):
                for c in ResultSet:
                    res_list[c.symbol] = json.loads(c.data)
                # res_list = [self.screenerCls(c.symbol, c.data) for c in ResultSet]
            #clear cache now
            self.db.session.expire_all()
            return res_list
        except Exception as e:
            print(str(e))             
# EOF
