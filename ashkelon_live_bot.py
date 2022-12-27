import os
import sys
import time
import uuid
from typing import Union
from threading import Thread
from helpers.loggers import get_logger

import telebot
from telethon.tl.patched import Message
from telethon import TelegramClient, events, errors
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from wrappers.config_wrapper import ConfigWrapper

logger = get_logger(__file__)

DEV = False
ALLOWED_CHAT_IDS_FILE_PATH = "configurations/allowed_chat_ids.yaml"

try:
    TELEGRAM_API_ID = os.environ["TELEGRAM_API_ID"]
    TELEGRAM_API_HASH = os.environ["TELEGRAM_API_HASH"]
    TOKEN = os.environ["ASHKELON_NEWS_BOT_TOKEN"]
    # MYSQL_USER = os.environ["MYSQL_USER"]
    # MYSQL_PASS = os.environ["MYSQL_PASS"]

    TELEGRAM_API_ID = int(TELEGRAM_API_ID)

    assert os.path.isfile(ALLOWED_CHAT_IDS_FILE_PATH)
except KeyError:
    logger.error("Please set the environment variables: TELEGRAM_API_ID, TELEGRAM_API_HASH, ASHKELON_NEWS_BOT_TOKEN")
    sys.exit(1)
except AssertionError:
    logger.error("Please set the environment variables properly")
    sys.exit(1)

# initial objects
bot = telebot.TeleBot(TOKEN)
client = TelegramClient('session_name', TELEGRAM_API_ID, TELEGRAM_API_HASH)

conf_obj = ConfigWrapper()
chat_ids = conf_obj.get_config_file('allowed_chat_ids')
ts_chat_id = chat_ids['tony']

# initial variables
producer_without_confirmation = [-1001436772127]
producers = [-1001023468930, -1001337442223, -1001307152557, -1001143765178, -1001468698690, -1001406113886,
             -1001436772127, -1001221122299, ts_chat_id, -1001474443960]
confirmation_group = -1001216509728
test_group_id = -1001754623712
prod_group_id = -1001489287278
messages = {}


@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def echo_all(message):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


async def handle_deletion(message_obj: Message):
    await client.delete_messages(test_group_id, message_obj.id)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    data = call.data
    if data.startswith("accept-report:"):
        chat_id = test_group_id if DEV else prod_group_id

        button_details = data.replace('accept-report:', '')
        button_id, accept_message_id = button_details.split('|')

        message_details = messages.get(accept_message_id)
        if message_details:
            if button_id == '1':
                send_a_message_via_bot(chat_id=chat_id,
                                       message=message_details,
                                       accept_message_id=accept_message_id)
            elif button_id == '2':
                bot.delete_message(chat_id=confirmation_group, message_id=message_details.get('question_message_id'))


def send_a_message_via_bot(chat_id: Union[int, str], message: Union[dict, str], accept_message_id=None,
                           reply_markup=None) -> int:
    """
    This method sends message via bot to the provided chat id
    """
    global messages

    if isinstance(message, dict):
        media_path = message.get('media_path')
        message_object = message.get('message_obj')

        if media_path and media_path.endswith('.mp4'):
            logger.info(f"Sending video to chat_id:{chat_id}")
            sending_status = bot.send_video(chat_id, video=open(media_path, 'rb'), caption=message_object.text,
                                            reply_markup=reply_markup)
        elif media_path and media_path.endswith('.jpg'):
            logger.info(f"Sending photo to chat_id:{chat_id}")
            sending_status = bot.send_photo(chat_id, photo=open(media_path, 'rb'), caption=message_object.text,
                                            reply_markup=reply_markup)
        else:
            logger.info(f"Sending text message to chat_id:{chat_id}")
            sending_status = bot.send_message(chat_id, message_object.text, reply_markup=reply_markup)

        if sending_status:
            logger.debug(f'removing message & downloaded media by id:{accept_message_id} since it already sent')

            if media_path:
                os.remove(media_path)

            if 'question_message_id' in message.keys():
                messages.pop(accept_message_id)
                bot.delete_message(chat_id=confirmation_group, message_id=message.get('question_message_id'))
    else:
        sending_status = bot.send_message(chat_id, message, reply_markup=reply_markup)

    return sending_status.id


async def send_me_a_message(message_text: str):
    await client.send_message('me', message=message_text)


@client.on(events.NewMessage(chats=producers))
async def my_event_handler(event):
    global messages

    if any(word in event.message.text for word in ['ashkelon', 'ashqelon', 'אשקלון', 'באר גנים', 'צומת סילבר', 'מבקיעים']):
        logger.info('found message by the ashkelon word. will send it..')
        sent = False
        while not sent:
            try:
                message_id = uuid.uuid4()
                media_path = None
                logger.debug("Sending new report to TS chat and ask for acceptation")

                menu_buttons = {
                    '1': 'שלח',
                    '2': 'בטל'
                }

                reply_markup = InlineKeyboardMarkup()
                options = [InlineKeyboardButton(button_text, callback_data=f'accept-report:{button_id}|{message_id}')
                           for button_id, button_text in
                           menu_buttons.items()]

                for option in options:
                    reply_markup.row(option)

                if hasattr(event.message, 'video') and event.message.video:
                    media_path = f'temp/{message_id}.mp4'
                elif hasattr(event.message, 'photo') and event.message.photo:
                    media_path = f'temp/{message_id}.jpg'

                if media_path:
                    await event.download_media(media_path)

                message = {'message_obj': event.message,
                           'media_path': media_path}
                # if event.message.chat_id in producer_without_confirmation:
                send_a_message_via_bot(chat_id=test_group_id if DEV else prod_group_id,
                                       message=message,
                                       accept_message_id=message_id.__str__())
                # else:
                #     messages[message_id.__str__()] = message
                #     question_message_id = send_a_message_via_bot(confirmation_group, event.message.text,
                #                                                  reply_markup=reply_markup)
                #     messages[message_id.__str__()]['question_message_id'] = question_message_id
                sent = True
                if 'צופר - צבע אדום' in event.message.text:
                    time.sleep(60)
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
        logger.info('Existing...')

        bot.close()
        sys.exit(0)
