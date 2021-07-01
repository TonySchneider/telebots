import random
from threading import Thread
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from googletrans import Translator
import time
from wrappers.db_wrapper import DBWrapper
from wrappers.config_wrapper import ConfigWrapper
conf_obj = ConfigWrapper()

MYSQL_IP = '127.0.0.1'
MYSQL_USER = 'root'
MYSQL_PASS =
MYSQL_SCHEMA = 'english_bot'

db_obj = DBWrapper(host=MYSQL_IP, mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database=MYSQL_SCHEMA)

telebot_conf = conf_obj.get_config_file('telebot_configurations')
TOKEN = telebot_conf['tony_english_token']

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(func=lambda message: message.text == 'תפריט')
def show_menu(message):
    menu_buttons = {
        '1': 'הוסף מילה חדשה',
        '2': 'התחל/עצור שליחה אוטומטית',
        '3': 'רשימת מילים ואפשרות מחיקה',
        '4': 'שנה זמן המתנה בין מילים',
        '5': 'עזרה'
    }

    current_text_reply = u"""
    \u2B07תפריט:
    """.encode('utf-8')

    reply_markup = InlineKeyboardMarkup()
    options = [InlineKeyboardButton(button_text, callback_data=f'menu:{button_id}') for button_id, button_text in menu_buttons.items()]

    for option in options:
        reply_markup.row(option)

    msg = bot.reply_to(message, current_text_reply, reply_markup=reply_markup)
    clean_chat(message.chat.id, msg.message_id)

    return msg.message_id


def show_wordlist(chat_id):
    en_words = db_obj.get_all_values_by_field(table_name='translations', condition_field='chat_id', condition_value=chat_id, field='en_word')
    cross_icon = u"\u274c".encode('utf-8')

    words_buttons = [InlineKeyboardButton(en_word) for en_word in en_words]
    cross_icon_buttons = [InlineKeyboardButton(cross_icon, callback_data=f'delete_word:{en_word}') for en_word in en_words]

    reply_markup = InlineKeyboardMarkup()

    for button_index in range(len(words_buttons)):
        reply_markup.row(words_buttons[button_index], cross_icon_buttons[button_index])

    msg = bot.send_message(chat_id, "רשימת המילים שלך:", reply_markup=reply_markup)
    clean_chat(chat_id, msg.message_id)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    data = call.data
    if data.startswith("menu:"):
        button_id = data.replace('menu:', '')
        if button_id == '1':
            callback_msg = bot.send_message(call.message.chat.id, 'שלח את המילה החדשה')
            bot.register_next_step_handler(callback_msg, add_new_word_to_db)
        elif button_id == '2':
            user_details = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id', condition_value=call.message.chat.id)
            current_value = user_details['auto_send_active']
            if not current_value:
                if user_details['number_of_words'] >= 4:
                    db_obj.update_field(table_name='users', field='auto_send_active', condition_field='chat_id', condition_value=call.message.chat.id, value=not current_value)
                    bot.send_message(call.message.chat.id, 'שליחת המילים האוטומטית הופעלה')
                else:
                    bot.send_message(call.message.chat.id, 'לא הוספו 4 מילים')
            else:
                bot.send_message(call.message.chat.id, 'שליחת המילים האוטומטית הופסקה')
        elif button_id == '3':
            pass
            # TODO: you saved a bookmark at python folder
        elif button_id == '4':
            callback_msg = bot.send_message(call.message.chat.id, 'שלח מספר דקות לשינוי זמן ההמתנה')
            bot.register_next_step_handler(callback_msg, change_waiting_time)
        elif button_id == '5':
            bot.send_message(call.message.chat.id, 'מה אתה צריך????!!')

    elif data.startswith("compare:"):
        button_callback = data.replace('compare:', '')
        en_word, he_word, chosen_he_word = button_callback.split('|')
        if he_word == chosen_he_word:
            bot.send_message(call.message.chat.id, 'נכון, כל הכבוד!')
        else:
            bot.send_message(call.message.chat.id, f'טעות, התרגום של המילה {en_word} זה "{he_word}"')

    elif data.startswith("delete_word:"):
        button_callback = data.replace('delete_word:', '')
        delete_word(call.message.chat.id, button_callback)

        show_wordlist(call.message.chat.id)


def add_new_word_to_db(message):
    # TODO: increase the number_of_words in users table
    new_word = message.text.lower()
    translations = get_translations(new_word)
    if not translations:
        bot.send_message(message.chat.id, 'המערכת לא הצליחה למצוא תרגום למילה המבוקשת')
        return

    statuses = []

    for translation in translations:
        statuses.append(db_obj.insert_row(table_name='translations', keys_values={'en_word': new_word, 'he_word': translation}))

    if all(statuses):
        bot.send_message(message.chat.id, f'המילה {new_word} נוספה בהצלחה')
    else:
        bot.send_message(message.chat.id, 'המערכת לא הצליחה להוסיף את המילה המבוקשת, שאל את המפתחים')


def change_waiting_time(message):
    pass
    # TODO: ..


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
    all_trans = db_obj.get_all_values_by_field(table_name='translations')

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
        current_random_he_word = random.choice([trans['he_word'] for trans in all_trans if trans['en_word'] == current_en_word])
        random_he_words.append(current_random_he_word)

    random_he_words.append(chosen_he_word)

    reply_markup = InlineKeyboardMarkup()
    options = [InlineKeyboardButton(button_he_word, callback_data=f'compare:{chosen_en_word}|{chosen_he_word}|{button_he_word}') for button_he_word in random_he_words]

    for option in options:
        reply_markup.row(option)

    msg = bot.send_message(chat_id, f'בחר את התרגום של {chosen_en_word}', reply_markup=reply_markup)
    clean_chat(chat_id, msg.message_id)


@bot.message_handler(commands=['start'])
def start_the_bot(message):
    message_id = show_menu(message)
    bot.send_message(message.chat.id, 'אנא הוסף לפחות 4 מילים על מנת שהמערכת תוכל להתחיל לשלוח מילים בצורה אוטומטית')

    db_obj.insert_row(table_name='users', keys_values={
        'chat_id': message.chat.id,
        'last_message_id': message_id
    })
    # TODO: add logging


def clean_chat(chat_id, message_id):
    last_message_id = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id', condition_value=chat_id, field='last_message_id')

    for msg_id in range(message_id - 1, last_message_id, -1):
        try:
            bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass

    db_obj.update_field(table_name='users', field='last_message_id', condition_field='chat_id', condition_value=chat_id, value=message_id)


def delete_word(chat_id, en_word):
    db_obj.delete_by_field(table_name='translations', field_condition='en_word', value_condition=en_word, second_field_condition='chat_id', second_value_condition=chat_id)

    current_user_details = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id', condition_value=chat_id)
    new_number_of_words_value = current_user_details['number_of_words'] - 1
    db_obj.update_field(table_name='users', field='number_of_words', condition_field='chat_id', condition_value=chat_id, value=new_number_of_words_value)

    if eval(current_user_details['auto_send_active']) and new_number_of_words_value < 4:
        bot.send_message(chat_id, f'שליחת המילים האוטומטית הופסקה, מספר המילים לא מספיקה ({new_number_of_words_value})')
        db_obj.update_field(table_name='users', field='auto_send_active', condition_field='chat_id', condition_value=chat_id, value=False)


@bot.message_handler(func=lambda message: message.text == 'שלח מילה')
def new_word_command(message):
    send_new_word(message.chat.id)


def new_words_worker(chat_id):
    current_user_details = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id', condition_value=chat_id)

    while True:
        if eval(current_user_details['auto_send_active']):
            send_new_word(chat_id)

        current_user_details = db_obj.get_all_values_by_field(table_name='users', condition_field='chat_id', condition_value=chat_id)
        time.sleep(current_user_details['delay_time'] * 60)


if __name__ == '__main__':
    users = db_obj.get_all_values_by_field(table_name='users')
    users = [users] if len(users) else users

    for current_chat_id in [user['chat_id'] for user in users]:
        Thread(target=new_words_worker, args=(current_chat_id,)).start()

    bot.polling(none_stop=True)
