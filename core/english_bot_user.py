import time

from helpers.loggers import get_logger
from core.word_sender import WordSender

logger = get_logger(__file__)


class EnglishBotUser:
    active_users = {}

    @staticmethod
    def get_user_by_chat_id(chat_id: int):
        return EnglishBotUser.active_users.get(chat_id)

    def __init__(self, chat_id: int, db_connector, global_bot, word_sender_active: bool = False, delay_time: int = 20, num_of_words: int = 0,
                 user_translations: list = None):
        self.chat_id = chat_id
        self.word_sender = None
        self.messages = []
        self.word_sender_active = word_sender_active
        self.global_bot = global_bot
        self.delay_time = delay_time
        self.num_of_words = num_of_words
        self.user_translations = user_translations if user_translations else []
        self.db_connector = db_connector
        self.word_sender_paused = False

        EnglishBotUser.active_users[chat_id] = self

    def new_words_worker(self):
        while True:
            if self.word_sender.is_stopped:
                logger.debug(f"The word sender of chat id '{self.chat_id}' was stopped")
                break

            self.global_bot.send_new_word(self.chat_id)

            while self.word_sender_paused:
                if self.word_sender.is_stopped:
                    break
                time.sleep(1)

            logger.debug(f"WordSender | Sleeping {self.delay_time} minutes")
            time.sleep(self.delay_time * 60)
            # except KeyError:
            #     logger.error(f"TODO: Word sender | KeyError Exception Skipped. chat id - {self.chat_id}")
            # except Exception as e:
            #     logger.error(f"Word sender | Exception - {e}")
            #     self.global_bot.send_message(chat_id=self.chat_id, text='מערכת שליחת התרגילים קרסה, אנא פנה למפתחים')
            #     return

    def is_locked(self):
        return self.word_sender_paused

    def activate_word_sender(self):
        logger.debug(f"Activating word sender (chat_id={self.chat_id})")

        self.word_sender = WordSender(chat_id=self.chat_id,
                                      delay_time=self.delay_time,
                                      target=self.new_words_worker)
        self.word_sender.start()

        # TODO: change the following to celery task
        if not self.word_sender_active:
            self.db_connector.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                           condition_value=self.chat_id, value=True)
            self.word_sender_active = True

    def pause_sender(self):
        logger.debug(f"Pausing word sender (chat_id={self.chat_id})")
        self.word_sender_paused = True

        # if self.word_sender:
        #     self.word_sender.pause()

    def resume_sender(self):
        logger.debug(f"Resuming word sender (chat_id={self.chat_id})")
        self.word_sender_paused = False

        # if self.word_sender:
        #     self.word_sender.resume()

    def deactivate_word_sender(self):
        logger.debug(f"Deactivating word sender (chat_id={self.chat_id})")

        # change the status in DB
        self.db_connector.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                       condition_value=self.chat_id, value=False)

        # change in the object (mem)
        self.word_sender_active = False

        # stop the thread
        if self.word_sender:
            self.word_sender.stop()
            self.word_sender = None

    def delete_word(self, en_word: str) -> bool:
        logger.debug(f"Deleting word ({en_word})")

        delete_status = self.db_connector.delete_by_field(table_name='translations', field_condition='en_word',
                                                          value_condition=en_word, second_field_condition='chat_id',
                                                          second_value_condition=self.chat_id)

        if delete_status:
            self.num_of_words -= 1
            self.user_translations = [translate for translate in self.user_translations if translate['en_word'] != en_word]

        return delete_status

    def update_delay_time(self, new_time: int) -> bool:
        update_status = self.db_connector.update_field(table_name='users', condition_field='chat_id',
                                                       condition_value=self.chat_id, field='delay_time',
                                                       value=new_time)

        if update_status:
            self.delay_time = new_time

        return update_status

    def update_translations(self, translations) -> bool:
        insertion_status = self.db_connector.insert_multiple_rows(table_name='translations',
                                                                  keys_values=translations)

        if insertion_status:
            self.user_translations += translations
            self.num_of_words += 1

        return insertion_status

    def close(self):
        if self.word_sender:
            self.word_sender.stop()
