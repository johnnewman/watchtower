#!/bin/sh

min_usage=85
days_to_save=3
supplied_dir=$1
today=`date +%Y-%m-%d`
today_sec=`date -d "$today" +%s`

check_usage() {
    usage=`df -h "$supplied_dir" | grep -vE '^Filesystem' | awk '{ print $5}'`
    usage=`expr "$usage" : '\([0-9]*\)'`
    if [ "$usage" -gt "$min_usage" ]; then
        echo `date`: Disk usage "$usage"% is above min usage "$min_usage"%. >> ~/disk_purge.log
        purge_one_day
    fi
}

purge_one_day() {
    oldest_dir=`ls -1 "$supplied_dir" | sed 1q`
    dir_date=`date -d "$oldest_dir" +%s`
    if [ "$dir_date" -le $(( $today_sec - $days_to_save * 24 * 60 * 60 )) ]; then
        echo `date`: Purging "$supplied_dir"/"$oldest_dir". >> ~/disk_purge.log
        rm -rf "$supplied_dir"/"$oldest_dir"
        check_usage
    fi
}

check_usage
