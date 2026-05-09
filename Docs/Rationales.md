# Why Metadata Editing?

It's good to know who made various media you own and authoritative links to the original source.
Citation is always cool.

It's not-so-good to try and enforce a reliable citation, attribution, and source via the filename.
Nor is it any good to try and search for files based on some name-based sorting mechanism.

## Organizing files using folders/directories can only help so much:

* Some media belongs to multiple "collections" at the same time.
* Symlinks (or shortcuts, in Windows parlance) in different directories can help, but symlinks don't receive first-class support from many common programs (even though they should) and when applied to mass-media collections they outscale maintainability VERY quickly.
* For those who are still on Windows, nesting too many folders with too long of names [_actually breaks the OS_](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation) unless the individual applications you use opt-in to Microsoft's newer APIs to fix it. Gross.

## Metadata persists when sharing files:

* Certain metadata, such as GPS location, are usually purged from files before sharing on social media platforms (this is a good thing).
* All other metadata is allowed to persist, meaning that if one person attributes a file and shares it, you transparently recieve the information.
* MOST common file formats support broad categories of metadata that can cover a multitude of needs, however this metadata is usually not set by media providers.

# Specifics of TomatoManager's Metadata Management Strategy:

TomatoManager uses XMP metadata tags to track key information in file headers:

* Who created the media (publicly known names only, such as a social media handle)?
* Where was the media originally posted (DOI or URL)?
* How is the media tagged (characters, styles, expressions, themes, anything you want)?
* Who helped with the metadata management (opt-in, give credit to those who give credit)?

You can also provide captions, descriptions, lyrics, and transcripts in your metadata.
Awfully convenient, isn't it?

## What file formats are supported?

The current prototype tool relies upon [ExifTool](https://exiftool.org) as an external dependency for reading/writing metadata, so our support hinges upon their supported file formats and capabilities.
This mature, free open-source software is very robust and can handle almost any media you'll typically use.

With exiftool Version 13.50, TomatoManager can fully support:

* JPEG / JPG
* PNG
* WEBP
* GIF
* MP4
* M4A
* PDF

TomatoManager cannot currently support the following common media formats due to missing metadata-write capabilities from ExifTool.

* AIFF
* MP3
* OGG
* WAV
* WEBM

If you can help contribute metadata-write capabilities to ExifTool, consider doing so but ensure you conform to their contribution expectations!

