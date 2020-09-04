import atexit
import logging
from threading import Thread


stopped = False

def shutdown():
    global stopped
    logging.getLogger(__name__).info('Received atexit command. Stopping threads...')
    stopped = True

try:
    import uwsgi
    uwsgi.atexit = shutdown
    print('Registered uwsgi atexit handler.')
except ImportError:
    atexit.register(shutdown)
    print('Registered python atexit handler.')


class TerminableThread(Thread):

    @property
    def should_run(self):
        global stopped
        return not stopped
