#!/bin/bash
# (C) BoundedByte 2026

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <FILES>";
    exit 0;
fi;

tags=( 'AttributionURL' 'Author' 'BaseURL' 'Caption' 'Description' 'DOI' 'Label' 'Lyrics' 'MetadataAuthorityIdentifier' 'MetadataAuthorityName' 'MetadataDate' 'MetadataLastEdited' 'MetadataLastEditorIdentifier' 'MetadataLastEditorName' 'MetadataModDate' 'Notes' 'Tagged' 'TagsList' 'Transcript' 'TranscriptLink' 'URLUrl' );

export_target="exiftool.csv";
if [[ -f '.TagStudio' ]]; then
    export_target=".TagStudio/${export_target}";
fi;
# Ensure export directory exists
mkdir -pv $( dirname "${export_target}" );

cmd="exiftool -csv -o ${export_target}";
for tag in ${tags[@]}; do
    cmd="${cmd} -${tag}";
done;
cmd="${cmd} -- ${@}";
echo "${cmd}";
eval "${cmd}";

