#!/bin/sh

MIN_USAGE=85
DAYS_TO_SAVE=3
SUPPLIED_DIR=$1
TODAY=`date +%Y-%m-%d`
TODAY_SEC=`date -d $TODAY +%s`

check_usage() {
    USAGE=`df -h $SUPPLIED_DIR | grep -vE '^Filesystem' | awk '{ print $5}'`
    USAGE=`expr "$USAGE" : '\([0-9]*\)'`
    if [ $USAGE -gt $MIN_USAGE ]
    then
        echo `date`: Disk usage $USAGE% is above min usage $MIN_USAGE%. >> ~/disk_purge.log
        purge_one_day
    fi
}

purge_one_day() {
    OLDEST_DIR=`ls -1 $SUPPLIED_DIR | sed 1q`
    DIR_DATE=`date -d $OLDEST_DIR +%s`
    if [ $DIR_DATE -le $(( $TODAY_SEC - $DAYS_TO_SAVE * 24 * 60 * 60 )) ]
    then
        echo `date`: Purging $SUPPLIED_DIR/$OLDEST_DIR. >> ~/disk_purge.log
        rm -rf $SUPPLIED_DIR/$OLDEST_DIR
        check_usage
    fi
}

check_usage
