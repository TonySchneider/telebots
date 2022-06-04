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

logger = get_logger(__name__)


DEV = False

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
bot = telebot.TeleBot(TOKEN)
client = TelegramClient('session_name', TELEGRAM_API_ID, TELEGRAM_API_HASH)

# initial variables
producer_without_confirmation = [-1001436772127]
producers = [-1001023468930, -1001337442223, -1001307152557, -1001143765178, -1001468698690, -1001406113886, -1001436772127, -1001221122299, 239169883]
ts_chat_id = 239169883
test_group_id = -1001216509728
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
        button_details = data.replace('accept-report:', '')
        button_id, accept_message_id = button_details.split('|')
        if button_id == '1':
            send_a_message_via_bot(chat_id=test_group_id if DEV else prod_group_id,
                                   message_object=messages[accept_message_id].get('message_obj'),
                                   accept_message_id=accept_message_id,
                                   media_path=messages[accept_message_id].get('media_path'))
        elif button_id == '2':
            pass


def send_a_message_via_bot(chat_id: Union[int, str], message_object: Union[Message, str], accept_message_id=None, media_path=None, reply_markup=None):
    """
    This method sends message via bot to the provided chat id
    """
    global messages
    if chat_id == 'me':
        chat_id = ts_chat_id

    if isinstance(message_object, Message):
        if media_path and media_path.endswith('.mp4'):
            logger.info(f"Sending video to chat_id:{chat_id}")
            sending_status = bot.send_video(chat_id, video=open(media_path, 'rb'), caption=message_object.text, reply_markup=reply_markup)
        elif media_path and media_path.endswith('.jpg'):
            logger.info(f"Sending photo to chat_id:{chat_id}")
            sending_status = bot.send_photo(chat_id, photo=open(media_path, 'rb'), caption=message_object.text, reply_markup=reply_markup)
        else:
            logger.info(f"Sending text message to chat_id:{chat_id}")
            sending_status = bot.send_message(chat_id, message_object.text, reply_markup=reply_markup)
    else:
        sending_status = bot.send_message(chat_id, message_object, reply_markup=reply_markup)

    if sending_status and accept_message_id in messages.keys():
        logger.debug(f'removing message by id:{accept_message_id} since it already sent')
        messages.pop(accept_message_id)
        # TODO: delete messages
        # client.delete_messages(test_group_id, message_object.id)
    return sending_status


async def send_me_a_message(message_text: str):
    await client.send_message('me', message=message_text)


@client.on(events.NewMessage(chats=producers))
async def my_event_handler(event):
    global messages

    if any(word in event.message.text for word in ['ashkelon', 'ashqelon', 'אשקלון']):
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
                options = [InlineKeyboardButton(button_text, callback_data=f'accept-report:{button_id}|{message_id}') for button_id, button_text in
                           menu_buttons.items()]

                for option in options:
                    reply_markup.row(option)

                if hasattr(event.message, 'video') and event.message.video:
                    media_path = f'temp/{message_id}.mp4'
                elif hasattr(event.message, 'photo') and event.message.photo:
                    media_path = f'temp/{message_id}.jpg'

                messages[message_id.__str__()] = {'message_obj': event.message}
                if media_path:
                    await event.download_media(media_path)
                    messages[message_id.__str__()]['media_path'] = media_path

                if event.message.chat_id in producer_without_confirmation:
                    send_a_message_via_bot(chat_id=test_group_id,
                                           message_object=messages[message_id].get('message_obj'),
                                           accept_message_id=message_id,
                                           media_path=messages[message_id].get('media_path'))
                else:
                    send_a_message_via_bot(ts_chat_id, event.message.text, reply_markup=reply_markup)
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
        logger.info('Existing...')

        bot.close()
        sys.exit(0)
