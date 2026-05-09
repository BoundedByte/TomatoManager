"""
    (C) BoundedByte 2026

    tagstudio.py: Interactions with TagStudio (non-Python dependency)
        - Read metadata from database
        - Write metadata to database
"""

# Dependent libraries
import pandas as pd # SQLITE3 read, DataFrame type

# Local modules
from .metadata import TomatoManagerTags, TagSpacing
from .pdutil import sqlite_db_load, sqlite_db_save, pandas_append_series_to_end_of_frame
from .manager import Manager

# Python3 builtin modules -- no extra install required
import argparse
import datetime
import pathlib
import uuid
from typing import Dict, List, Generator, Optional, Union

class TagStudioManager(Manager):
    """
        Manager for SQLITE data in TagStudio format (Schema denoted in self.tagstudio_schema)
    """
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
        """
            Enforce SQLITE path expectation -- bind_from_disk() will catch incorrect schema
        """
        if database_target.suffix.lower() != ".sqlite":
            raise ValueError(f"SQLITE target must be SQLITE type, got '{database_target.suffix}'")
        super().__init__(database_target)

    def bind_from_disk(self,
                       bind: bool = True,
                       ) -> Optional[Dict[str,pd.DataFrame]]:
        """
            Use sqlite_db_load pandas utilities to create TagStudio dictionary of DataFrames
        """
        if not self.file_target.exists():
            self.mappings = None
            self.cache = None
            return
        mappings = sqlite_db_load(self.file_target)
        if bind:
            self.mappings = mappings
            self.cache = None
        else:
            return mappings

    def bind_to_disk(self,
                     ) -> None:
        """
            Use sqlite_db_save pandas utilities to update TagStudio database on disk
        """
        sqlite_db_save(self.file_target, self.mappings)

    def lookup_entry_id(self,
                        paths: Union[pathlib.Path, List[pathlib.Path]],
                        ) -> List[Optional[int]]:
        """
            TagStudio Schema Helper function: Find given paths' entry_id for foreign key lookups

            Parameters
            ----------
            paths: Paths to retrieve keys for

            Returns
            -------
            List of (integer entry_id keys -or- None if entry is not found)
        """
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
        """
            TagStudio Schema Helper function: Find tags for given entries

            Parameters
            ----------
            entries: IDs to look up and retrieve tags

            Returns
            -------
            List of (list of str tags -or- None if entry is not found)
        """
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
                           ) -> List[Optional[Dict[str,List[str]]]]:
        """
            TagStudio Schema Helper function: Find text fields for given entries

            Parameters
            ----------
            entries: IDs to look up and retrieve tags

            Returns
            -------
            List of (dict of text_type:List[values] -or- None if entry is not found)
        """
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

    def to_tagstudio(self,
                     original_mappings: Dict[str, pd.DataFrame],
                     common_df: pd.DataFrame,
                     ) -> Dict[str, pd.DataFrame]:
        """
            Convert from common format into TagStudio format, defaulting to
            original mappings to ensure no data is lost.
        """
        mappings = dict((k,v) for (k,v) in original_mappings.items())
        # NEVER UPDATED FROM TAGSTUDIO SCHEMA:
        #   tag_aliases
        #   tag_parents
        #   namespaces
        #   value_type
        #   preferences
        #   versions
        #   tag_colors
        #   sqlite_sequence
        # Make updates as necessary
        for _, row in common_df.iterrows():
            # COULD REQUIRE UPDATES:
            # SourceFile -> entries, folders
            file = pathlib.Path(row['SourceFile'])
            # First find/create the folder entry
            found = False
            for folder_idx, folder in enumerate(mappings['folders']['path']):
                if file.is_relative_to(folder):
                    folder_id = mappings['folders']['id'].iloc[folder_idx]
                    found = True
                    break
            if not found:
                folder_id = 1+(0 if len(mappings['folders']) == 0 else max(mappings['folders']['id']))
                folder_uuid = str(uuid.uuid4())
                new_folder = pd.Series({'id': folder_id,
                                        # TODO: This can possibly be upgraded to make fewer folders
                                        # by looking at how TagStudio aggregates them, but for now
                                        # we'll do this
                                        'path': str(file.parents[0]),
                                        'uuid': folder_uuid,
                                        })
                mappings['folders'] = pandas_append_series_to_end_of_frame(mappings['folders'], new_folder)
            # Next find/create the file entry
            filename = str(file.name)
            if (mappings['entries']['filename'] == filename).any():
                file_id = int(mappings['entries'][mappings['entries']['filename'] == filename]['id'].iloc[0])
            else:
                suffix = str(file.suffix)[1:]
                date_created = pd.NaT
                date_modified = pd.NaT
                path = str(file)
                date_added = datetime.datetime.now()
                file_id = int(1+(0 if len(mappings['entries'] == 0) else max(mappings['entries']['id'])))
                new_file = pd.Series({'id': file_id,
                                      'folder_id': folder_id,
                                      'path': path,
                                      'filename': filename,
                                      'suffix': suffix,
                                      'date_created': date_created,
                                      'date_modified': date_modified,
                                      'date_added': date_added,
                                      })
                mappings['entries'] = pandas_append_series_to_end_of_frame(mappings['entries'], new_file)

            # TagsList -> tags, tag_entries
            if not pd.isna(row['TagsList']):
                tags = filter(lambda x: len(x)>0, row['TagsList'].split(';'))
                for tag in tags:
                    if (mappings['tags']['name'] == tag).any():
                        tag_id = mappings['tags'][mappings['tags']['name'] == tag]['id'].iloc[0]
                    else:
                        tag_id = max(1000, max(mappings['tags']['id'])+1)
                        shorthand = ''
                        color_namespace = 'tagstudio-standard'
                        color_slug = 'white'
                        is_category = False
                        icon = None
                        disambiguation_id = None
                        new_tag = pd.Series({'id': tag_id,
                                             'name': tag,
                                             'shorthand': shorthand,
                                             'color_namespace': color_namespace,
                                             'color_slug': color_slug,
                                             'is_category': is_category,
                                             'icon': icon,
                                             'disambiguation_id': disambiguation_id,
                                             })
                        mappings['tags'] = pandas_append_series_to_end_of_frame(mappings['tags'], new_tag)
                    # Once ID set, ensure tag<-->entry is marked as well
                    if ((mappings['tag_entries']['tag_id'] == tag_id) & 
                        (mappings['tag_entries']['entry_id'] == file_id)).sum() != 1:
                        new_tag_entry = pd.Series({'tag_id': tag_id,
                                                   'entry_id': file_id,
                                                   })
                        mappings['tag_entries'] = pandas_append_series_to_end_of_frame(mappings['tag_entries'], new_tag_entry)

            # TODO: Support datetimes
            # Datetime'd object -> datetime_fields
            # MetadataDate, MetadataLastEdited, MetadataModDate
            # value, id, type_key, entry_id, position

            # TODO: Support setting tagged boolean (? TagStudio doesn't require this too much)
            # Tagged -> boolean_fields
            # value, id, type_key, entry_id, position

            # AttributionURL,Author,BaseURL,Caption,Description, etc -> text_fields
            # value, id, type_key{URL, AUTHOR, ARTIST, NOTES, DESCRIPTION, COLLATION, BOOK, COMIC, SERIES, MANGA, SORUCE, VOLUME, ANTHOLOGY, MAGAZINE, PUBLISHER, GUEST_ARTIST, COMPOSER, COMMENTS}, entry_id, position
            text_type = {'AttributionURL': 'URL',
                         'Author': 'AUTHOR',
                         'BaseURL': 'URL',
                         'Caption': 'DESCRIPTION',
                         'Description': 'DESCRIPTION',
                         'DOI': 'NOTES', # Most DOIs are URLs, but not necessarily
                         'Label': 'NOTES',
                         'Lyrics': 'NOTES',
                         'MetadataAuthorityIdentifier': 'NOTES',
                         'MetadataAuthorityName': 'AUTHOR',
                         'MetadataLastEditorIdentifier': 'NOTES',
                         'MetadataLastEditorName': 'AUTHOR',
                         'Notes': 'NOTES',
                         'Transcript': 'NOTES',
                         'TranscriptLink': 'URL',
                         'URLUrl': 'URL',
                         }
            for field, type_key in text_type.items():
                if pd.isna(row[field]):
                    continue
                # Duplication that is unnecessary for TagStudio libraries
                if type_key == 'DESCRIPTION' and row[field] == row['TagsList']:
                    continue
                for value in filter(lambda x: len(x)>0, row[field].split(',')):
                    value = value.lstrip()
                    if type_key != 'AUTHOR':
                        filtered_idx = ((mappings['text_fields']['entry_id'] == file_id) &
                                        (mappings['text_fields']['type_key'] == type_key))
                    else:
                        # Artist TagStudio type is not well supported, need a fix to check against it and not also set the same value as author
                        filtered_idx = ((mappings['text_fields']['entry_id'] == file_id) &
                                        ((mappings['text_fields']['type_key'] == type_key) |
                                         (mappings['text_fields']['type_key'] == 'ARTIST')))
                    if not (mappings['text_fields'][filtered_idx]['value'] == value).any():
                        text_idx = 1+(0 if len(mappings['text_fields']) == 0 else max(mappings['text_fields']['id']))
                        # position is incremented for same entry and same type
                        position = len(mappings['text_fields'][filtered_idx])
                        new_text = pd.Series({'value': value,
                                              'id': text_idx,
                                              'type_key': type_key,
                                              'entry_id': file_id,
                                              'position': position,
                                              })
                        mappings['text_fields'] = pandas_append_series_to_end_of_frame(mappings['text_fields'], new_text)
        return mappings

    def to_common(self,
                  ) -> pd.DataFrame:
        """
            Convert TagStudio's SQLITE schema to flattened DataFrame

            Returns
            -------
            Common format DataFrame with columns ('SourceFile'+TomatoManagerTags)
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
                                    # It has to be done as prepend-order to be most-consistent with ExifTool
                                    record['Author'] = f"{value}, {record['Author']}"
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
            Overwrite own mappings with other_manager matches
            Same as Manager superclass's merge but you have to update all of
            TagStudio's table schemas correctly, including inserting new rows
            for new tags etc

            Parameters
            ----------
            other_manager: Manager with authoritative data that overrides self.mappings
            merge_queue: Paths to update in self.mappings
            bind: Whether to commit to own representation or return updated version

            Returns
            -------
            Updated mappings WITHOUT altering self.mappings if bind=False, otherwise updates in place
        """
        updated_mappings = self.to_tagstudio(self.mappings,
                                             super().merge(other_manager, merge_queue, bind=False))
        if not bind:
            return updated_mappings
        # Invalidate cache
        self.cache = None
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
                    for tag in filter(lambda x: len(x)>0, row['TagsList'].split(';')):
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
                    # TODO: Notes type not implemented yet
                    if type_key == 'NOTES':
                        continue
                    if row[field] in existing_texts[type_key]:
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
                            report_field = f"TAGSTUDIO {field+':':<{TagSpacing}}{value}"
                            yield self.string_options(report_field, options)
        associated_tags = self.lookup_tags(hit)
        if associated_tags is not None:
            for tag_list in associated_tags:
                if tag_list is not None:
                    entry_made = True
                    report_field = f"TAGSTUDIO {'TAGS:':<{TagSpacing}}{';'.join(tag_list)+';'}"
                    yield self.string_options(report_field, options)
        if not entry_made:
            report_field = f"No relevant TAGSTUDIO metadata for '{path}'"
            yield self.string_options(report_field, options)

