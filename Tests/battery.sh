#!/bin/bash

# Safeguards and usage
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <file to test>";
    exit 0;
fi;
if [[ "$1" == *" "* ]]; then
    echo "File '${1}' cannot be tested -- contains space in filename";
    exit 1;
fi;
echo "Testing '${1}'";

TEST_TAG="Test1234567890Test1234567890Test1234567890Test1234567890";
TEST_DATE="2026:01:30 13:59:00.99";
TEST_LINK="https://exiftool.org/TagNames/XMP.html#QualifiedLink";
TEST_LINKQUALIFIER="Use_a_browser";
TEST_QUALIFIED_LINK="{Link=${TEST_LINK},LinkQualifier=${TEST_LINKQUALIFIER}}";
TEST_EXPECTED_LINK="[${TEST_QUALIFIED_LINK}]";

exiftool \
    -About="${TEST_TAG}" \
    -AttributionURL="${TEST_TAG}" \
    -Author="${TEST_TAG}" \
    -BaseURL="${TEST_TAG}" \
    -Caption="${TEST_TAG}" \
    -Comment="${TEST_TAG}" \
    -Description="${TEST_TAG}" \
    -DOI="${TEST_TAG}" \
    -Label="${TEST_TAG}" \
    -LabelName1="${TEST_TAG}" \
    -LabelName2="${TEST_TAG}" \
    -LabelName3="${TEST_TAG}" \
    -LabelName4="${TEST_TAG}" \
    -LabelName5="${TEST_TAG}" \
    -LabelName6="${TEST_TAG}" \
    -Lyrics="${TEST_TAG}" \
    -MetadataAuthorityIdentifier="${TEST_TAG}" \
    -MetadataAuthorityName="${TEST_TAG}" \
    -MetadataDate="${TEST_DATE}" \
    -MetadataLastEdited="${TEST_DATE}" \
    -MetadataLastEditorIdentifier="${TEST_TAG}" \
    -MetadataLastEditorName="${TEST_TAG}" \
    -MetadataModDate="${TEST_DATE}" \
    -Notes="${TEST_TAG}" \
    -Tagged=Yes \
    -TagsList="${TEST_TAG}" \
    -Transcript="${TEST_TAG}" \
    -TranscriptLink="${TEST_QUALIFIED_LINK}" \
    -URLUrl="${TEST_TAG}" \
    $1;

expect_valid_count=0;
validated_count=0;

# Verify test tags
for tag in "About" "AttributionURL" "Author" "BaseURL" "Caption" "Comment" "Description" "DOI" "Label" "LabelName1" "LabelName2" "LabelName3" "LabelName4" "LabelName5" "LabelName6" "Lyrics" "MetadataAuthorityIdentifier" "MetadataAuthorityName" "MetadataLastEditorIdentifier" "MetadataLastEditorName" "Notes" "TagsList" "Transcript" "URLUrl"; do
    expect_valid_count=$(( ${expect_valid_count} + 1 ));
    exifresult=$( exiftool -${tag} $1 | sed 's/ /\n/g' | tail -n1 );
    if [[ ${#exifresult} -gt 0 ]]; then
        if [[ "${exifresult}" == "${TEST_TAG}" ]]; then
            validated_count=$(( ${validated_count} + 1 ));
            echo "+ ${tag} Validated: ${exifresult}";
        else
            echo "! Tag '${tag}' is '${exifresult}', expected '${TEST_TAG}'";
        fi;
    else
        echo "! No hit on tag: ${tag}";
    fi;
done;
# Verify booleans
for tag in "Tagged"; do
    expect_valid_count=$(( ${expect_valid_count} + 1 ));
    exifresult=$( exiftool -${tag} $1 | sed 's/ /\n/g' | tail -n1 );
    if [[ ${#exifresult} -gt 0 ]]; then
        if [[ "${exifresult}" == "Yes" ]]; then
            validated_count=$(( ${validated_count} + 1 ));
            echo "+ ${tag} Validated: ${exifresult}";
        else
            echo "! Boolean tag '${tag}' is '${exifresult}', expected 'Yes'";
        fi;
    else
        echo "! No hit on boolean tag: ${tag}";
    fi;
done;
# Verify test dates
for tag in "MetadataDate" "MetadataLastEdited" "MetadataModDate"; do
    expect_valid_count=$(( ${expect_valid_count} + 1 ));
    exifresult=$( exiftool -${tag} $1 | sed 's/ /\n/g' | tail -n2 | tr '\n' ' ' | sed 's/\(.*\) $/\1/' );
    if [[ ${#exifresult} -gt 0 ]]; then
        if [[ "${exifresult}" == "${TEST_DATE}" ]]; then
            validated_count=$(( ${validated_count} + 1 ));
            echo "+ ${tag} Validated: ${exifresult}";
        else
            echo "! Date tag '${tag}' is '${exifresult}', expected '${TEST_DATE}'";
        fi;
    else
        echo "! No hit on date tag: ${tag}";
    fi;
done;
# Verify test links
for tag in "TranscriptLink"; do
    expect_valid_count=$(( ${expect_valid_count} + 1 ));
    exifresult=$( exiftool -${tag} -struct $1 | sed 's/ /\n/g' | tail -n1 );
    if [[ ${#exifresult} -gt 0 ]]; then
        if [[ "${exifresult}" == "${TEST_EXPECTED_LINK}" ]]; then
            validated_count=$(( ${validated_count} + 1 ));
            echo "+ ${tag} Validated: ${exifresult}";
        else
            echo "! Link tag '${tag}' is '${exifresult}', expected '${TEST_EXPECTED_LINK}'";
        fi;
    else
        echo "! No hit on link tag: ${tag}";
    fi;
done;

# Final verdict
if [[ ${validated_count} -eq ${expect_valid_count} ]]; then
    echo "All ${expect_valid_count} tag tests passed :)";
else
    echo "${validated_count} / ${expect_valid_count} tag tests passed";
fi;
