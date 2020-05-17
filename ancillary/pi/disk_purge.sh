#!/bin/sh

# disk_purge.sh
#
# John Newman
# 2018-10-22
#
# Use as a cron job. If the supplied motion event directory's partition
# usage is over $min_usage percent, the oldest motion event directory
# over $days_to_save old will be deleted.
#
# Example crontab listing to execute every 5 minutes:
# */5 * * * * /home/<username>/watchtower/ancillary/pi/disk_purge.sh "/home/<username>/watchtower/<cam name>" >> /var/logs/watchtower/disk_purge.log

min_usage=80
days_to_save=3
supplied_dir=$1
today=`date +%Y-%m-%d`
today_sec=`date -d "$today" +%s`

check_usage() {
    usage=`df -h "$supplied_dir" | grep -vE '^Filesystem' | awk '{ print $5}'`
    usage=`expr "$usage" : '\([0-9]*\)'`
    if [ "$usage" -gt "$min_usage" ]; then
        echo `date`: Disk usage "$usage"% is above min usage "$min_usage"%.
        purge_one_day
    fi
}

purge_one_day() {
    regex="^.*/[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}$"
    oldest_path=`find "$supplied_dir" -maxdepth 1 -type d -regextype sed -regex "$regex" | sort | sed 1q`
    oldest_dir=`basename "$oldest_path"`
    dir_date=`date -d "$oldest_dir" +%s`
    if [ "$dir_date" -le $(( $today_sec - $days_to_save * 24 * 60 * 60 )) ]; then
        echo `date`: Purging "$oldest_path".
        rm -rf "$oldest_path"
        check_usage
    fi
}

check_usage
