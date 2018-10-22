#!/bin/sh

fps=15

cp -r "$1" "$2"
find "$2" -name "*.h264" | while read file; do
    MP4Box -fps "$fps" -add "$file" ${file%.*}.mp4
    rm "$file"
done
open "$2"
