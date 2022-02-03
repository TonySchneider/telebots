import os
import sys
import time
import random
import telebot
import logging
from threading import Thread
from googletrans import Translator
from wrappers.db_wrapper import DBWrapper
from wrappers.requets_wrapper import RequestWrapper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


try:
    TOKEN = os.environ["TONY_ENGLISH_BOT_TOKEN"]
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASS = os.environ["MYSQL_PASS"]
except KeyError:
    logging.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, TONY_ENGLISH_BOT_TOKEN. Aborting...")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-10s | %(message)s', stream=sys.stdout)
db_obj = DBWrapper(host='127.0.0.1', mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database='english_bot')


bot = telebot.TeleBot(TOKEN)

USERS = []
MESSAGES = []


def send_message(chat_id, text, reply_markup=None):
    logging.debug(f"sending message to '{chat_id}'. (text- '{text}')")

    global MESSAGES

    msg_obj = bot.send_message(chat_id, text, reply_markup=reply_markup)
    MESSAGES.append(msg_obj.message_id)
    return msg_obj


def show_menu(chat_id):
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

    clean_chat(chat_id)
    send_message(chat_id, "תפריט", reply_markup=reply_markup)


def show_wordlist(chat_id):
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

    clean_chat(chat_id)
    send_message(chat_id, "רשימת המילים שלך:", reply_markup=reply_markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id

    data = call.data
    if data.startswith("menu:"):
        button_id = data.replace('menu:', '')
        if button_id == '1':
            lock_chat(chat_id)

            callback_msg = send_message(chat_id, 'שלח את המילה החדשה')
            bot.register_next_step_handler(callback_msg, add_new_word_to_db)
        elif button_id == '2':
            user_details = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id',
                                                          condition_value=chat_id, first_item=True)
            current_value = eval(user_details['auto_send_active'])
            if not current_value:
                if user_details['number_of_words'] >= 4:
                    db_obj.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                        condition_value=chat_id, value=not current_value)
                    send_message(chat_id, 'שליחת המילים האוטומטית הופעלה')
                else:
                    send_message(chat_id, 'לא הוספו 4 מילים')
            elif current_value:
                db_obj.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                    condition_value=chat_id, value=not current_value)
                send_message(chat_id, 'שליחת המילים האוטומטית הופסקה')
        elif button_id == '3':
            lock_chat(chat_id)

            show_wordlist(chat_id)
        elif button_id == '4':
            lock_chat(chat_id)

            callback_msg = send_message(chat_id, 'שלח מספר דקות לשינוי זמן ההמתנה')
            bot.register_next_step_handler(callback_msg, change_waiting_time)
        elif button_id == '5':
            send_message(chat_id, 'מה אתה צריך????!!')

    elif data.startswith("compare:"):
        logging.debug(f"comparison words for '{chat_id}'")

        button_callback = data.replace('compare:', '')
        en_word, he_word, chosen_he_word = button_callback.split('|')
        if he_word == chosen_he_word:
            send_message(chat_id, 'נכון, כל הכבוד!')
        else:
            send_message(chat_id, f'טעות, התרגום של המילה {en_word} זה "{he_word}"')

        show_menu(chat_id)
        unlock_chat(chat_id)

    elif data.startswith("delete_word:"):
        button_callback = data.replace('delete_word:', '')
        delete_word(chat_id, button_callback)

        show_wordlist(chat_id)

    elif data.startswith("exit"):
        show_menu(chat_id)
        unlock_chat(chat_id)


def add_new_word_to_db(message):
    new_word = message.text.lower()

    try:
        assert new_word
        assert new_word.isalpha()
        assert len(new_word) < 46
    except AssertionError:
        send_message(message.chat.id, 'המילה צריכה להכיל רק אותיות ולהיות לא יותר מ45 תווים')
        return

    translations = get_translations(new_word)
    if not translations:
        send_message(message.chat.id, 'המערכת לא הצליחה למצוא תרגום למילה המבוקשת')
        return

    statuses = []

    for translation in translations:
        statuses.append(db_obj.insert_row(table_name='translations',
                                          keys_values={'en_word': new_word, 'he_word': translation,
                                                       'chat_id': message.chat.id}))

    if all(statuses):
        send_message(message.chat.id, f'המילה {new_word} נוספה בהצלחה')
        db_obj.increment_field(table_name='users', condition_field='chat_id', condition_value=message.chat.id,
                               field='number_of_words')
    else:
        send_message(message.chat.id, 'המערכת לא הצליחה להוסיף את המילה המבוקשת, שאל את המפתחים')

    show_menu(message.chat.id)


def change_waiting_time(message):
    new_time = message.text
    logging.debug(f"Changing time to '{new_time}'. | chat_id - '{message.chat.id}'")

    try:
        assert new_time, "The object is empty"
        assert new_time.isnumeric(), "The object is not numeric"
        assert int(new_time) <= 24 * 60, "The number is more than 24 hours"
        update_status = db_obj.update_field(table_name='users', condition_field='chat_id',
                                            condition_value=message.chat.id, field='delay_time', value=new_time)
        if update_status:
            send_message(message.chat.id, f'זמן ההמתנה שונה ל-{new_time} דקות')
        else:
            send_message(message.chat.id, 'המערכת לא הצליחה לשנות את זמן ההמתנה')
    except AssertionError as e:
        logging.error(f"There was an assertion error. Error - '{e}'. | method - 'change_waiting_time' | message.text - '{new_time}'")
    finally:
        unlock_chat(message.chat.id)
        show_menu(message.chat.id)


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


def send_new_word(chat_id):
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

    clean_chat(chat_id)
    send_message(chat_id, f'בחר את התרגום של {chosen_en_word}', reply_markup=reply_markup)

    lock_chat(chat_id)


@bot.message_handler(commands=['start'])
def start_the_bot(message):
    show_menu(message.chat.id)
    send_message(message.chat.id, 'אנא הוסף לפחות 4 מילים על מנת שהמערכת תוכל להתחיל לשלוח מילים בצורה אוטומטית')

    db_obj.insert_row(table_name='users', keys_values={'chat_id': message.chat.id})


def clean_chat(chat_id):
    request_obj = RequestWrapper()
    chat_history = request_obj.perform_request(url=f"https://api.telegram.org/bot{TOKEN}/getUpdates?chat_id={chat_id}")

    try:
        for message_id in MESSAGES:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
                MESSAGES.remove(message_id)
            except Exception:
                pass

        assert chat_history
        assert hasattr(chat_history, 'result')
        assert all(hasattr(message, 'message') for message in chat_history['result'])
        assert all(hasattr(message['message'], 'message_id') for message in chat_history['result'])

        for message_id in [message['message']['message_id'] for message in chat_history['result']]:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass

    except AssertionError:
        pass


def delete_word(chat_id, en_word):
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
            send_message(chat_id, f'שליחת המילים האוטומטית הופסקה, מספר המילים לא מספיקה ({new_number_of_words_value})')
            db_obj.update_field(table_name='users', field='auto_send_active', condition_field='chat_id',
                                condition_value=chat_id, value=False)


def lock_chat(chat_id):
    for user in USERS:
        if user['chat_id'] == chat_id:
            user['locked'] = True


def unlock_chat(chat_id):
    for user in USERS:
        if user['chat_id'] == chat_id:
            user['locked'] = False


@bot.message_handler(func=lambda message: message.text == 'שלח מילה')
def new_word_command(message):
    send_new_word(message.chat.id)


def new_words_worker(chat_id):
    current_user_details = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id', condition_value=chat_id, first_item=True)
    if not current_user_details:
        logging.error(f"Didn't manage to get user's details by the chat_id - '{chat_id}'\nAborting...")
        sys.exit(1)

    while True:
        if eval(current_user_details['auto_send_active']):
            send_new_word(chat_id)
        else:
            show_menu(chat_id)

        current_user_details = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id',
                                                              condition_value=chat_id, first_item=True)
        time.sleep(current_user_details['delay_time'] * 60)


if __name__ == '__main__':
    try:
        logging.info('Starting bot... Press CTRL+C to quit.')

        USERS = db_obj.get_all_values_by_field(table_name='users')

        for user in USERS:
            user['locked'] = False

        bot.polling(none_stop=True)

        threads = []
        for current_chat_id in [user['chat_id'] for user in USERS]:
            thread = Thread(target=new_words_worker, args=(current_chat_id,))
            thread.start()
            threads.append(thread)

    except KeyboardInterrupt:
        logging.info('Quitting... (CTRL+C pressed)\n Exits...')
    except Exception:  # Catch-all for unexpected exceptions, with stack trace
        logging.exception(f'Unhandled exception occurred!\n Aborting...')
    finally:
        logging.debug("cleaning chats..")
        for user in USERS:
            clean_chat(user['chat_id'])

        db_obj.close_connection()
        sys.exit(0)
