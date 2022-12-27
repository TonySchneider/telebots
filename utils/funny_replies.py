import os
import re
import sys
import time

from telethon import TelegramClient, events, errors

from helpers.loggers import get_logger
from wrappers.config_wrapper import ConfigWrapper

PROD = True
logger = get_logger(__file__)
ALLOWED_CHAT_IDS_FILE_PATH = "configurations/allowed_chat_ids.yaml"


try:
    TELEGRAM_API_ID = os.environ["TELEGRAM_API_ID"]
    TELEGRAM_API_HASH = os.environ["TELEGRAM_API_HASH"]

    TELEGRAM_API_ID = int(TELEGRAM_API_ID)

    assert os.path.isfile(ALLOWED_CHAT_IDS_FILE_PATH)
except KeyError:
    logger.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, TONY_ENGLISH_BOT_TOKEN")
    sys.exit(1)
except AssertionError:
    logger.error("Please set the environment variables properly")
    sys.exit(1)

client = TelegramClient('funny_replies' if PROD else 'dev_funny_replies', TELEGRAM_API_ID, TELEGRAM_API_HASH)
conf_obj = ConfigWrapper()
chat_ids = conf_obj.get_config_file('allowed_chat_ids')
# initial variables
ts_chat_id = chat_ids['tony']
boris_id = chat_ids['boris']
b_id = chat_ids['b']
prod_group_id = -1001408213165
test_group_id = -1001216509728
messages = {}


async def reply_a_message(message_text: str, message_id: int):
    await client.send_message(entity=prod_group_id if PROD else test_group_id, message=message_text, reply_to=message_id)


@client.on(events.NewMessage(chats=prod_group_id if PROD else test_group_id))
async def my_event_handler(event):
    global messages
    message_text = event.message.text

    conditioned_sender_id = [boris_id, b_id] if PROD else [ts_chat_id]
    message_to_send = None

    if event.message.sender_id in conditioned_sender_id and re.search(r'[י]+[א]+[ל]+[ה]+ אימו[ן]+', message_text):
        message_to_send = "💪🏼"
    elif re.search(r'מאיזשהי סיבה', message_text):
        message_to_send = "למשהו*"
    elif re.search(r'[י]+[א]+[ל]+[ה]+ פיצ[ה]+', message_text):
        message_to_send = "🍕"
    elif re.search(r'[י]+[א]+[ל]+[ה]+ קפ[ה]+', message_text):
        message_to_send = "☕"
    elif re.search(r'[י]+[א]+[ל]+[ה]+ קק[י]+', message_text) or re.match(r'קק[י]+', message_text):
        message_to_send = "💩"
    elif event.message.sender_id in conditioned_sender_id and event.message.media:
        try:
            gif_file_name = event.message.media.document.attributes[1].file_name
            if gif_file_name in ['whyy-noo.mp4']:
                message_to_send = "הגיע הזמן להחליף gif"
        except Exception:
            logger.error("Didn't find the gif file name attribute")
            pass

    if message_to_send:
        logger.info(f'Found a message from {event.message.sender.username} | text="{message_text}"')
        sent = False
        while not sent:
            try:
                logger.info(f'Will reply with "{message_to_send}"')
                await reply_a_message(message_text=message_to_send, message_id=event.message.id)
                sent = True
            except errors.rpcerrorlist.FloodWaitError:
                print('FloodWaitError exception, will try send another time in 5 seconds...')
                time.sleep(5)

if __name__ == '__main__':
    try:
        logger.info('Starting Telethon client...')
        client.start()
        client.run_until_disconnected()
    except KeyboardInterrupt:
        logger.info('Quitting... (CTRL+C pressed)\n Exits...')
    except Exception:  # Catch-all for unexpected exceptions, with stack trace
        logger.exception(f'Unhandled exception occurred!\n Aborting...')
    finally:
        client.disconnect()
        sys.exit(0)
