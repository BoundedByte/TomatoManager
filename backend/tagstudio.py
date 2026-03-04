"""
    (C) BoundedByte 2026

    tagstudio.py: Interactions with TagStudio (non-Python dependency)
        - Read metadata from database
        - Write metadata to database
"""

# Dependent libraries
import pandas as pd # SQLITE3 read, DataFrame type

# Local modules
from .metadata import TomatoManagerTags, TomatoManagerTypes, TomatoManagerDFTypes
from .pdutil import sqlite_db_load, sqlite_db_save, pandas_append_series_to_end_of_frame
from .manager import Manager

# Python3 builtin modules -- no extra install required
import argparse
from io import StringIO
import pathlib
import subprocess
from typing import Callable, Dict, List, Generator, Optional, Tuple, Union

class TagStudioManager(Manager):
    tagstudio_schema = """\
folders: id, path, uuid
entries: folder_id, path, filename, suffix, date_created, date_modified, date_added
text_fields: value, id, type_key, entry_id, position
tags: id, name, shorthand, color_namespace, color_slug, is_category, icon, disambiguation_id
tag_entries: tag_id, entry_id
"""
    def __init__(self,
                 database_target: pathlib.Path = pathlib.Path('.TagStudio/ts_library.sqlite'),
                 ) -> None:
        if database_target.suffix.lower() != ".sqlite":
            raise ValueError(f"SQLITE target must be SQLITE type, got '{database_target.suffix}'")
        super().__init__(database_target)

    def bind_from_disk(self,
                       bind: bool = True,
                       ) -> Optional[Dict[str,pd.DataFrame]]:
        if not self.file_target.exists():
            self.mappings = None
            return
        mappings = sqlite_db_load(self.file_target)
        if bind:
            self.mappings = mappings
        else:
            return mappings

    def bind_to_disk(self,
                     ) -> None:
        sqlite_db_save(self.file_target, self.mappings)

    def lookup_entry_id(self,
                        paths: Union[pathlib.Path, List[pathlib.Path]],
                        ) -> List[Optional[int]]:
        if not isinstance(paths, list):
            paths = [paths]
        # Ensure no string-types are given as inputs
        paths = list(map(pathlib.Path, paths))

        entries = list()
        for path in paths:
            # If folder is recognized, filter entries against a folder
            filter_against = None
            for folder_id, folder in zip(self.mappings['folders']['id'],
                                         self.mappings['folders']['path']):
                if path.is_relative_to(folder):
                    filter_against = folder_id
                    path = path.relative_to(folder)
                    break
            # Set the series to utilize
            if filter_against is None:
                searchable = self.mappings['entries']['path']
                search_index = self.mappings['entries']['id']
            else:
                filter_boolean = (self.mappings['entries']['folder_id'] == filter_against)
                searchable = self.mappings['entries'][filter_boolean]['path']
                search_index = self.mappings['entries'][filter_boolean]['id']
            matches = (searchable == str(path)).tolist()
            if sum(matches) == 0:
                entries.append(None)
            else:
                entries.append(search_index[matches.index(True)])
        return entries

    def lookup_tags(self,
                    entries: List[Optional[int]],
                    ) -> List[Optional[List[str]]]:
        if entries is None:
            return list()
        if not isinstance(entries, list):
            entries = [entries]
        tag_lists = list()
        for entry in entries:
            if entry is None:
                tag_lists.append(None)
                continue
            tag_filter = (self.mappings['tag_entries']['entry_id'] == entry)
            if tag_filter.sum() == 0:
                tag_lists.append(None)
                continue
            tags = list()
            for tag_id in self.mappings['tag_entries'][tag_filter]['tag_id']:
                tags.append(self.mappings['tags'][self.mappings['tags']['id'] == tag_id]['name'].tolist()[0])
            tag_lists.append(tags)
        return tag_lists

    def lookup_text_fields(self,
                           entries: List[Optional[int]],
                           ) -> List[Optional[Dict[str,str]]]:
        if entries is None:
            return list()
        if not isinstance(entries, list):
            entries = [entries]
        text_fields = list()
        for entry in entries:
            if entry is None:
                text_fields.append(None)
                continue
            text_filter = (self.mappings['text_fields']['entry_id'] == entry)
            if text_filter.sum() == 0:
                text_fields.append(None)
                continue
            texts = dict()
            for (idx, matching_entry) in self.mappings['text_fields'][text_filter].iterrows():
                type_key = matching_entry['type_key']
                if type_key not in texts:
                    texts[type_key] = list()
                texts[type_key].append(matching_entry['value'])
            text_fields.append(texts)
        return text_fields

    def to_common(self,
                  ) -> pd.DataFrame:
        """
            Convert TagStudio-SQLITE to flattened DataFrame
        """
        mappings = pd.DataFrame(columns=['SourceFile']+TomatoManagerTags)
        for (_, entry_row) in self.mappings['entries'].iterrows():
            record = pd.Series(index=mappings.columns, dtype=str)
            record['SourceFile'] = entry_row['path']
            # Search for TagStudio->CommonExif mappings
            tags = self.lookup_tags([entry_row['id']])[0]
            if tags is not None:
                record['TagsList'] = ";".join(tags)+";"
                record['Tagged'] = True
            else:
                record['Tagged'] = False
            fields = self.lookup_text_fields([entry_row['id']])[0]
            if fields is not None:
                for field_type, values in fields.items():
                    for value in values:
                        match field_type:
                            case 'AUTHOR' | 'ARTIST':
                                if pd.isna(record['Author']):
                                    record['Author'] = value
                                else:
                                    record['Author'] += f", {value}"
                            case 'URL':
                                record['AttributionURL'] = value
                                record['BaseURL'] = value
                                record['URLUrl'] = value
                            case 'NOTES':
                                record['Notes'] = value
                            #'Caption'
                            #'Description'
                            #'DOI'
                            #'Label'
                            #'Lyrics'
                            #'Metadata{Authority{Identifier,Name},Date,LastEdit{ed,or{Identifier,Name}},ModDate}'
                            #'Transcript'
                            #'TranscriptLink'
            mappings = pandas_append_series_to_end_of_frame(mappings, record)
        return mappings

    def merge(self,
              other_manager: object,
              merge_queue: List[pathlib.Path],
              bind: bool = True,
              ) -> Optional[pd.DataFrame]:
        """
            Same as ExifTool's merge but you have to update all of TagStudio's table schemas correctly,
            including inserting new rows for new tags etc
        """
        updated_mappings = super().merge(other_manager, merge_queue, bind=False)
        if not bind:
            return updated_mappings
        # Updates to TagStudio tables (be careful!)
        other_is_tagstudio = isinstance(other_manager, TagStudioManager)

        # All other data bindings can now done directly to the TagStudio format
        # so they'll persist on future interactions, and ultimately,
        # some call to bind_to_disk() for beyond-program-life persistence
        for (idx, row) in updated_mappings.iterrows():
            entry_id = self.lookup_entry_id(row['SourceFile'])[0]
            for field in TomatoManagerTags:
                if field == 'TagsList':
                    # Get existing tags
                    existing_tags = self.lookup_tags(entry_id)[0]
                    for tag in row['TagsList'].split(';'):
                        if existing_tags is not None and tag in existing_tags:
                            continue

                        # If tag is not in the tags table, insert it at auto-incremented id
                        tag_table = self.mappings['tags']
                        if tag in tag_table['name']:
                            tag_id = tag_table[tag_table['name'] == tag,'id']
                        else:
                            tag_id = max(tag_table['id'])+1
                            if other_is_tagstudio:
                                other_tags = other_manager.mappings['tags']
                                tag_info = other_tags[other_tags['name'] == tag].reset_index(drop=True).loc[0]
                                # But always update the ID
                                tag_info['id'] = tag_id
                            else:
                                # Reasonable defaults -- user can change them later
                                tag_info = pd.Series({'id': tag_id,
                                           'name': tag,
                                           'shorthand': '',
                                           'color_namespace': 'tagstudio-standard',
                                           'color_slug': 'red', # Red for TomatoManager, of course
                                           'is_category': False,
                                           'icon': None,
                                           'diambiguation_id': None,
                                           })
                            self.mappings['tags'] = pandas_append_series_to_end_of_frame(tag_table, tag_info)
                        # Add tag<-->entry pairing
                        tag_entry = pd.Series({'tag_id': tag_id,
                                               'entry_id': entry_id,
                                               })
                        self.mappings['tag_entries'] = pandas_append_series_to_end_of_frame(self.mappings['tag_entries'], tag_entry)
                else: # Text Field
                    existing_texts = self.lookup_text_fields(entry_id)[0]

                    # Set correct field type for TagStudio
                    match field:
                        case 'Author':
                            type_key = 'AUTHOR'
                        case 'AttributionURL' | 'BaseURL' | 'DOI' | 'TranscriptLink' | 'URLUrl':
                            type_key = 'URL'
                        case _: # Default
                            # Not implemented for tracking within TagStudio yet!
                            # TODO: Pass these as NOTES, but have to reverse-parse them on to_common() to get cross-compatibility with ExifTool
                            type_key = 'NOTES'

                    # Determine if it already exists
                    if row[field] in existing_texts[type_key]:
                        continue
                    # TODO: Notes type not implemented yet
                    if type_key == 'NOTES':
                        continue

                    # Add text field
                    text_field_info = pd.Series({'id': max(self.mappings['text_fields']['id'])+1,
                                                 'type_key': type_key,
                                                 'entry_id': entry_id,
                                                 'position': 0 if existing_texts[type_key] is None else len(existing_texts[type_key]),
                                                 })
                    self.mappings['text_fields'] = pandas_append_series_to_end_of_frame(self.mappings['text_fields'], text_field_info)

    def report(self,
               path: pathlib.Path,
               options: Optional[argparse.Namespace],
               ) -> Generator[str,str,str]:
        hit = self.lookup_entry_id(path)[0]
        if hit is None:
            report_field = f"No TAGSTUDIO entry for '{path}'"
            yield self.string_options(report_field, options)
            return
        entry_made = False
        associated_text_fields = self.lookup_text_fields(hit)
        if associated_text_fields is not None:
            for field_dict in associated_text_fields:
                if field_dict is not None:
                    for field, values in field_dict.items():
                        entry_made = True
                        for value in values:
                            report_field = f"TAGSTUDIO {field}:"+" "*(11-len(field))+f"{value}"
                            yield self.string_options(report_field, options)
        associated_tags = self.lookup_tags(hit)
        if associated_tags is not None:
            for tag_list in associated_tags:
                if tag_list is not None:
                    entry_made = True
                    report_field = f"TAGSTUDIO TAGS:       {';'.join(tag_list)+';'}"
                    yield self.string_options(report_field, options)
        if not entry_made:
            report_field = f"No relevant TAGSTUDIO metadata for '{path}'"
            yield self.string_options(report_field, options)

