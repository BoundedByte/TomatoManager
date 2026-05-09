"""
    (C) BoundedByte 2026

    local.py: Interactions with ExifTool (non-Python dependency) to support reading data in files
        - Read metadata from file
        - Write metadata to file
"""

# Dependent libraries
import pandas as pd # CSV read, DataFrame type

# Local modules
from .metadata import TomatoManagerTags, TagSpacing
from .manager import Manager
from .pdutil import pandas_append_series_to_end_of_frame

# Python3 builtin modules -- no extra install required
import argparse
from io import StringIO
import pathlib
import subprocess
from typing import List, Generator, Optional, Union

class LocalManager(Manager):
    """
        Manager for metadata resident in files via ExifTool
    """
    def __init__(self,
                 targets: Optional[List[pathlib.Path]] = None,
                 exiftool_path: pathlib.Path = pathlib.Path('exiftool'),
                 ) -> None:
        """
            Store exiftool path for use when calling out to exiftool dependency
            Load any local files indicated at initialization time
        """
        accepted_targets = list()
        if targets is not None:
            while len(targets) > 0:
                t = targets.pop()
                if not t.is_dir():
                    accepted_targets.append(t)
                else:
                    targets.extend(t.iterdir())
        if len(accepted_targets) == 0:
            raise ValueError("No files to index")
        self.targets = accepted_targets
        self.exiftool_path = exiftool_path
        super().__init__("<LOCAL TO FILES>")

    def bind_from_disk(self,
                       bind: bool = True,
                       ) -> Optional[pd.DataFrame]:
        """
            Use ExifTool to read from disk
        """
        return self.read_mappings_from_files(self.targets, bind=bind)

    def bind_to_disk(self,
                     ) -> None:
        """
           Use ExifTool to write back to files
        """
        temporary_csv = pathlib.Path('tmp.csv')
        suffix = 0
        while temporary_csv.exists():
            temporary_csv = temporary_csv.with_stem(f'tmp_{suffix}')
            suffix += 1
        self.mappings.to_csv(temporary_csv, index=False)
        old_file_target = self.file_target
        self.file_target = temporary_csv
        self.apply_mappings_to_files(self.targets, allow_overwrite=True)
        temporary_csv.unlink()
        self.file_target = old_file_target

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
            cmd = [self.exiftool_path, '-r']
            cmd += [f'-{tag}' for tag in TomatoManagerTags]
            cmd += disk_paths

            print(" ".join([str(_) for _ in cmd]))
            proc = subprocess.run(cmd, capture_output=True)
            if proc.returncode != 0:
                raise ValueError(f"ExifTool return code: {proc.returncode}")
            output = proc.stdout.decode('utf-8')
            # Parse EXIFTOOL output
            current_media = None
            row = pd.Series(index=['SourceFile']+TomatoManagerTags, dtype=object)
            for line in output.split('\n'):
                if len(line) == 0 or line.endswith('files read'):
                    continue
                if line.startswith('========'):
                    if current_media is not None:
                        mappings = pandas_append_series_to_end_of_frame(mappings, row)
                        row = pd.Series(index=['SourceFile']+TomatoManagerTags, dtype=object)
                    current_media = line.split(' ',1)[1]
                    row['SourceFile'] = current_media
                else:
                    field, value = line.split(':',1)
                    # ExifTool pretty-prints the field names, strip out spaces etc
                    field = field.rstrip().replace(' ','')
                    value = value.lstrip()
                    row[field] = value
            # Single-file reads imply name at the end
            if current_media is None:
                row['SourceFile'] = str(disk_paths[0])
            if sum(row.isna()) < len(row):
                mappings = pandas_append_series_to_end_of_frame(mappings, row)
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
            report_field = f"LOCAL {tag+':':<{TagSpacing}}{value}"
            yield self.string_options(report_field, options)
        if not entry_made:
            report_field = f"No relevant EXIFTOOL metadata for '{path}'"
            yield self.string_options(report_field, options)

