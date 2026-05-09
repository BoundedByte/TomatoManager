"""
    (C) BoundedByte 2026

    metadata.py: Tags used by TomatoManager
"""

# Python3 builtin modules -- no extra installation required
import datetime

# Tags in the XMP namespace used across all media
TomatoManagerTags = [
    'AttributionURL',
    'Author',
    'BaseURL',
    'Caption',
    'Description',
    'DOI',
    'Label',
    'Lyrics',
    'MetadataAuthorityIdentifier',
    'MetadataAuthorityName',
    'MetadataDate',
    'MetadataLastEdited',
    'MetadataLastEditorIdentifier',
    'MetadataLastEditorName',
    'MetadataModDate',
    'Notes',
    'Tagged',
    'TagsList',
    'Transcript',
    'TranscriptLink',
    'URLUrl',
]
TagSpacing = max(map(len,TomatoManagerTags))+1

type_and_modifier_help = """\
Types:
    {<field>=<type>[, ...]} is a struct with named fields
    string is a character stream (generally not specific max length)
    string[#] is a known length-capped string with maximum length #
    date is written as YYYY:mm:dd HH:MM:SS[.ss][+/-HH:MM]
    lang-alt indicates a tag has alternative language suffixes
    boolean has literal values 'Yes' and 'No'
Modifiers:
    + indicates a List tag that can be appended to

    / indicates a tag ExifTool will edit, but preferably avoid creating if another same-name tag can be created instead

    ! indicates a tag that is generally unsafe to write to under normal circumstances as they can affect data processing / rendering

    * indicates protected tag which is handled automatically by ExifTool

    : indicates a mandatory tag which may be added automatically when writing
"""
TomatoManagerTypes = {
    'AttributionURL': 'string',
    'Author': 'string',
    'BaseURL': 'string',
    'Caption': 'string/',
    'Description': 'string/',
    'DOI': 'string/',
    'Label': 'string',
    'Lyrics': 'string',
    'MetadataAuthorityIdentifier': 'string_+',
    'MetadataAuthorityName': 'lang-alt_',
    'MetadataDate': 'date',
    'MetadataLastEdited': 'date',
    'MetadataLastEditorIdentifier': 'string_+',
    'MetadataLastEditorName': 'lang-alt_',
    'MetadataModDate': 'date',
    'Notes': 'string/',
    'Tagged': 'boolean/',
    'TagsList': 'string+',
    'Transcript': 'lang-alt',
    'TranscriptLink': '{Link=string,LinkQualifier=string}',
    'URLUrl': 'string/_+',
}

TomatoManagerDFTypes = [str,
                        str,
                        str,
                        str,
                        str,
                        str,
                        str,
                        str,
                        str,
                        str,
                        datetime.datetime,
                        datetime.datetime,
                        str,
                        str,
                        datetime.datetime,
                        str,
                        bool,
                        str,
                        str,
                        str,
                        str,
                        ]

