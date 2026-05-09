# Development Roadmap

## To-Be-Developed

### As soon as available and trustworthy:

    - Manager registration for filetypes in case of subclassing/extensions
    - Manager search via date
    - Replicate TagStudio folder consolidation based on real path to reduce folder count in the database
    - TagStudio full compatibility on NOTES type
    - Support multiple URLs for a media within ExifTool
    - Reject ill-formatted dbs from ExifTool and TagStudio upon load

### v2.x: Cross-platform browser/GUI as simplified TagStudio replacement

    - File browsing with previews
    - Fully featured GUI-based metadata management and searching
    - More nuanced metadata merges
        + Blank slate to accumulate an authoritative merge (with user input to pick which version)
        + Constrain merges to particular fields
    - Improved search capabilities:
        + Date-fields
        + Tagged boolean status

### v3.x: Centralized website with community databases

    - Centralized website
        + Subscribable endpoint for metadata updates with per-community databases (or alternative IP if self-hosting)
        + Allows pseudonoymous affiliation for submitted attributions so others can thank you for it

### v4.x: External tool support

    - Transcript, SauceNao and/or other external resource/aggregator lookups
    - Automatically match files based on content (reverse image search or hashing-based)

### v5.x: App integrations

    - Discord bot to fetch attributions when known
        + Crawler for known/consenting persons and sites to automatically match new works ASAP

## Released

### v1.x: CLI fully functions with{out} TagStudio

    - ✅ Metadata write/read to/from files, TagStudio, ExifTool databases
    - ✅ Metadata-based search

