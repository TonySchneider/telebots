import os
import sys
import time
import random
import telebot
import logging
from threading import Thread, Lock
from googletrans import Translator

from core.english_bot_telebot_extension import EnglishBotTelebotExtension
from core.english_bot_user import EnglishBotUser
from wrappers.db_wrapper import DBWrapper
from wrappers.requets_wrapper import RequestWrapper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


try:
    TOKEN = os.environ["TONY_ENGLISH_BOT_TOKEN"]
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASS = os.environ["MYSQL_PASS"]
except KeyError:
    logging.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, TONY_ENGLISH_BOT_TOKEN")
    sys.exit(1)


logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-10s | %(message)s', stream=sys.stdout)
db_obj = DBWrapper(host='localhost', mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database='english_bot')
bot = EnglishBotTelebotExtension(TOKEN)

USERS = {}


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id

    data = call.data
    if data.startswith("menu:"):
        button_id = data.replace('menu:', '')
        if button_id == '1':
            lock_chat(chat_id)

            callback_msg = bot.send_message(chat_id, 'שלח את המילה החדשה')
            bot.register_next_step_handler(callback_msg, add_new_word_to_db)
        elif button_id == '2':
            user_details = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id',
                                                          condition_value=chat_id, first_item=True)
            current_value = eval(user_details['auto_send_active'])
            if not current_value:
                if user_details['number_of_words'] >= 4:
                    db_obj.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                        condition_value=chat_id, value=not current_value)
                    bot.send_message(chat_id, 'שליחת המילים האוטומטית הופעלה')
                else:
                    bot.send_message(chat_id, 'לא הוספו 4 מילים')
            elif current_value:
                db_obj.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                    condition_value=chat_id, value=not current_value)
                bot.send_message(chat_id, 'שליחת המילים האוטומטית הופסקה')
        elif button_id == '3':
            lock_chat(chat_id)

            bot.show_wordlist(chat_id)
        elif button_id == '4':
            lock_chat(chat_id)

            callback_msg = bot.send_message(chat_id, 'שלח מספר דקות לשינוי זמן ההמתנה')
            bot.register_next_step_handler(callback_msg, bot.change_waiting_time)
        elif button_id == '5':
            bot.send_message(chat_id, 'מה אתה צריך????!!')

    elif data.startswith("compare:"):
        logging.debug(f"comparison words for '{chat_id}'")

        button_callback = data.replace('compare:', '')
        en_word, he_word, chosen_he_word = button_callback.split('|')
        if he_word == chosen_he_word:
            bot.send_message(chat_id, 'נכון, כל הכבוד!')
        else:
            bot.send_message(chat_id, f'טעות, התרגום של המילה {en_word} זה "{he_word}"')

        bot.show_menu(chat_id)
        unlock_chat(chat_id)

    elif data.startswith("delete_word:"):
        button_callback = data.replace('delete_word:', '')
        bot.delete_word(chat_id, button_callback)

        bot.show_wordlist(chat_id)

    elif data.startswith("exit"):
        bot.show_menu(chat_id)
        unlock_chat(chat_id)


def get_translations(word):
    translator = Translator()
    trans_obj = translator.translate(word, dest='he')

    all_translations = trans_obj.extra_data['all-translations']
    if not all_translations:
        return [trans_obj.text] if hasattr(trans_obj, 'text') else None

    return_in_hebrew_list = []

    for translation in all_translations:
        current_list = translation[2]
        for trans in current_list:
            if any(isinstance(obj, float) for obj in trans):
                return_in_hebrew_list.append(trans[0])

    if not return_in_hebrew_list:
        for translation in all_translations:
            current_list = translation[2]
            return_in_hebrew_list.append(current_list[0][0])

    return return_in_hebrew_list


@bot.message_handler(commands=['start'])
def start_the_bot(message):
    bot.show_menu(message.chat.id)
    bot.send_message(message.chat.id, 'אנא הוסף לפחות 4 מילים על מנת שהמערכת תוכל להתחיל לשלוח מילים בצורה אוטומטית')

    db_obj.insert_row(table_name='users', keys_values={'chat_id': message.chat.id})


@bot.message_handler(func=lambda message: message.text == 'שלח מילה')
def new_word_command(message):
    bot.send_new_word(message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'תפריט')
def new_word_command(message):
    if not USERS[message.chat.id]['locked']:
        bot.show_menu(message.chat.id)


if __name__ == '__main__':
    try:
        logging.info('Starting bot... Press CTRL+C to quit.')

        fetched_users = db_obj.get_all_values_by_field(table_name='users')
        EnglishBotUser.initial_active_users(fetched_users)

        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        logging.info('Quitting... (CTRL+C pressed)\n Exits...')
    except Exception:  # Catch-all for unexpected exceptions, with stack trace
        logging.exception(f'Unhandled exception occurred!\n Aborting...')
    finally:
        pass

        # TODO: update users table

        # logging.debug("cleaning chats..")
        # for registered_chat in USERS.keys():
        #     clean_chat(registered_chat)

        db_obj.close_connection()
        sys.exit(0)
