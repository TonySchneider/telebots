import sys
import time
import logging

from core.word_sender import WordSender


class EnglishBotUser:
    active_users = []

    @staticmethod
    def initial_active_users(users_db_data):
        logging.debug(f"Initializing users")

        for user in users_db_data:
            active_user = EnglishBotUser(user['chat_id'])

            EnglishBotUser.active_users.append(active_user)

    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.word_sender = WordSender(target=self.new_words_worker, args=(self.chat_id,))

    def new_words_worker(self, chat_id):
        current_user_details = db_obj.get_all_values_by_field(table_name='users',
                                                              condition_field='chat_id',
                                                              condition_value=chat_id,
                                                              first_item=True)
        if not current_user_details:
            logging.error(f"Didn't manage to get user's details by the chat_id - '{chat_id}'\nAborting...")
            sys.exit(1)

        while True:
            with self.word_sender.pause_cond:
                while self.word_sender.paused:
                    self.word_sender.pause_cond.wait()

                if eval(current_user_details['auto_send_active']) and not USERS[chat_id]['locked']:
                    self.send_new_word(chat_id)
                # else:
                #     show_menu(chat_id)

                current_user_details = db_obj.get_all_values_by_field(table_name='users',
                                                                      condition_field='chat_id',
                                                                      condition_value=chat_id,
                                                                      first_item=True)
            time.sleep(current_user_details['delay_time'] * 60)

    def start_word_sender(self):
        logging.debug(f"Starting word sender (chat_id={self.chat_id})")
        self.word_sender.start()

    def lock_chat(self):
        logging.debug(f"Pausing word sender (chat_id={self.chat_id})")
        self.word_sender.pause()

    def unlock_chat(self):
        logging.debug(f"Resuming word sender (chat_id={self.chat_id})")
        self.word_sender.resume()