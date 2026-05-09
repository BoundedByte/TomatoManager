"""
    (C) BoundedByte 2026

    exiftool.py: Interactions with ExifTool (non-Python dependency)
        - Read metadata from file
        - Write metadata to file
"""

# Dependent libraries
import pandas as pd # CSV read, DataFrame type

# Local modules
from .metadata import TomatoManagerTags, TagSpacing
from .manager import Manager

# Python3 builtin modules -- no extra install required
import argparse
from io import StringIO
import pathlib
import subprocess
from typing import List, Generator, Optional, Union

class ExifToolManager(Manager):
    """
        Manager for CSV data in ExifTool format ('SourceFile' column + TomatoManagerTags)
    """
    def __init__(self,
                 csv_target: pathlib.Path = pathlib.Path('exiftool.csv'),
                 exiftool_path: pathlib.Path = pathlib.Path('exiftool'),
                 ) -> None:
        """
            Enforce CSV path expectation and store exiftool path for use when calling out to exiftool dependency
        """
        if csv_target.suffix.lower() != ".csv":
            raise ValueError(f"CSV target must be CSV type, got '{csv_target.suffix}'")
        super().__init__(csv_target)
        self.exiftool_path = exiftool_path

    def bind_from_disk(self,
                       bind: bool = True,
                       ) -> Optional[pd.DataFrame]:
        """
            Use pandas to read CSV for simple DataFrame
        """
        if not self.file_target.exists():
            self.mappings = None
            self.cache = None
            return
        mappings = pd.read_csv(self.file_target)
        if bind:
            self.mappings = mappings
            self.cache = None
        else:
            return mappings

    def bind_to_disk(self,
                     ) -> None:
        """
            Pandas DataFrame provides CSV writing capabilities
        """
        self.mappings.to_csv(self.file_target, index=False)

    def read_mappings_from_files(self,
                                 disk_paths: Optional[Union[pathlib.Path,
                                                            List[pathlib.Path]]],
                                 bind: bool = False,
                                 ) -> Optional[pd.DataFrame]:
        """
            Directly read file metadata from disk for given paths, optionally updating bound representation

            Parameters
            ----------
            disk_paths: Files to read
            bind: Overwrite self.mappings if true, else return the interpreted DataFrame

            Returns
            -------
            DataFrame of data from disk if bind=False, else None but overwrites self.mappings with the same data
        """
        mappings = pd.DataFrame(columns=['SourceFile']+TomatoManagerTags)
        if disk_paths is not None:
            if not isinstance(disk_paths, list):
                disk_paths = [disk_paths]

            # Batch-call ExifTool on all paths
            cmd = [self.exiftool_path, '-csv', '-r']
            cmd += [f'-{tag}' for tag in TomatoManagerTags]
            cmd += disk_paths

            print(" ".join([str(_) for _ in cmd]))
            proc = subprocess.run(cmd, capture_output=True)
            if proc.returncode != 0:
                raise ValueError(f"ExifTool return code: {proc.returncode}")
            output = proc.stdout.decode('utf-8')
            mappings = pd.read_csv(StringIO(output))
        if bind:
            self.mappings = mappings
            self.cache = None
        else:
            return mappings

    def apply_mappings_to_files(self,
                                disk_paths: Optional[Union[pathlib.Path,
                                                           List[pathlib.Path]]],
                                allow_overwrite: bool = False,
                                ) -> None:
        """
            Use ExifTool to write metadata from self.file_target to metadata of files

            Parameters
            ----------
            disk_paths: Files to update on disk
            allow_overwrite: Instruct ExifTool to overwrite in place rather than leaving the '_original' file behind
        """
        if disk_paths is None:
            return
        if not isinstance(disk_paths, list):
            disk_paths = [disk_paths]

        # Batch-call ExifTool on all paths
        cmd = [self.exiftool_path, f'-csv={self.file_target}']
        cmd += [f'-{tag}' for tag in TomatoManagerTags]
        if allow_overwrite:
            cmd += ['-overwrite_original_in_place']
        cmd += disk_paths

        print(" ".join([str(_) for _ in cmd]))
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            raise ValueError(f"ExifTool return code: {proc.returncode}")

    def report(self,
               path: pathlib.Path,
               options: Optional[argparse.Namespace],
               ) -> Generator[str,str,str]:
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
        try:
            rowidx = (self.mappings['SourceFile'] == str(path)).tolist().index(True)
        except:
            report_field = f"No relevant EXIF metadata for '{path}'"
            yield self.string_options(report_field, options)
            return
        entry_made = False
        for tag in TomatoManagerTags:
            try:
                value = self.mappings.loc[rowidx,tag]
            except KeyError:
                continue
            if pd.isna(value):
                continue
            entry_made = True
            report_field = f"EXIFTOOL {tag+':':<{TagSpacing}}{value}"
            yield self.string_options(report_field, options)
        if not entry_made:
            report_field = f"No relevant EXIFTOOL metadata for '{path}'"
            yield self.string_options(report_field, options)

