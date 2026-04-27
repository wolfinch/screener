#
# Wolfinch Screener
# Desc: Options history DB persistence
#  Copyright: (c) 2017-2026 Wolfinch Inc.
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
from sqlalchemy import Table, Column, Text
from sqlalchemy import inspect as sa_inspect
import json

log = getLogger('OPTIONS-DB')
log.setLevel(log.DEBUG)

TABLE_NAME = 'options_history'


class OptionsDb(object):
    def __init__(self):
        self.db = init_db()
        if not sa_inspect(self.db.engine).has_table(TABLE_NAME):
            log.info("creating table: %s", TABLE_NAME)
            self.table = Table(TABLE_NAME, self.db.metadata,
                               Column('symbol', Text, primary_key=True, nullable=False),
                               Column('date', Text, primary_key=True, nullable=False),
                               Column('data', Text))
            self.db.metadata.create_all(self.db.engine, checkfirst=True)
        else:
            log.info("table %s exists already", TABLE_NAME)
            self.table = self.db.metadata.tables[TABLE_NAME]

    def save_snapshot(self, symbol, date_str, snapshot):
        """Upsert a daily options snapshot for a symbol."""
        data_json = json.dumps(snapshot)
        with self.db.engine.begin() as conn:
            existing = conn.execute(
                self.table.select().where(
                    (self.table.c.symbol == symbol) &
                    (self.table.c.date == date_str)
                )
            ).fetchone()
            if existing:
                conn.execute(
                    self.table.update().where(
                        (self.table.c.symbol == symbol) &
                        (self.table.c.date == date_str)
                    ).values(data=data_json)
                )
            else:
                conn.execute(
                    self.table.insert().values(
                        symbol=symbol, date=date_str, data=data_json
                    )
                )
        log.debug("saved snapshot %s %s", symbol, date_str)

    def load_all(self):
        """Load all options snapshots grouped by symbol, sorted by date.
        Returns dict: {symbol: [snap1, snap2, ...]}"""
        history = {}
        with self.db.engine.connect() as conn:
            rows = conn.execute(
                self.table.select().order_by(
                    self.table.c.symbol, self.table.c.date)
            ).fetchall()
            for row in rows:
                sym = row[0]
                snap = json.loads(row[2])
                if sym not in history:
                    history[sym] = []
                history[sym].append(snap)
        return history

    def load_symbol(self, symbol):
        """Load snapshots for a single symbol, sorted by date."""
        with self.db.engine.connect() as conn:
            rows = conn.execute(
                self.table.select().where(
                    self.table.c.symbol == symbol
                ).order_by(self.table.c.date)
            ).fetchall()
            return [json.loads(row[2]) for row in rows]

# EOF
