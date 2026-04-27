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

TABLE_AGGREGATED = 'options_history'       # daily aggregated OI/Vol/Prem + top strikes
TABLE_RAW_CHAINS = 'options_raw_chains'    # full per-strike per-expiry chain data


class OptionsDb(object):
    def __init__(self):
        self.db = init_db()
        inspector = sa_inspect(self.db.engine)
        # ── aggregated table ──
        if not inspector.has_table(TABLE_AGGREGATED):
            log.info("creating table: %s", TABLE_AGGREGATED)
            self.tbl_agg = Table(TABLE_AGGREGATED, self.db.metadata,
                                Column('symbol', Text, primary_key=True, nullable=False),
                                Column('date', Text, primary_key=True, nullable=False),
                                Column('data', Text))
        else:
            log.info("table %s exists already", TABLE_AGGREGATED)
            self.tbl_agg = self.db.metadata.tables[TABLE_AGGREGATED]
        # ── raw chains table ──
        if not inspector.has_table(TABLE_RAW_CHAINS):
            log.info("creating table: %s", TABLE_RAW_CHAINS)
            self.tbl_raw = Table(TABLE_RAW_CHAINS, self.db.metadata,
                                Column('symbol', Text, primary_key=True, nullable=False),
                                Column('date', Text, primary_key=True, nullable=False),
                                Column('data', Text))
        else:
            log.info("table %s exists already", TABLE_RAW_CHAINS)
            self.tbl_raw = self.db.metadata.tables[TABLE_RAW_CHAINS]
        self.db.metadata.create_all(self.db.engine, checkfirst=True)

    # ── generic upsert helper ──────────────────────────
    def _upsert(self, table, symbol, date_str, data_json):
        with self.db.engine.begin() as conn:
            existing = conn.execute(
                table.select().where(
                    (table.c.symbol == symbol) &
                    (table.c.date == date_str)
                )
            ).fetchone()
            if existing:
                conn.execute(
                    table.update().where(
                        (table.c.symbol == symbol) &
                        (table.c.date == date_str)
                    ).values(data=data_json)
                )
            else:
                conn.execute(
                    table.insert().values(
                        symbol=symbol, date=date_str, data=data_json
                    )
                )

    def _load_all(self, table):
        history = {}
        with self.db.engine.connect() as conn:
            rows = conn.execute(
                table.select().order_by(table.c.symbol, table.c.date)
            ).fetchall()
            for row in rows:
                sym = row[0]
                data = json.loads(row[2])
                if sym not in history:
                    history[sym] = []
                history[sym].append(data)
        return history

    def _load_symbol(self, table, symbol):
        with self.db.engine.connect() as conn:
            rows = conn.execute(
                table.select().where(
                    table.c.symbol == symbol
                ).order_by(table.c.date)
            ).fetchall()
            return [json.loads(row[2]) for row in rows]

    # ── aggregated data (daily OI/Vol/Prem totals + top strikes) ──
    def save_snapshot(self, symbol, date_str, snapshot):
        """Upsert a daily aggregated options snapshot."""
        self._upsert(self.tbl_agg, symbol, date_str, json.dumps(snapshot))
        log.debug("saved aggregated snapshot %s %s", symbol, date_str)

    def load_all(self):
        """Load all aggregated snapshots grouped by symbol.
        Returns dict: {symbol: [snap1, snap2, ...]}"""
        return self._load_all(self.tbl_agg)

    def load_symbol(self, symbol):
        """Load aggregated snapshots for a single symbol."""
        return self._load_symbol(self.tbl_agg, symbol)

    # ── raw chain data (full per-strike per-expiry chains from RH) ──
    def save_raw_chain(self, symbol, date_str, chains):
        """Upsert the full raw options chain for a symbol on a given date.
        `chains` is the list of expiry groups as returned by tdata.get_options()."""
        self._upsert(self.tbl_raw, symbol, date_str, json.dumps(chains))
        log.debug("saved raw chain %s %s", symbol, date_str)

    def load_all_raw_chains(self):
        """Load all raw chain snapshots grouped by symbol.
        Returns dict: {symbol: [chains_day1, chains_day2, ...]}"""
        return self._load_all(self.tbl_raw)

    def load_raw_chain(self, symbol):
        """Load raw chain snapshots for a single symbol."""
        return self._load_symbol(self.tbl_raw, symbol)

# EOF
