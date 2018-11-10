#!/bin/sh

# mp4_wrapper.sh
#
# John Newman
# 2018-10-22
#
# Searches the input directory for .h264 files and combines the ones with
# shared directories into one file in the output directory. All the blended
# .h264 files in the output directory are wrapped in an mp4 format. The output
# directory mirrors the structure of the input directory except spaces in dir
# names are removed.

fps=20

# Append all the .h264 files into one
find "$1" -name "*.h264" | sort | while read file; do
    short_path=${file//"$1"/}
    short_dir=`dirname "$short_path"`
    short_dir=${short_dir//[[:blank:]]/} # MP4Box does not like spaces
    new_file="$2$short_dir"/blended_video.h264
    mkdir -p "`dirname "$new_file"`"
    cat "$file" >> "$new_file"
done

# Wrap each .h264 file in an mp4
find "$2" -name "*.h264" | while read file; do
    MP4Box -fps "$fps" -add "$file" ${file%.*}.mp4
    rm "$file"
done

open "$2"
