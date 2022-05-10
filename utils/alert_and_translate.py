import os
import sys
import time
import telebot
from typing import Union
from threading import Thread
from telethon import TelegramClient, events, errors
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from helpers.loggers import get_logger
from helpers.trenslations import translate_it

logger = get_logger(__name__)


try:
    TELEGRAM_API_ID = os.environ["TELEGRAM_API_ID"]
    TELEGRAM_API_HASH = os.environ["TELEGRAM_API_HASH"]
    TOKEN = os.environ["ASHKELON_NEWS_BOT_TOKEN"]
    # MYSQL_USER = os.environ["MYSQL_USER"]
    # MYSQL_PASS = os.environ["MYSQL_PASS"]

    TELEGRAM_API_ID = int(TELEGRAM_API_ID)
except KeyError:
    logger.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, TONY_ENGLISH_BOT_TOKEN")
    sys.exit(1)
except AssertionError:
    logger.error("Please set the environment variables properly")
    sys.exit(1)

# initial objects
# db_connector = DBWrapper(host='', mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database='english_bot')
bot = telebot.TeleBot(TOKEN)
client = TelegramClient('alerts', TELEGRAM_API_ID, TELEGRAM_API_HASH)

# initial variables
ts_chat_id = 239169883
test_group_id = -1001216509728
last_message = None


# @bot.callback_query_handler(func=lambda call: True)
# def handle_query(call):
#     data = call.data
#     if data.startswith("accept-report:"):
#         button_id = data.replace('accept-report:', '')
#         if button_id == '1':
#             send_a_message_via_bot(test_group_id, last_message)
#         elif button_id == '2':
#             pass
#
#         send_a_message_via_bot()


def send_a_message_via_bot(chat_id: Union[int, str], message_object, reply_markup=None):
    """
    This method sends message via bot to the provided chat id
    """
    if chat_id == 'me':
        chat_id = ts_chat_id
    bot.send_message(chat_id, message_object, reply_markup=reply_markup)


async def send_me_a_message(message_text: str):
    await client.send_message('me', message=message_text)


# def accept_new_report(message_text):
#     logger.debug("Sending new report to TS chat and ask for acceptation")
#
#     menu_buttons = {
#         '1': 'שלח',
#         '2': 'בטל'
#     }
#
#     reply_markup = InlineKeyboardMarkup()
#     options = [InlineKeyboardButton(button_text, callback_data=f'accept-report:{button_id}') for button_id, button_text in
#                menu_buttons.items()]
#
#     for option in options:
#         reply_markup.row(option)
#
#     send_a_message_via_bot(ts_chat_id, message_text, reply_markup=reply_markup)


@client.on(events.NewMessage(chats=(-1001493954148, -1001238669963)))
async def my_event_handler(event):
    global last_message

    logger.info('Got message. will send it..')
    sent = False
    while not sent:
        try:
            logger.debug(f'sending message to {test_group_id}')
            last_message = event.message

            translated_text = translate_it(text=event.message.text, lang_from="ar", lang_to="he")
            translated_text = translated_text.replace('\\', '').replace('t.me/', '')

            send_a_message_via_bot(ts_chat_id, translated_text)
            # accept_new_report(event.message.text)
            sent = True
        except errors.rpcerrorlist.FloodWaitError:
            print('exception, sleeping 5 seconds...')
            time.sleep(5)


if __name__ == '__main__':
    try:
        logger.info('Starting bot...')
        Thread(target=bot.polling, args=(True,)).start()

        logger.info('Starting Telethon client...')
        client.start()
        client.run_until_disconnected()
    except KeyboardInterrupt:
        logger.info('Quitting... (CTRL+C pressed)\n Exits...')
    except Exception:  # Catch-all for unexpected exceptions, with stack trace
        logger.exception(f'Unhandled exception occurred!\n Aborting...')
    finally:
        client.disconnect()
        bot.close()
        # db_connector.close_connection()
        sys.exit(0)
