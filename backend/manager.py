"""
    (C) BoundedByte 2026

    manager.py: SuperClass for Metadata managers
"""

# Dependent libraries
import pandas as pd

# Local libraries
from .metadata import TomatoManagerTags

# Python3 builtin modules -- no extra install required
import argparse
import pathlib
from typing import Callable, Dict, List, Generator, Optional, Tuple, Union

class Manager():
    def __init__(self,
                 file_target: pathlib.Path,
                 ) -> None:
        self.file_target = file_target
        self.bind_from_disk()

    def bind_from_disk(self,
                       bind: bool = True,
                       ) -> Optional[pd.DataFrame]:
        """
            If self.file_target does not exist, set self.mappings = None and
            return None regardless of bind setting
            ```
            if not self.file_target.exists():
                self.mappings = None
                return
            ```

            Should bind DataFrame to self.mappings IFF bind == True,
            else return the DataFrame after setting self.mappings = None
            ```
            mappings = # Some way to load from self.file_target
            if bind:
                self.mappings = mappings
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

    def intersect(self,
                  other_manager: object,
                  limit_paths: Optional[List[pathlib.Path]] = None,
                  ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
            Make a common intersection pair of DataFrames for given manager and self
        """
        if limit_paths is not None and not isinstance(limit_paths, list):
            limit_paths = [limit_paths]

        own = self.to_common()
        other = other_manager.to_common()
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
            Find path in own mappings and foreign mappings, return True IFF all
            tags are symmetric
        """
        own, other = self.intersect(other_manager, path)
        return own.reset_index(drop=True).equals(other.reset_index(drop=True))

    def search(self,
               key: Optional[str],
               value: str,
               ) -> List[pathlib.Path]:
        df = self.to_common().infer_objects()
        if key is not None:
            df = df[['SourceFile',key]]
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
        return set(df.loc[dfs[dfs > 0].index, 'SourceFile'].tolist())

    def plan_write(self,
                   path: pathlib.Path,
                   tag: str,
                   ) -> bool:
        """
            Return True IFF tag would change metadata representation in manager
        """
        try:
            field, value = tag.split(':',1)
        except:
            raise ValueError(f"Improperly formatted tag! Should be <key>:<value>")
        common = self.to_common()
        current = common[common['SourceFile'] == str(path)]
        return current[field].tolist()[0] != value

    def merge(self,
              other_manager: object,
              merge_queue: List[pathlib.Path],
              bind: bool = True,
              ) -> Optional[pd.DataFrame]:
        """
            Other manager is authoritative on differences!
        """
        bindable = self.to_common().copy()
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
        else:
            return bindable[bindable['SourceFile'].isin(map(str,merge_queue))]

    def string_options(self,
                       initial_str: str,
                       options: Optional[argparse.Namespace],
                       ) -> str:
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
            Yield one line per metadata field that is set for the given path
            in mappings.

            Errors in processing should ALSO be yielded as strings
        """
        raise NotImplemented

