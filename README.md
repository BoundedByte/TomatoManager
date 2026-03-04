# TomatoManager: Community-Sharable Metadata Read/Write for Media Attribution

TomatoManager helps you utilize your media's metadata to its full extent, with an emphasis on reliable attribution, improved organization capabilities, and robust search.
TomatoManager encourages community-based efforts to share quality information, and since documentation is embedded in media metadata, it can benefit other tools and media managers as well!

## Installation

Requires Python>=3.14, python3-pandas, and [exiftool](https://exiftool.org).

TomatoManager itself just runs as a script -- no additional compilation or installation required.

Optionally, you can also include [TagStudio](github.com/TagStudioDev/TagStudio/releases) for a GUI to create and manage tags and metadata -- TagStudio does NOT have a TomatoManager plugin, so you'll need to synchronize metadata to files via TomatoManager.

## Setup

The [License](.LICENSE) leaves you in charge of your usage of the program, but it is always recommended to create and maintain a backup of all files **PRIOR** to using TomatoManager!

No current issues are known and the tool tries to be reasonably safe unless you manually request overrides, but a backup guarantees the capability to restore your data!

---

**NOTE**: TomatoManager is an **INDEPENDENT** project and cannot fix issues with other software.

Please **DO NOT** make requests regarding TomatoManager features or compatibility from *other repository maintainers*; make those requests here!
Please **DO** share your appreciation and open-source contributions with other repositories as you are able!

To establish your own libraries or refer to interoperability between various software and TomatoManager, please refer to these specific guides:

* [ExifTool Guide](./Docs/ExifTool.md)
* [TagStudio Guide](./Docs/TagStudio.md)

## Usage and Interfaces

The current version only supports a CLI, so you'll need to use either Microsoft PowerShell or a UNIX terminal.

* CLI: For up-to-date options and usage, try: `python3 cli.py --help`.

### Future Interfaces

Planned interfaces that don't exist yet. See the [Roadmap](.Docs/Roadmap.md) for additional details.

    - Self-hostable / browser GUI
    - Centralized website with community database
    - Discord Bot

