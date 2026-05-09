# ExifTool x TomatoManager

**NOTE**: TomatoManager is an **INDEPENDENT** project and cannot fix issues with ExifTool.

Please **DO NOT** make requests regarding TomatoManager features or compatibility from ExifTool maintainers.
Please **DO** share your appreciation and open-source contributions with them as you are able!

---

[ExifTool](https://exiftool.org) is FOSS that permits reading and writing metadata from _many_ media formats.

For details about the program, installation instructions, and latest releases, please refer to their website.
Details in this document are up-to-date as of the [13.50 Version](https://sourceforge.net/projects/exiftool/files/).

## Interoperability with TomatoManager

ExifTool is a fantastic tool for reading and writing metadata on its own.
However, it does not have means to translate metadata for use with other programs (like TagStudio) and requires more manual interventions to merge databases together.

TomatoManager operates as a wrapper for ExifTool that prioritizes XMP tags for maximum compatibility across the most common media formats.
The specific tags are detailed in [metadata.py](../backend/metadata.py)

### Directly using ExifTool yourself

Generally, you can (over)write any of TomatoMangaer's tracked tags using the following ExifTool call: `exiftool -<TAG>=<VALUE> -- <FILES>`.

## Exporting Your ExifTool Library

TomatoManager knows how to read the CSV export format from ExifTool, but needs the CSV to match the list of supported tags.
For your convenience, you can use [exiftool\_export.sh](../exiftool_export.sh) to create an appropriate CSV named "exiftool.csv": `./exiftool_export.sh <FILES TO EXPORT>`
If the current working directory has a ".TagStudio" folder, the script will place the CSV in that folder, otherwise the CSV will be placed in the current working directory.

## Importing Another Library (Merge)

TomatoManager can merge data from another library with your metadata.
In the current version, merges are authoritative, meaning _all_ foreign data will overwrite your previously saved data!

A future release will allow you to navigate merges with more nuance, but you can limit the scope by specifying specific files you want merged from the foreign data:

`python3 cli.py --data-sources <YOUR_LIBRARY> --merge <OTHER_LIBRARY> -- <SPECIFIC FILES TO OVERRIDE>`

