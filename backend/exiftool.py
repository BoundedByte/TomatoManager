"""
    (C) BoundedByte 2026

    exiftool.py: Interactions with ExifTool (non-Python dependency)
        - Read metadata from file
        - Write metadata to file
"""

# Dependent libraries
import pandas as pd # CSV read, DataFrame type

# Local modules
from .metadata import TomatoManagerTags, TomatoManagerTypes
from .manager import Manager

# Python3 builtin modules -- no extra install required
import argparse
from io import StringIO
import pathlib
import subprocess
from typing import Callable, Dict, List, Generator, Optional, Tuple, Union

class ExifToolManager(Manager):
    def __init__(self,
                 csv_target: pathlib.Path = pathlib.Path('exiftool.csv'),
                 exiftool_path: pathlib.Path = pathlib.Path('exiftool'),
                 ) -> None:
        if csv_target.suffix.lower() != ".csv":
            raise ValueError(f"CSV target must be CSV type, got '{csv_target.suffix}'")
        super().__init__(csv_target)
        self.exiftool_path = exiftool_path

    def bind_from_disk(self,
                       bind: bool = True,
                       ) -> Optional[pd.DataFrame]:
        if not self.file_target.exists():
            self.mappings = None
            return
        mappings = pd.read_csv(self.file_target)
        if bind:
            self.mappings = mappings
        else:
            return mappings

    def bind_to_disk(self,
                     ) -> None:
        self.mappings.to_csv(self.file_target, index=False)

    def read_mappings_from_files(self,
                                 disk_paths: Optional[Union[pathlib.Path,
                                                            List[pathlib.Path]]],
                                 bind: bool = False,
                                 ) -> Optional[pd.DataFrame]:
        mappings = pd.DataFrame(columns=['SourceFile']+TomatoManagerTags)
        if disk_paths is not None:
            if not isinstance(disk_paths, list):
                disk_paths = [disk_paths]

            # Batch-call ExifTool on all paths
            cmd = [self.exiftool_path, '-r']
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
        else:
            return mappings

    def apply_mappings_to_files(self,
                                disk_paths: Optional[Union[pathlib.Path,
                                                           List[pathlib.Path]]],
                                allow_overwrite: bool = False,
                                ) -> None:
        if disk_paths is None:
            return
        if not isinstance(disk_paths, list):
            disk_paths = [disk_paths]

        # Batch-call ExifTool on all paths
        cmd = [self.exiftool_path, f'-csv={self.csv_target}']
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
            report_field = f"EXIFTOOL {tag}:"+" "*(12-len(tag))+f"{value}"
            yield self.string_options(report_field, options)
        if not entry_made:
            report_field = f"No relevant EXIFTOOL metadata for '{path}'"
            yield self.string_options(report_field, options)

