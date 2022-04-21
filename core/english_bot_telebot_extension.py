import os
import sys
import time
import random
import telebot
import logging
from threading import Thread, Lock
from googletrans import Translator

from core.english_bot_user import EnglishBotUser
from core.word_sender import WordSender
from wrappers.db_wrapper import DBWrapper
from wrappers.requets_wrapper import RequestWrapper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import logging
from typing import Union, Optional, List

from telebot import TeleBot, types
from telebot.async_telebot import REPLY_MARKUP_TYPES

from core._base_telebot_extension import BaseTelebotExtension


class EnglishBotTelebotExtension(BaseTelebotExtension):
    MESSAGES: List

    def __init__(self, token: str):
        super(EnglishBotTelebotExtension, self).__init__(token)
        self.word_sender = None

    def show_menu(self, chat_id):
        logging.debug(f"showing menu for '{chat_id}'")

        menu_buttons = {
            '1': 'הוסף מילה חדשה',
            '2': 'התחל/עצור שליחה אוטומטית',
            '3': 'רשימת מילים ואפשרות מחיקה',
            '4': 'שנה זמן המתנה בין מילים',
            '5': 'עזרה'
        }

        reply_markup = InlineKeyboardMarkup()
        options = [InlineKeyboardButton(button_text, callback_data=f'menu:{button_id}') for button_id, button_text in
                   menu_buttons.items()]

        for option in options:
            reply_markup.row(option)

        # clean_chat(chat_id)
        self.send_message(chat_id, "תפריט", reply_markup=reply_markup)

    def show_wordlist(self, chat_id):
        logging.debug(f"showing wordlist for '{chat_id}'")

        en_words = list(set(db_obj.get_all_values_by_field(table_name='translations', condition_field='chat_id',
                                                           condition_value=chat_id, field='en_word')))
        cross_icon = u"\u274c"

        words_buttons = [InlineKeyboardButton(en_word, callback_data=f'word:{en_word}') for en_word in en_words]
        cross_icon_buttons = [InlineKeyboardButton(cross_icon, callback_data=f'delete_word:{en_word}') for en_word in
                              en_words]

        reply_markup = InlineKeyboardMarkup()

        for button_index in range(len(words_buttons)):
            reply_markup.row(words_buttons[button_index], cross_icon_buttons[button_index])

        reply_markup.row(InlineKeyboardButton("חזרה לתפריט הראשי", callback_data=f'exit'))

        # clean_chat(chat_id)
        self.send_message(chat_id, "רשימת המילים שלך:", reply_markup=reply_markup)

    def add_new_word_to_db(self, message):
        new_word = message.text.lower()

        try:
            assert new_word
            assert new_word.isalpha()
            assert len(new_word) < 46
        except AssertionError:
            self.send_message(message.chat.id, 'המילה צריכה להכיל רק אותיות ולהיות לא יותר מ45 תווים')
            return

        translations = get_translations(new_word)
        if not translations:
            self.send_message(message.chat.id, 'המערכת לא הצליחה למצוא תרגום למילה המבוקשת')
            return

        statuses = []

        for translation in translations:
            statuses.append(db_obj.insert_row(table_name='translations',
                                              keys_values={'en_word': new_word, 'he_word': translation,
                                                           'chat_id': message.chat.id}))

        if all(statuses):
            self.send_message(message.chat.id, f'המילה {new_word} נוספה בהצלחה')
            db_obj.increment_field(table_name='users', condition_field='chat_id', condition_value=message.chat.id,
                                   field='number_of_words')
        else:
            self.send_message(message.chat.id, 'המערכת לא הצליחה להוסיף את המילה המבוקשת, שאל את המפתחים')

        self.show_menu(message.chat.id)

    def change_waiting_time(self, message):
        new_time = message.text
        logging.debug(f"Changing time to '{new_time}'. | chat_id - '{message.chat.id}'")

        try:
            assert new_time, "The object is empty"
            assert new_time.isnumeric(), "The object is not numeric"
            assert int(new_time) <= 24 * 60, "The number is more than 24 hours"
            update_status = db_obj.update_field(table_name='users', condition_field='chat_id',
                                                condition_value=message.chat.id, field='delay_time', value=new_time)
            if update_status:
                self.send_message(message.chat.id, f'זמן ההמתנה שונה ל-{new_time} דקות')
            else:
                self.send_message(message.chat.id, 'המערכת לא הצליחה לשנות את זמן ההמתנה')
        except AssertionError as e:
            logging.error(
                f"There was an assertion error. Error - '{e}'. | method - 'change_waiting_time' | message.text - '{new_time}'")
        finally:
            self.unlock_chat(message.chat.id)
            self.show_menu(message.chat.id)

    def send_new_word(self, chat_id):
        all_trans = db_obj.get_all_values_by_field(table_name='translations', condition_field='chat_id',
                                                   condition_value=chat_id)

        en_words = list(set([trans['en_word'] for trans in all_trans]))
        chosen_en_word = random.choice(en_words)
        en_words.remove(chosen_en_word)

        chosen_he_word = random.choice([trans['he_word'] for trans in all_trans if trans['en_word'] == chosen_en_word])

        additional_random_en_words = []
        while len(additional_random_en_words) < 3:
            current_random_choice = random.choice(en_words)
            if current_random_choice not in additional_random_en_words:
                additional_random_en_words.append(current_random_choice)

        random_he_words = []
        while additional_random_en_words:
            current_en_word = additional_random_en_words.pop()
            current_random_he_word = random.choice(
                [trans['he_word'] for trans in all_trans if trans['en_word'] == current_en_word])
            random_he_words.append(current_random_he_word)

        random_he_words.append(chosen_he_word)

        random.shuffle(random_he_words)

        reply_markup = InlineKeyboardMarkup()
        options = [InlineKeyboardButton(button_he_word,
                                        callback_data=f'compare:{chosen_en_word}|{chosen_he_word}|{button_he_word}') for
                   button_he_word in random_he_words]

        for option in options:
            reply_markup.row(option)

        # clean_chat(chat_id)
        self.send_message(chat_id, f'בחר את התרגום של {chosen_en_word}', reply_markup=reply_markup)
        logging.debug(f"sent word '{chosen_en_word}' to chat id - '{chat_id}'")
        self.lock_chat(chat_id)

    def delete_word(self, chat_id, en_word):
        delete_status = db_obj.delete_by_field(table_name='translations', field_condition='en_word',
                                               value_condition=en_word, second_field_condition='chat_id',
                                               second_value_condition=chat_id)

        if delete_status:
            current_user_details = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id',
                                                                  condition_value=chat_id, first_item=True)
            new_number_of_words_value = current_user_details['number_of_words'] - 1
            db_obj.decrement_field(table_name='users', field='number_of_words', condition_field='chat_id',
                                   condition_value=chat_id)

            if eval(current_user_details['auto_send_active']) and new_number_of_words_value < 4:
                self.send_message(chat_id,
                                  f'שליחת המילים האוטומטית הופסקה, מספר המילים לא מספיקה ({new_number_of_words_value})')
                db_obj.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                    condition_value=chat_id, value=False)

    def polling(self, non_stop: bool = False, skip_pending=False, interval: int = 0, timeout: int = 20,
                long_polling_timeout: int = 20, allowed_updates: Optional[List[str]] = None,
                none_stop: Optional[bool] = None):

        # TODO: check necessity of the lock object
        # threads_lock = Lock()
        # threads = []
        for user in EnglishBotUser.active_users:
            user.start_word_sender()

        super().polling(none_stop=True)
