"""
    (C) BoundedByte 2026

    pdutil.py: Pandas backend interface for CSV and SQLITE management
"""
# Dependent libraries
import pandas as pd

# Python3 builtin modules -- no extra install required
import pathlib
import sqlite3
from typing import Dict, Tuple, Union

def pandas_append_series_to_end_of_frame(df: pd.DataFrame,
                                         se: pd.Series,
                                         ) -> pd.DataFrame:
    """
        Like pd.concat, but for a DataFrame and a Series

        Parameters
        ----------
        df: DataFrame to append into
        se: Series to append as a new DataFrame row

        Returns
        -------
        (df UNION se)

        Honestly I'm not sure how much this differs from the documentation's
        suggested `pd.concat([df, se.to_frame().T], ignore_index=True)`
        Maybe worth a performance test down the line
    """
    return pd.concat((df,
                      pd.DataFrame(se).T.set_index([pd.Index([len(df)])]),
                      ))

def get_db_connection(fname: Union[pathlib.Path, str],
                      with_con: bool = False,
                      ) -> Union[sqlite3.Cursor,
                                 Tuple[sqlite3.Cursor, sqlite3.Connection]]:
    """
        Open SQLITE3 connection to given path with a cursor

        Parameters
        ----------
        fname: Database path
        with_con: Determines return value

        Returns
        -------
        sqlite3.Cursor for the database (always)
        IFF with_con=True, additionally returns the sqlite3.Connection
    """
    con = sqlite3.connect(fname)
    if with_con:
        return con.cursor(), con
    return con.cursor()

def get_tables(cur: sqlite3.Cursor,
               ) -> pd.DataFrame:
    """
        Fetch all of the tables from given cursor's main schema

        Parameters
        ----------
        cur: Cursor for the SQLITE database

        Returns
        -------
        DataFrame of the overall database schema
    """
    # Expected columns based on SQLite version 3.37.0 (2021/11/27) documentation
    # More columns may be added in the future
    expect_columns = ['schema','name','type','ncol','wr','strict']
    cur.execute('PRAGMA main.table_list;')
    records = cur.fetchall()
    return pd.DataFrame.from_records(records, columns=expect_columns)

def sqlite_db_load(dbname: Union[str, pathlib.Path],
                   ) -> Dict[str, pd.DataFrame]:
    """
        Load SQLITE tables from disk

        Parameters
        ----------
        dbname: Path to the database

        Returns
        -------
        Dictionary where key is a table name and value is a DataFrame of the table
    """
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
    """
        Save SQLITE tables to disk

        Parameters
        ----------
        dbname: path to save to on disk, should reflect the load path in most cases
        dbdatadict: Dictionary where keys are table names and values are DataFrames of the table contents
    """
    cur, con = get_db_connection(dbname, with_con=True)
    PROTECTED_TABLES = ['sqlite_sequence', 'preferences']
    for tblname, tbldata in dbdatadict.items():
        if tblname in PROTECTED_TABLES:
            continue
        tbldata.to_sql(tblname, con, if_exists='replace',
                       index=False, method='multi')

