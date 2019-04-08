#!/bin/sh

# mp4_wrapper.sh
#
# John Newman
# 2018-10-22
#
# Searches the input directory for .h264 files and combines the ones with
# shared directories into one file in the output directory. If a path to a
# pem file containing the private decryption key is supplied, the .h264 files
# are decrypted using decrypt.py. All the blended .h264 files in the output
# directory are wrapped in an mp4 format. The output directory mirrors the
# structure of the input directory except spaces in dir names are removed.

while getopts ":hi:o:k:f:" opt; do
    case "$opt" in
        h )
            echo "Usage:"
            echo "    -h       Display help."
            echo "    -i       Input directory to search for h264 or h264e files."
            echo "    -o       Output directory to send mp4 files."
            echo "    -k       Optional path to pem file containing private key used to decrypt the video files."
            echo "    -f       Framerate of the video files."
            exit 0
            ;;
        i )
            input_path="$OPTARG"
            ;;
        o )
            output_path="$OPTARG"
            ;;
        k )
            key_path="$OPTARG"
            ;;
        f )
            fps="$OPTARG"
            ;;
        \?)
            echo "Invalid input: $OPTARG" 1>&2
            exit 1
            ;;
        : )
            echo "Invalid input: $OPTARG requires an argument!" 1>&2
            exit 1
            ;;
    esac
done

# Optionally decrypt all h264e files and append all the h264 data into one
find "$input_path" -name "*.h264" | sort -V | while read file; do
    short_path=${file//"$input_path"/}
    short_dir=`dirname "$short_path"`
    short_dir=${short_dir//[[:blank:]]/} # MP4Box does not like spaces
    new_file="$output_path$short_dir"/blended_video.h264
    mkdir -p "`dirname "$new_file"`"
    if [[ -z "$key_path" ]]; then
        cat "$file" >> "$new_file"
    else
        python decryption/decrypt.py -k "$key_path" -i "$file" -o $"$new_file"
    fi
done

# Wrap each combined .h264 file in an mp4
find "$output_path" -name "*.h264" | while read file; do
    MP4Box -fps "$fps" -add "$file" ${file%.*}.mp4
    rm "$file"
done

open "$output_path"
