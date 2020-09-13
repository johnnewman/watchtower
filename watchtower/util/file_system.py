"""This module contains convenience functions for file system operations
involving recordings.

Watchtower stores recordings in the following directory structure:
watcthower/
   instance/
      recordings/           <- Contains all camera recordings.
         YYYY-mm-dd/        <- Contains all recordings for that day.
            HH.MM.SS/       <- Contains a single recording triggered at that timestamp.
               trigger.jpg  <- The motion frame that triggered the recording.
               video.h264   <- The full recording video.
"""

import os
from datetime import datetime
import shutil

def __dirnames_matching_format(dirnames, format):
    """
    Iterates through dirnames and returns a sorted array of directory names
    that match the provided format.
    """
    matching_dates = []
    for dirname in dirnames:
        try:
            dt = datetime.strptime(dirname, format)
            if dt is not None:
                matching_dates.append(dt)
        except ValueError:
            pass
    matching_dates.sort(reverse=True)
    return [datetime.strftime(dt, format) for dt in matching_dates]

def all_recordings(path, day_format, time_format):
    """
    Iterates through the provided directory path and returns an array of
    dictionaries where each dictionary represents one day.
    """
    recordings = []
    days = all_recording_days(path, day_format)
    for day in days:
        recordings.append({
            'day': day,
            'times': all_recording_times_for_day(path, day, time_format)
        })
    return recordings

def all_recording_days(path, day_format):
    """
    Iterates through the provided directory path and returns an array of all
    day directories that match the provided format.
    """
    dirpath, dirnames, filenames = next(os.walk(path))
    return __dirnames_matching_format(dirnames, day_format)

def all_recording_times_for_day(path, day_dirname, time_format):
    """
    Iterates through the provided day directory path and returns an array of
    all time directories that match the provided format.
    """
    path = os.path.join(path, day_dirname)
    dirpath, dirnames, filenames = next(os.walk(path))
    return __dirnames_matching_format(dirnames, time_format)

def delete_recording(path, day_dirname, time_dirname=None):
    """
    If a time_dirname is supplied, this will delete the time directory within
    the provided day directory. Otherwise if just a day_dirname is supplied,
    the day's whole directory tree will be deleted.
    """
    path = os.path.join(path, day_dirname)
    if time_dirname is not None:
        path = os.path.join(path, time_dirname)
    if os.path.exists(os.path.dirname(path)):
        try:
            shutil.rmtree(path)
            return True
        except Exception as ex:
            print(ex)
    return False
