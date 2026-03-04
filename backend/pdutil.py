"""
    (C) BoundedByte 2026

    pdutil.py: Pandas backend interface for CSV and SQLITE management
"""
# Dependent libraries
import pandas as pd

# Python3 builtin modules -- no extra install required
import pathlib
import sqlite3
from typing import Callable, Dict, List, Optional, Tuple, Union

def pandas_append_series_to_end_of_frame(df: pd.DataFrame,
                                         se: pd.Series,
                                         ) -> pd.DataFrame:
    # There's probably a better way to do this, but this pattern shows up a lot
    # and it is ugly AF
    return pd.concat((df,
                      pd.DataFrame(se).T.set_index([pd.Index([len(df)])]),
                      ))

def get_db_connection(fname: Union[pathlib.Path, str],
                      with_con: bool = False,
                      ) -> Union[sqlite3.Cursor,
                                 Tuple[sqlite3.Cursor, sqlite3.Connection]]:
    # Just a SQLite3 handler
    con = sqlite3.connect(fname)
    if with_con:
        return con.cursor(), con
    return con.cursor()

def get_tables(cur: sqlite3.Cursor,
               ) -> pd.DataFrame:
    # Fetch all of the tables from given cursor's main schema

    # Expect columns based on SQLite version 3.37.0 (2021/11/27) documentation
    # More columns may be added in the future
    expect_columns = ['schema','name','type','ncol','wr','strict']
    cur.execute('PRAGMA main.table_list;')
    records = cur.fetchall()
    return pd.DataFrame.from_records(records, columns=expect_columns)

def sqlite_db_load(dbname: Union[str, pathlib.Path],
                   ) -> Dict[str, pd.DataFrame]:
    cur = get_db_connection(dbname)
    avail_tables = get_tables(cur)
    cur.close()
    all_table_data = dict()

    # Pandas does not support retrieving the sqlite_schema, but we do not need it
    skip_names = ['sqlite_schema']
    for table_name in avail_tables['name']:
        if table_name in skip_names:
            continue
        # Pandas only supports URIs for now; cannot reuse sqlite cursor/connection
        all_table_data[table_name] = pd.read_sql_table(table_name,
                                                       f"sqlite:///{dbname}")
    return all_table_data

def sqlite_db_save(dbname: str,
                   dbdatadict: Dict[str, pd.DataFrame],
                   ) -> None:
    cur, con = get_db_connection(dbname, with_con=True)
    PROTECTED_TABLES = ['sqlite_sequence']
    for tblname, tbldata in dbdatadict.items():
        if tblname in PROTECTED_TABLES:
            continue
        tbldata.to_sql(tblname, con, if_exists='replace',
                       index=False, method='multi')

