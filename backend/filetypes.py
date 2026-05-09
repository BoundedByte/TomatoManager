"""
    (C) BoundedByte 2026

    filetypes.py: FileTypes managed by TomatoManager
        - Any file type with ExifTool R/W on XMP Metadata should qualify for
          Supported
        - However, any file types I have not tested will remain at Questionable
          until they are known to work without caveats
        - Known common file formats that ExifTool does not support are listed
          at Unsupported
        - All other formats are considered Unknown
"""

Supported = ['gif','jpeg','jpg','png','m4a','mp4','pdf','webp']
Questionable = ['avif','jxl','ppm','psd','tiff']
Unsupported = ['aiff','mp3','ogg','wav','webm']

