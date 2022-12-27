import os
import sys
import time
import uuid
import telebot
from typing import Union
from threading import Thread
from telethon.tl.patched import Message
from telethon import TelegramClient, events, errors
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from helpers.loggers import get_logger
from helpers.trenslations import translate_it
from wrappers.config_wrapper import ConfigWrapper

logger = get_logger(__file__)
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
# db_connector = DBWrapper(host='', mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database='english_bot')
bot = telebot.TeleBot(TOKEN)
client = TelegramClient('alerts', TELEGRAM_API_ID, TELEGRAM_API_HASH)
conf_obj = ConfigWrapper()
chat_ids = conf_obj.get_config_file('allowed_chat_ids')

# initial variables
ts_chat_id = chat_ids['tony']
test_group_id = -1001216509728
messages = {}


def send_a_message_via_bot(chat_id: Union[int, str], message_object: Union[Message, str], accept_message_id=None, media_path=None, text=None, reply_markup=None):
    """
    This method sends message via bot to the provided chat id
    """
    global messages

    if isinstance(message_object, Message):
        if media_path and media_path.endswith('.mp4'):
            logger.info(f"Sending video to chat_id:{chat_id}")
            sending_status = bot.send_video(chat_id, video=open(media_path, 'rb'), caption=text if text else message_object.text, reply_markup=reply_markup)
        elif media_path and media_path.endswith('.jpg'):
            logger.info(f"Sending photo to chat_id:{chat_id}")
            sending_status = bot.send_photo(chat_id, photo=open(media_path, 'rb'), caption=text if text else message_object.text, reply_markup=reply_markup)
        else:
            logger.info(f"Sending text message to chat_id:{chat_id}")
            sending_status = bot.send_message(chat_id, text if text else message_object.text, reply_markup=reply_markup)
    else:
        sending_status = bot.send_message(chat_id, text if text else message_object, reply_markup=reply_markup)

    if sending_status and accept_message_id in messages.keys():
        logger.debug(f'removing message & downloaded media by id:{accept_message_id} since it already sent')

        if media_path:
            os.remove(media_path)
        messages.pop(accept_message_id)

        # bot.delete_message(confirmation_group, message_object.id)
    return sending_status


async def send_me_a_message(message_text: str):
    await client.send_message('me', message=message_text)


@client.on(events.NewMessage(chats=(-1001493954148, -1001238669963, -1001318165547)))
async def my_event_handler(event):
    global messages

    logger.info('Got a message. will send it..')
    sent = False
    while not sent:
        try:
            message_id = uuid.uuid4().__str__()
            media_path = None

            logger.debug(f'sending message to {test_group_id}')

            logger.debug(f"Will translate message by id - '{message_id}'")
            translated_text = translate_it(text=event.message.text, lang_from="ar", lang_to="he")
            if not translated_text:
                logger.debug(f"Didn't manage to translate message by id - '{message_id}'...")
                break

            translated_text = translated_text.replace('\\', '').replace('t.me/', '')

            if hasattr(event.message, 'video') and event.message.video:
                media_path = f'temp/{message_id}.mp4'
            elif hasattr(event.message, 'photo') and event.message.photo:
                media_path = f'temp/{message_id}.jpg'

            messages[message_id] = {'message_obj': event.message}
            if media_path:
                await event.download_media(media_path)
                messages[message_id]['media_path'] = media_path

            send_a_message_via_bot(chat_id=ts_chat_id,
                                   message_object=messages[message_id].get('message_obj'),
                                   accept_message_id=message_id,
                                   media_path=messages[message_id].get('media_path'),
                                   text=translated_text)
            # send_a_message_via_bot(ts_chat_id, translated_text)
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
