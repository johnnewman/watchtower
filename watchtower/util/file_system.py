import os
from datetime import datetime
import shutil

def __dirnames_matching_format(dirnames, format):
    matching_dates = []
    for dirname in dirnames:
        try:
            dt = datetime.strptime(dirname, format)
            if dt is not None:
                matching_dates.append(dt)
        except ValueError:
            pass
    matching_dates.sort()
    return [datetime.strftime(dt, format) for dt in matching_dates]

def all_recording_days(path, day_format):
    dirpath, dirnames, filenames = next(os.walk(path))
    return __dirnames_matching_format(dirnames, day_format)

def recording_times(path, day_dirname, time_format):
    path = os.path.join(path, day_dirname)
    dirpath, dirnames, filenames = next(os.walk(path))
    return __dirnames_matching_format(dirnames, time_format)

def delete_recording_day(path, day_dirname, day_format):
    path = os.path.join(path, day_dirname)
    if os.path.exists(os.path.dirname(path)):
        try:
            shutil.rmtree(path)
            return True
        except Exception as ex:
            print(ex)
    print('path does not exist %s' % path)
    return False




