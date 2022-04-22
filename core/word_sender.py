import time
import threading

from helpers.loggers import get_logger

logger = get_logger(__name__)


class WordSender(threading.Thread):
    def __init__(self, chat_id: int, delay_time: int, global_bot, **kwargs):
        threading.Thread.__init__(self, **kwargs)
        self.paused = False
        self.pause_cond = threading.Condition(threading.Lock())
        self._is_stopped = False
        self.global_bot = global_bot
        self.chat_id = chat_id
        self.delay_time = delay_time

    def new_words_worker(self):
        while True:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self._is_stopped:
                    logger.debug(f"The word sender of chat id '{self.chat_id}' was stopped")
                    break

                self.global_bot.send_new_word(self.chat_id)

            time.sleep(self.delay_time * 60)

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
        self._is_stopped = True
