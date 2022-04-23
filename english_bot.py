import os
import sys
import time

from helpers.loggers import get_logger
from wrappers.db_wrapper import DBWrapper
from core.english_bot_user import EnglishBotUser
from core.english_bot_telebot_extension import EnglishBotTelebotExtension

logger = get_logger(__name__)

try:
    TOKEN = os.environ["TONY_ENGLISH_BOT_TOKEN"]
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASS = os.environ["MYSQL_PASS"]
except KeyError:
    logger.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, TONY_ENGLISH_BOT_TOKEN")
    sys.exit(1)

db_connector = DBWrapper(host='176.58.99.61', mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database='english_bot')
bot = EnglishBotTelebotExtension(TOKEN)

active_users = {}


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    current_user: "EnglishBotUser" = EnglishBotUser.get_user_by_chat_id(chat_id)

    data = call.data
    if data.startswith("menu:"):
        if not current_user.is_locked():
            button_id = data.replace('menu:', '')
            if button_id == '1':
                bot.pause_user_word_sender(chat_id)

                callback_msg = bot.send_message(chat_id, 'שלח את המילה החדשה')
                bot.register_next_step_handler(callback_msg, bot.add_new_word_to_db)
            elif button_id == '2':
                current_sender_status = current_user.word_sender_active
                if not current_sender_status:
                    if current_user.num_of_words >= 4:
                        current_user.activate_word_sender()
                        bot.send_message(chat_id, 'שליחת המילים האוטומטית הופעלה')
                    else:
                        bot.send_message(chat_id, 'לא נוספו 4 מילים')
                elif current_sender_status:
                    current_user.deactivate_word_sender()
                    bot.send_message(chat_id, 'שליחת המילים האוטומטית הופסקה')
            elif button_id == '3':
                bot.pause_user_word_sender(chat_id)

                bot.show_wordlist(chat_id)
            elif button_id == '4':
                bot.pause_user_word_sender(chat_id)

                callback_msg = bot.send_message(chat_id, 'שלח מספר דקות לשינוי זמן ההמתנה')
                bot.register_next_step_handler(callback_msg, bot.change_waiting_time)
            elif button_id == '5':
                bot.send_message(chat_id, 'מה אתה צריך????!!')

    elif data.startswith("compare:"):
        logger.debug(f"comparison words for '{chat_id}'")

        button_callback = data.replace('compare:', '')
        en_word, he_word, chosen_he_word = button_callback.split('|')
        if he_word == chosen_he_word:
            bot.send_message(chat_id, 'נכון, כל הכבוד!')
        else:
            bot.send_message(chat_id, f'טעות, התרגום של המילה {en_word} זה "{he_word}"')
            time.sleep(5)

        bot.show_menu(chat_id)
        bot.resume_user_word_sender(chat_id)

    elif data.startswith("delete_word:"):
        button_callback = data.replace('delete_word:', '')
        bot.delete_word(chat_id, button_callback)

        bot.show_wordlist(chat_id)

    elif data.startswith("exit"):
        bot.show_menu(chat_id)
        bot.resume_user_word_sender(chat_id)


@bot.message_handler(commands=['start'])
def start_the_bot(message):
    bot.MESSAGES.append(message.message_id)

    bot.show_menu(message.chat.id)
    bot.send_message(message.chat.id, 'אנא הוסף לפחות 4 מילים על מנת שהמערכת תוכל להתחיל לשלוח מילים בצורה אוטומטית')

    db_connector.insert_row(table_name='users', keys_values={'chat_id': message.chat.id})


@bot.message_handler(func=lambda message: message.text in ['שלח-מילה', '/send'])
def new_word_command(message):
    bot.MESSAGES.append(message.message_id)

    current_user = EnglishBotUser.get_user_by_chat_id(message.chat.id)

    if not current_user.is_locked():
        bot.send_new_word(message.chat.id)


@bot.message_handler(func=lambda message: message.text in ['תפריט', '/menu'])
def new_word_command(message):
    bot.MESSAGES.append(message.message_id)

    current_user = EnglishBotUser.get_user_by_chat_id(message.chat.id)

    if not current_user.is_locked():
        bot.show_menu(message.chat.id)


@bot.message_handler(func=lambda message: message.text)
def catch_every_user_message(message):
    logger.debug(f"catching user message ({message.text})")
    bot.MESSAGES.append(message.message_id)


if __name__ == '__main__':
    try:
        logger.info('Starting bot... Press CTRL+C to quit.')

        logger.debug(f"Initializing users")
        fetched_users = db_connector.get_all_values_by_field(table_name='users_extended')
        for user in fetched_users:
            user_translations = db_connector.get_all_values_by_field(table_name='translations',
                                                                     condition_field='chat_id',
                                                                     condition_value=user['chat_id'])

            EnglishBotUser(chat_id=user['chat_id'],
                           word_sender_active=eval(user['auto_send_active']),
                           delay_time=user['delay_time'],
                           num_of_words=user['num_of_words'],
                           user_translations=user_translations,
                           db_connector=db_connector,
                           global_bot=bot)

        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        logger.info('Quitting... (CTRL+C pressed)\n Exits...')
    except Exception:  # Catch-all for unexpected exceptions, with stack trace
        logger.exception(f'Unhandled exception occurred!\n Aborting...')
    finally:
        logger.info('Existing...')

        bot.close()
        db_connector.close_connection()
        sys.exit(0)
