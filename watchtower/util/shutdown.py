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
    """
    This is a threaded class intended to be subclassed. Threads that need to
    loop in their run() method can check the should_run flag on each loop
    iteration. This flag will flip to False when Watchtower is shut down. This
    avoids the program hanging at termination time.
    """

    @property
    def should_run(self):
        global stopped
        return not stopped
