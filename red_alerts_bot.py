from threading import Thread
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from wrappers.config_wrapper import ConfigWrapper
from wrappers.requets_wrapper import RequestWrapper
import time
import datetime

alarms = {}

conf_obj = ConfigWrapper()
telebot_conf = conf_obj.get_config_file('telebot_configurations')
bot = telebot.TeleBot(telebot_conf['safe_ashkelon_token'])

CURRENT_CHAT = telebot_conf['dev_env_chat_id']
OLD_ALARMS = []


@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def echo_all(message):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


@bot.message_handler(func=lambda message: message.text == 'מנהלים')
def get_admins_command(message):
    print(f"message from chat - '{message.chat.id}' | message text - '{message}'")

    current_text_reply = u"""
    \u2B07מנהלים
    """.encode('utf-8')
    options = []
    for admin in bot.get_chat_administrators(chat_id=CURRENT_CHAT):
        admin_name = admin.user.first_name + (" " + admin.user.last_name if admin.user.last_name else "")
        options.append(InlineKeyboardButton(admin_name, url=f'https://t.me/{admin.user.username}'))

    reply_markup = InlineKeyboardMarkup([options])
    bot.reply_to(message, current_text_reply, reply_markup=reply_markup)


def check_for_new_alarms():
    alerted_places = {}
    alerted_ids = []

    headers = conf_obj.get_config_file('oref_alerts_headers')

    while True:
        print(f"checking for new alerts..")
        req_obj = RequestWrapper()
        response_content = req_obj.perform_request(
            method='GET',
            url='https://www.oref.org.il/WarningMessages/alert/alerts.json',
            headers=headers
        )
        if response_content:
            current_alert_id = response_content['id']

            if current_alert_id not in alerted_ids:
                to_alert_places = []

                for place in response_content['data']:
                    if place not in alerted_places.keys() or datetime.datetime.now() > alerted_places[place] + datetime.timedelta(seconds=30):
                        to_alert_places.append(place)
                        alerted_places[place] = datetime.datetime.now()
                        alerted_ids.append(current_alert_id)
                    else:
                        continue

                if to_alert_places:
                    print(response_content)
                    alarm_text = "התרעת צבע אדום ב" + "<b>" + ", ".join(to_alert_places) + "</b>" + ". נא להתמגן! " + "&#128680;"
                    print(alarm_text)
                    bot.send_message(chat_id=CURRENT_CHAT, text=alarm_text, parse_mode="HTML")

        time.sleep(1)


if __name__ == '__main__':
    Thread(target=check_for_new_alarms).start()
    bot.polling(none_stop=True)
