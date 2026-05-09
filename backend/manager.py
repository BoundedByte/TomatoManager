"""
    (C) BoundedByte 2026

    manager.py: SuperClass for Metadata managers
        Basic global implementation for:
            * Initialization
            * Converting to common format and caching it
            * Comparison to other Manager objects
            * Searching within records
            * Dummy write checks
            * Merging with other Manager objects
            * Basic API for extending string report representation
        Subclasses have to implement:
            * Reading from disk and writing back to disk
            * String-ified reporting for records
"""

# Dependent libraries
import pandas as pd

# Local libraries
from .metadata import TomatoManagerTags

# Python3 builtin modules -- no extra install required
import argparse
import pathlib
from typing import List, Generator, Optional, Tuple, Union

class Manager():
    """
        Abstract database manager for some kind of metadata library tool or program

        Provides interoperability between all Manager subclasses wrt:
            * Reading database from disk in original format
            * Converting to common TomatoManager representation
            * Common file identification and metadata comparison
            * Search within database
            * Merging / writing metadata for specific files
            * Reporting state in string-ified form
            * Writing updates to disk in original format
    """
    def __repr__(self):
        return f"{self.__class__.__name__} at {hex(id(self))}"

    def __init__(self,
                 file_target: pathlib.Path,
                 ) -> None:
        """
            Memorize the target filepath, read it from disk and bind to self.mappings
        """
        self.file_target = file_target
        self.bind_from_disk()
        # If you make a change that invalidates the cache, you should set
        # self.cache to None
        self.cache = None

    def bind_from_disk(self,
                       bind: bool = True,
                       ) -> Optional[pd.DataFrame]:
        """
            Read database from disk and optionally bind to self.mappings, if not bound, return DB
            Always unset cache if changing the underlying mapping object

            If self.file_target does not exist, set self.mappings = None and
            return None regardless of bind setting
            ```
            if not self.file_target.exists():
                self.mappings = None
                self.cache = None
                return
            ```

            Should bind DataFrame to self.mappings IFF bind == True,
            else return the DataFrame after setting self.mappings = None
            ```
            mappings = # Some way to load from self.file_target
            if bind:
                self.mappings = mappings
                self.cache = None
            else:
                return mappings
            ```
        """
        raise NotImplemented

    def bind_to_disk(self,
                     ) -> None:
        """
            Should write current values of self.mappings to self.file_target
        """
        raise NotImplemented

    def partial_mapping_update(self,
                               updated_mappings,
                               ) -> None:
        pass

    def to_common(self,
                  ) -> pd.DataFrame:
        """
            Should return a common-format DataFrame
                columns = SourceFile+TomatoManagerTags
        """
        # To find assignable metadata by columns:
        # self.to_common().apply(lambda x: pd.isna(x)).sum(axis=0)
        basis = self.mappings.copy()
        # Drop uncommon columns
        for col in basis.columns:
            if col == 'SourceFile':
                continue
            if col not in TomatoManagerTags:
                basis = basis.drop(columns=[col])
        # Add common columns
        for col in TomatoManagerTags:
            if col not in basis.columns:
                basis.insert(len(basis.columns), col, [None]*len(basis))
        # Ensure proper order
        basis = basis[['SourceFile']+TomatoManagerTags]
        return basis

    def cached_common(self,
                      ) -> pd.DataFrame:
        """
            Version of to_common() that you should attempt to use when many
            operations or sub-operations will conver the representation without
            making underlying changes.
            If you make a change that invalidates the cache, you should set
            self.cache to None
        """
        if self.cache is None:
            self.cache = self.to_common()
        return self.cache

    def intersect(self,
                  other_manager: object,
                  limit_paths: Optional[List[pathlib.Path]] = None,
                  ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
            Make a common intersection pair of DataFrames for given manager and self

            Parameters
            ----------
            other_manager: Manager object to compare against (as common)
            limit_paths: Filter file paths to only concern this list, if given

            Returns
            -------
            Common-formatted dataframes for common files between self and other_manager
            Indices are NOT reset so they still properly lookup in each manager's respective
            common format
        """
        if limit_paths is not None and not isinstance(limit_paths, list):
            limit_paths = [limit_paths]

        own = self.cached_common()
        other = other_manager.cached_common()
        if limit_paths is not None:
            own = own[own['SourceFile'].isin(map(str,limit_paths))]
            other = other[other['SourceFile'].isin(map(str,limit_paths))]
        common_source_files = sorted(set(own['SourceFile']).intersection(set(other['SourceFile'])))
        own_index = own[own['SourceFile'].isin(common_source_files)].sort_values(by=['SourceFile']).index
        other_index = other[other['SourceFile'].isin(common_source_files)].sort_values(by=['SourceFile']).index
        return (own.loc[own_index],
               other.loc[other_index])

    def compare(self,
                path: pathlib.Path,
                other_manager: object,
                ) -> bool:
        """
            Evaluate metadata similarity between Managers

            Parameters
            ----------
            path: file to compare between self and other_manager

            Returns
            -------
            True IFF all metadata are symmetric
        """
        own, other = self.intersect(other_manager, path)
        return own.reset_index(drop=True).equals(other.reset_index(drop=True))

    def search(self,
               key: Optional[Union[str,List[str]]],
               value: str,
               ) -> List[pathlib.Path]:
        """
            Search for a given value in the common representation

            Parameters
            ----------
            key: Optional common column(s) to focus search on
            value: Target to match (as substring match, regex permitted)

            Returns
            -------
            List of paths that satisfy the search criteria
        """
        df = self.cached_common().infer_objects()
        if key is not None:
            if not isinstance(key, list):
               key = [key]
            df = df[['SourceFile']+key]
        per_col = list()
        for column in df.columns:
            if column == 'SourceFile':
                continue
            # Only string matching for now
            # TODO: date matching separately
            if df[column].dtype != 'O':
                continue
            matches = df[column].str.contains(value)
            per_col.append(matches)
        sdf = pd.concat(per_col, axis=1)
        dfs = sdf.sum(axis=1)
        return list(set(df.loc[dfs[dfs > 0].index, 'SourceFile'].tolist()))

    def plan_write(self,
                   path: pathlib.Path,
                   metadata_write: str,
                   ) -> bool:
        """
            Simulates a write on the common representation to see if a change is induced

            Parameters
            ----------
            path: File to simulate write upon
            metadata_write: 'Key:Value' metadata to potentially update

            Returns
            -------
            True IFF tag would change metadata representation in manager

            Raises
            ------
            ValueError if metadata_write cannot be read
        """
        try:
            field, value = metadata_write.split(':',1)
        except:
            raise ValueError(f"Improperly formatted metadata write! Should be <key>:<value>")
        common = self.cached_common()
        current = common[common['SourceFile'] == str(path)]
        return current[field].tolist()[0] != value

    def merge(self,
              other_manager: object,
              merge_queue: List[pathlib.Path],
              bind: bool = True,
              ) -> Optional[pd.DataFrame]:
        """
            Overwrite own mappings with other_manager matches

            Parameters
            ----------
            other_manager: Manager with authoritative data that overrides self.mappings
            merge_queue: Paths to update in self.mappings
            bind: Whether to commit to own representation or return updated version

            Returns
            -------
            Updated mappings WITHOUT altering self.mappings if bind=False, otherwise updates in place
        """
        bindable = self.cached_common().copy()
        own_intersect, other_intersect = self.intersect(other_manager, limit_paths=merge_queue)
        for own_index, other_index in zip(own_intersect.index, other_intersect.index):
            own_row = own_intersect.loc[own_index]
            other_row = other_intersect.loc[other_index]
            for field in TomatoManagerTags:
                if not pd.isna(other_row[field]) and\
                        (pd.isna(own_row[field]) or own_row[field] != other_row[field]):
                    bindable.loc[own_index,field] = other_row[field]
        if bind:
            self.mappings = bindable
            self.common_cache = None
        else:
            return bindable[bindable['SourceFile'].isin(map(str,merge_queue))]

    def string_options(self,
                       initial_str: str,
                       options: Optional[argparse.Namespace],
                       ) -> str:
        """
            Update strings for use in report() based on command line options

            Parameters
            ----------
            initial_str: Unmodified string for report()
            options: Namespace that may alter behaviors

            Returns
            -------
            Updated string based on options
        """
        if options is None:
            return initial_str
        modified_str = initial_str
        if options.show_manager:
            modified_str += f" via '{self.file_target}'"
        return modified_str

    def report(self,
               path: pathlib.Path,
               options: Optional[argparse.Namespace],
               ) -> Generator[str, str, str]:
        """
            Yield one line per metadata field that is set for the given path in mappings.

            Parameters
            ----------
            path: file to report on
            options: Namespace that can alter printing behaviors

            Returns
            -------
            Generator that yields a string per line of the file's report, including errors in processing
        """
        raise NotImplemented

