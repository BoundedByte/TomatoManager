# TagStudio x TomatoManager

**NOTE**: TomatoManager is an **INDEPENDENT** project and cannot fix issues with TagStudio.

Please **DO NOT** make requests regarding TomatoManager features or compatibility from TagStudio maintainers.
Please **DO** share your appreciation and open-source contributions with them as you are able!

---

[TagStudio](https://github.com/TagStudioDev/TagStudio/releases) is FOSS that permits organizing, tagging, annotating and previewing files in a library that roughly corresponds to a directory from your filesystem.

For details about the program, installation instructions, and latest releases, please refer to their repository.
Details in this document are up-to-date as of the [Alpha v9.5.6 Version](https://github.com/TagStudioDev/TagStudio/releases/tag/v9.5.6).

## Interoperability with TomatoManager

TagStudio is a relatively complete solution for tagging and indexing your own data on your own system.
However, it currently has two downsides that TomatoManager can help address:

1) All metadata is tracked in a separate database, meaning it doesn't travel _with_ the files.

2) There are no "social" library capabilities, meaning you need to _manually_ replicate metadata for communal tagging and annotation.

TomatoManager addresses (1) by embedding tags and annotations _within_ the file itself via its metadata, meaning that if you:

* Rename your file
* Move your file
* Share your file via social media

All tags and annotations remain intact and require _no further action on your part_ to remain so.
TagStudio will attempt to trace these changes, but is currently limited in its capabilities to recover from reorganization.
TagStudio also requires you to be the sole author of metadata and tags -- it cannot inherit them from other TagStudio users at this time.

TomatoManager addresses (2) by reading existing metadata (for instance, if you download a file previously tagged via TomatoManager or other metadata tools) and permitting merges when conflicts arise.

* Automatically inherit tags and annotations from other kind souls
* Easily update and upgrade tags as a community effort by pooling efforts together

## Setting Up Your Own TagStudio Library for TomatoManager

TomatoManager knows how to read TagStudio's database of annotations and tags, so use TagStudio normally.
The current version of TomatoManager explicitly supports the following:

* Tags
* Author, Artist, URL, and Note text fields

The current version of TomatoManager _may_ support the following _with caveats_:

* Hierarchical tags (parents, children)
* Other text fields

The current version of TomatoManager is not known to support other TagStudio capabilites.

## Exporting Your TagStudio Library

TomatoManager needs to read TagStudio's SQLite library as a data source.
TagStudio creates this in a hidden folder underneath the main folder you open in TagStudio.

For example, if you use `/home/${USER}/Pictures` as a TagStudio library, the path would be `/home/${USER}/Pictures/.TagStudio/ts_library.sqlite`.
On Windows, this may be similar to `C:\\Users\${User}\Pictures` and `C:\\Users\${User}\Pictures\.TagStudio\ts_library.sqlite`.

`python3 cli.py --data-sources .TagStudio/ts_library.sqlite`

## Importing Another Library (Merge)

TomatoManager can merge data from another library with your metadata.
In the current version, merges are authoritative, meaning _all_ foreign data will overwrite your data!

A future release will allow you to navigate merges with more nuance, but you can limit the scope by specifying specific files you want merged from the foreign data:

`python3 cli.py --data-sources <YOUR_LIBRARY> --merge <OTHER_LIBRARY> -- <SPECIFIC FILES TO OVERRIDE>`

