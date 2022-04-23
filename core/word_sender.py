import time
import threading

from helpers.loggers import get_logger

logger = get_logger(__name__)


class WordSender(threading.Thread):
    def __init__(self, chat_id: int, delay_time: int, target=None, args=()):
        threading.Thread.__init__(self, target=target, args=args)
        self.paused = False
        self.pause_cond = threading.Condition(threading.Lock())
        self.is_stopped = False
        self.chat_id = chat_id
        self.delay_time = delay_time

    def pause(self):
        self.paused = True
        # If in sleep, we acquire immediately, otherwise we wait for thread
        # to release condition. In race, worker will still see self.paused
        # and begin waiting until it's set back to False
        self.pause_cond.acquire()

    def resume(self):
        self.paused = False
        # Notify so thread will wake after lock released
        self.pause_cond.notify()
        # Now release the lock
        self.pause_cond.release()

    def stop(self):
        self.is_stopped = True
