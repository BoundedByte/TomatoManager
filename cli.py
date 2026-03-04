"""
    (C) BoundedByte 2026

    cli.py: Command Line Interface for TomatoManager
        - Read/Write ExifTool CSVs and File Metadata
        - Read/Write TagStudio Databases
        - Merge Exif - Exif, Exif - TagStudio, and TagStudio - TagStudio data
        - Search database
"""

# Local modules
from backend.filetypes import Supported, Questionable, Unsupported
from backend.exiftool import ExifToolManager
from backend.tagstudio import TagStudioManager
from backend.metadata import TomatoManagerTags

# Python3 builtin modules -- no extra install required
import argparse
import pathlib
from typing import Callable, Dict, List, Optional, Tuple, Union

def attribute_file(path: pathlib.Path,
                   managers: Optional[List[Union[ExifToolManager,TagStudioManager]]] = None,
                   options: Optional[argparse.Namespace] = None,
                   ) -> bool:
    # Given a file, retrieve all mapped metadata from all available managers
    if managers is None:
        managers = list()
    needs_merge = False

    print(path)
    longest_line = len(str(path))

    for (midx, manager) in enumerate(managers):
        for metadata_line in manager.report(path, options):
            print(metadata_line)
            longest_line = max(longest_line, len(metadata_line))
        if (not needs_merge and midx > 0) and not manager.compare(path, managers[0]):
            needs_merge = True
        # Also need merge if a tag write is necessary
        if not needs_merge:
            for tag in options.write_tag:
                for manager in managers:
                    if manager.plan_write(path, tag):
                        needs_merge = True
                        break
                if needs_merge:
                    break
    print('-' * longest_line)
    return needs_merge

def diriterate(query: pathlib.Path,
               managers: Optional[List[Union[ExifToolManager,TagStudioManager]]],
               to_merge: List[pathlib.Path],
               options: Optional[argparse.Namespace],
               ) -> List[pathlib.Path]:
    # Recurse over query to attribute all files and accumulate merge targets
    if query.is_dir():
        for subquery in query.iterdir():
            to_merge = diriterate(subquery, managers, to_merge, options)
        return to_merge
    # Pre-determine if file is usable
    filetype = query.suffix.lower()[1:]
    if filetype in Unsupported:
        print(f"! FileType '{filetype}' is NOT supported -- file: {query}")
        return to_merge
    if filetype in Questionable:
        print(f"? FileType '{filetype}' is not known to be properly supported -- file: {query}")
        print("\t"+"Please report your experience upstream to aid in properly classifying it")
    elif filetype not in Supported:
        print(f"! FileType '{filetype}' is UNKNOWN -- file: {query}")
        print("\t"+"Please make an issue if you would like official support")
        return to_merge

    needs_merge = attribute_file(query, managers, options)
    if needs_merge:
        to_merge.append(query)
    return to_merge

def build(
          ) -> argparse.ArgumentParser:
    prs = argparse.ArgumentParser()
    # ExifTool Namespace
    prs.add_argument('--exiftool-path',
                     type=pathlib.Path,
                     default='exiftool',
                     help="Path to ExifTool binary (Default: %(default)s)",
                     )
    prs.add_argument('--allow-exiftool-overwrite-in-place',
                     action='store_true',
                     help="Allow ExifTool to update files without preserving original file (Default: %(default)s)",
                     )
    # Should always be CLI top-level namespace
    prs.add_argument('--data-sources',
                     type=pathlib.Path,
                     nargs="*",
                     default=None,
                     help="Data sources to describe known metadata (CSV and TagStudio-SQLITE supported)",
                     )
    prs.add_argument('--merge-source',
                     type=pathlib.Path,
                     default=None,
                     help="Data source to merge TO all other data sources",
                     )
    prs.add_argument('--write-tag',
                     type=str,
                     nargs="*",
                     default=None,
                     help="<Key>:<Value> tags to write to ALL files",
                     )
    prs.add_argument('--search',
                     type=str,
                     nargs="*",
                     default=None,
                     help="Search for substring matches over query files (can prefix '<tag>:<search>' for narrow focus) -- multiple search terms will be INTERSECTED")
    prs.add_argument('--show-manager',
                     action='store_true',
                     help="Show information regarding which manager assisted in report outputs (Default: %(default)s)",
                     )
    prs.add_argument('query_files',
                     type=pathlib.Path,
                     nargs="*",
                     default=None,
                     help="Files to look up in data sources and on-disk (recurses through directories)",
                     )
    return prs

def parse(args: argparse.Namespace = None,
          prs: argparse.ArgumentParser = None,
          ) -> argparse.Namespace:
    if prs is None:
        prs = build()
    if args is None:
        args = prs.parse_args()
    # Validation
    # Only CSV and TagStudio-schema SQLITE can be supported as data sources
    all_ok = True
    if args.search is None:
        args.search = list()
    if args.write_tag is None:
        args.write_tag = list()
    for tag in args.write_tag:
        if ':' not in tag:
            raise ValueError(f"Cannot write tag '{tag}' -- improperly formatted! <key>:<value>")
        key, value = tag.split(':',1)
        if key not in TomatoManagerTags:
            raise ValueError(f"Cannot write tag '{key}' -- not a TomatoManager-controlled tag")
    if args.data_sources is None:
        args.data_sources = list()
    if args.merge_source is not None and args.merge_source not in args.data_sources:
        args.data_sources.append(args.merge_source)
    for datasource in args.data_sources:
        if datasource.suffix.lower() not in ['.csv','.sqlite']:
            all_ok = False
            print(f"! Data sources must be CSV or TagStudio-SQLITE -- exception: {datasource}")
    if not all_ok:
        exit(1)

    return args

def main(args: argparse.Namespace,
         ) -> None:
    # Load all data sources
    managers = list()
    for datasource in args.data_sources:
        filetype = datasource.suffix.lower()
        if filetype == '.csv':
            managers.append(ExifToolManager(datasource))
        elif filetype == '.sqlite':
            managers.append(TagStudioManager(datasource))

    # Search
    if len(args.search) > 0:
        matches = None
        for search_term in args.search:
            key = None
            if ":" in search_term:
                key, search_term = search_term.split(':',1)
            term_matches = set()
            for manager in managers:
                manager_matches = manager.search(key, search_term)
                term_matches = term_matches.union(manager_matches)
            if len(term_matches) > 0:
                if matches is None:
                    matches = term_matches
                else:
                    matches = matches.intersection(term_matches)
        if matches is None:
            print(f"No matches for search")
        else:
            print(f"Search produced {len(matches)} matches:")
            for match in matches:
                attribute_file(match, managers, args)
        exit(0)

    # Recursive iteration across files and managers
    merge_queue = list()
    for query in args.query_files:
        merge_queue = diriterate(query, managers, merge_queue, args)

    # Perform all merges
    if len(merge_queue) > 0:
        print(f"Metadata requires merge in {len(merge_queue)} files")
        print('\t* '+'\n\t* '.join([str(_) for _ in merge_queue]))
        if args.merge_source is None:
            print(f"Supply --merge-source to assign source of truth that overrides others")
            exit(0)
        merge_manager_idx = args.data_sources.index(args.merge_source)
        merger = managers[merge_manager_idx]
        for manager_idx, manager in enumerate(managers):
            if manager_idx == merge_manager_idx:
                continue
            before = manager.to_common()
            manager.merge(merger, merge_queue, bind=True)
            update = manager.to_common()
            print(f"BEFORE:")
            print(before[before['SourceFile'].isin(map(str,merge_queue))])
            print(f"TODO: save manager {args.data_sources[manager_idx]} with updates here:")
            print(update[update['SourceFile'].isin(map(str,merge_queue))])
    else:
        print(f"All metadata up-to-date and merged between all managers :)")

if __name__ == '__main__':
    main(parse())

