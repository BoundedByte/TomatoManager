#!/usr/bin/env python3
"""
    (C) BoundedByte 2026

    cli.py: Command Line Interface for TomatoManager
        - Read/Write supported databases via Managers
        - Merge databases
        - Search databases
"""

# Local modules
from backend.filetypes import Supported, Questionable, Unsupported
from backend.metadata import TomatoManagerTags
from backend.manager import Manager
from backend.exiftool import ExifToolManager
from backend.tagstudio import TagStudioManager
from backend.local import LocalManager

# Python3 builtin modules -- no extra install required
import argparse
import pathlib
from typing import List, Optional, Tuple, Union
import pprint

# Dependent modules
import pandas as pd

def attribute_file(path: pathlib.Path,
                   managers: Optional[List[Manager]] = None,
                   options: Optional[argparse.Namespace] = None,
                   ) -> bool:
    """
        Retrieve all mapped metadata for a given file from all available managers

        Parameters
        ----------
        path: file to be attributed
        managers: data-managing objects with metadata to report
        options: command-line arguments passed along to other function calls

        Returns
        -------
        Whether or not a merge is needed for all command line options and
        managers to reflect the same data
    """
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
        if not needs_merge and options is not None:
            for tag in options.write_tag:
                for manager in managers:
                    if manager.plan_write(path, tag):
                        needs_merge = True
                        break
                if needs_merge:
                    break
    print('-' * longest_line)
    return needs_merge

def diriterate(query: Union[str,pathlib.Path],
               managers: Optional[List[Manager]],
               to_merge: List[pathlib.Path],
               options: Optional[argparse.Namespace],
               ) -> List[pathlib.Path]:
    """
        Recurse over query path to attribute all files and accumulate merge targets

        Parameters
        ----------
        query: path to recurse upon
        managers: data-managing objects with metadata to report
        to_merge: current list of merge targets
        options: command-line arguments passed along to other function calls

        Returns
        -------
        Updated list of merge targets
    """
    if isinstance(query, str):
        query = pathlib.Path(query)
    if query.is_dir():
        for subquery in query.iterdir():
            to_merge = diriterate(subquery, managers, to_merge, options)
        return to_merge

    # Determine if file is usable
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
    """
        Creates ArgParse CLI. Use `python3 cli.py --help` to see the usage information
    """
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
    prs.add_argument('--local-data-source',
                     type=pathlib.Path,
                     nargs="*",
                     default=None,
                     help="Files to read metadata from that are not currently integrated into a supported library",
                     )
    prs.add_argument('--merge-source',
                     type=pathlib.Path,
                     default=None,
                     help="Data source to merge TO all other data sources",
                     )
    prs.add_argument('--yes-merge',
                     action='store_true',
                     help="Auto-accept all changes made for merges (Default: %(default)s)",
                     )
    prs.add_argument('--write-tag',
                     type=str,
                     nargs="*",
                     default=None,
                     help="<Key>:<Value> tags to write to ALL files",
                     )
    prs.add_argument('--dump-all',
                     action='store_true',
                     help="Display all data from all managers (Default: %(default)s)",
                     )
    prs.add_argument('--search',
                     type=str,
                     nargs="*",
                     default=None,
                     help="Search for substring matches over query files (can prefix '<tag>:<search>' for narrow focus); multiple search terms will be INTERSECTED")
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

def parse(args: Optional[argparse.Namespace] = None,
          prs: Optional[argparse.ArgumentParser] = None,
          ) -> Tuple[argparse.Namespace, Optional[List[str]]]:
    """
        Reasonably verify arguments and prepare expected data. Exit with failure code if parsing fails.

        Parameters
        ----------
        args: arguments to override reading from sys.args
        prs: ArgumentParser to override typical CLI

        Suggestion for Extensibility
        ----------------------------
        To leave this CLI intact but reuse/extend it in another script, consider:
        ```
        from cli import build, parse
        args, unknown = parse()
        my_prs = argparse.ArgumentParser()
        my_prs.add_argument('--my-arg', ...)
        ...
        my_prs.parse_args(unknown, namespace=args)
        # Validate your new arguments here
        # ie: if args.my_arg == 'XYZ': ...
        ```

        Returns
        -------
        args: Parsed command line arguments as a Namespace
        unknown: List of unrecognized command line arguments
    """
    if prs is None:
        prs = build()
    if args is None:
        args, unknown = prs.parse_known_args()

    # If this flag is flipped, parsing failed -- but attempt to find as many errors as possible before giving up
    all_ok = True
    if args.search is None:
        args.search = list()
    if args.write_tag is None:
        args.write_tag = list()
    for tag in args.write_tag:
        if ':' not in tag:
            print(f"! Cannot write tag '{tag}' -- improperly formatted! <key>:<value>")
            all_ok = False
            continue
        key, value = tag.split(':',1)
        if key not in TomatoManagerTags:
            print(f"! Cannot write tag '{key}' -- not a TomatoManager-controlled tag")
            all_ok = False
    if args.data_sources is None:
        args.data_sources = list()
    if args.local_data_source is None:
        args.local_data_source = list()
    if args.merge_source is not None and args.merge_source not in args.data_sources:
        args.data_sources.append(args.merge_source)
    # Only CSV and TagStudio-schema SQLITE can be supported as data sources
    for datasource in args.data_sources:
        if datasource.suffix.lower() not in ['.csv','.sqlite']:
            all_ok = False
            print(f"! Data sources must be CSV or TagStudio-SQLITE -- exception: {datasource}")
    if not all_ok:
        print(f"! CLI parse failed")
        exit(1)

    return args, unknown

def make_merge_view(before: pd.DataFrame,
                    update: pd.DataFrame,
                    merge_queue: List[str],
                    ) -> Tuple[dict, int]:
    bdict = before[before['SourceFile'].isin(map(str,merge_queue))].to_dict()
    udict = update[update['SourceFile'].isin(map(str,merge_queue))].to_dict()
    ddict = udict.copy()
    # Drop non-changes from diff, drop DELETION of data due to a merge
    skipped_deletions = 0
    for (k,v) in udict.items():
        if v == bdict[k]:
            del ddict[k]
            continue
        if all(map(pd.isna,v.values())):
            del ddict[k]
            skipped_deletions += 1
            continue
    # Convert from index to names with before/after for presentation
    final_dict = dict()
    for key in ddict.keys():
        final_dict[key] = dict()
        for idx, value in ddict[key].items():
            bvalue = bdict[key][idx]
            if bvalue != value and (not all(map(pd.isna, [value, bvalue]))):
                final_dict[key][bdict['SourceFile'][idx]] = f"{bvalue} ==> {value}"
    return final_dict, skipped_deletions

def approve(prompt: str) -> bool:
    while True:
        print(prompt)
        usr = input()
        if usr.rstrip().lower() in ['y','ye','yes','yeah','ok','si']:
            return True
        if usr.rstrip().lower() in ['n','no','nope']:
            return False

def main(args: argparse.Namespace,
         unknown: Optional[List[str]],
         ) -> None:
    """
        Main CLI for TomatoManager.

        Runs search queries (if searching via --search) and exits.
        Runs merges (if merging via --merge-source) and exits.
        Otherwise can be used to query data sources (all files or subset thereof).

        Does not handle unknown arguments, but does not return them either
    """

    # Load all data sources
    managers = list()
    if len(args.local_data_source) > 0:
        managers.append(LocalManager(args.local_data_source, args.exiftool_path))
    for datasource in args.data_sources:
        # TODO: Manager subclasses should be determined via a helper function for best extensibility
        filetype = datasource.suffix.lower()
        match filetype:
            case '.csv':
                managers.append(ExifToolManager(datasource, args.exiftool_path))
            case '.sqlite':
                managers.append(TagStudioManager(datasource))
            case _:
                raise NotImplemented(f"No data manager for filetype '{filetype}'")

    # Dump
    if args.dump_all:
        for manager in managers:
            managed_files = manager.cached_common()['SourceFile']
            for file in managed_files:
                print(f"{file} managed by {manager}")
                for metadata_line in manager.report(file, args):
                    print(metadata_line)
                print()

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
    if len(args.query_files) > 0:
        for query in args.query_files:
            merge_queue = diriterate(query, managers, merge_queue, args)
    else:
        file_set = set()
        for manager in managers:
            file_set = file_set.union(set(manager.cached_common()['SourceFile'].to_list()))
        for query in file_set:
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
            original_manager_bindings = manager.mappings.copy()
            common_before = manager.cached_common()

            updated_manager_bindings = manager.merge(merger, merge_queue, bind=False)
            
            manager.mappings = updated_manager_bindings
            # Explicitly invalidate cache, but we save both to avoid recomputing either
            manager.cache = None
            common_update = manager.to_common()
            
            # Restore the bindings/cache that are used (default: pre-merge until merge approved)
            manager.mappings = original_manager_bindings
            manager.cache = common_before
            ddict, skipped_deletions = make_merge_view(common_before, common_update, merge_queue)
            if skipped_deletions > 0:
                print(f"Skipped {skipped_deletions} keys that would delete data without replacing it")
            if len(ddict.keys()) == 0:
                print(f"No merge to perform")
            else:
                pprint.pprint(ddict)
                # TODO: TagStudio does not elegantly support the ideal of not deleting data because
                # its structure is so disparately indexed. It should mostly be fine, but warn the user
                ts_disclaimer = "" if not isinstance(manager, TagStudioManager) \
                                else f"WARNING: TagStudio MAY delete data that is unset via merge authority -- to be fixed in future release. You may want to save a backup of your current TagStudio library '{manager.file_target}' before accepting. "
                if args.yes_merge or approve(f"Save changes to {manager.file_target}? {ts_disclaimer}Y/n: "):
                    # ONLY hit approved and applicable indices!
                    manager.mappings = common_before
                    manager.cache = common_update
                    if isinstance(manager, TagStudioManager):
                        # Clobbers here
                        manager.mappings = updated_manager_bindings
                    else:
                        # Elegant / safer here
                        update_index = updated_manager_bindings.index
                        manager.mappings.loc[update_index] = updated_manager_bindings
                        manager.cache.loc[update_index] = updated_manager_bindings
                    manager.bind_to_disk()
                    print(f"Commited merges to manager for {manager.file_target}")
    else:
        print(f"All metadata up-to-date and merged between all managers :)")

if __name__ == '__main__':
    main(*parse())

