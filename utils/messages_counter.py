import os
import sys

# from telethon import TelegramClient, events, errors
from telethon.sync import TelegramClient
from helpers.loggers import get_logger
from wrappers.config_wrapper import ConfigWrapper

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


conf_obj = ConfigWrapper()
chat_ids = conf_obj.get_config_file('allowed_chat_ids')
# initial variables
ts_chat_id = chat_ids['tony']


users = {
    chat_ids['boris']: {
        'messages': 0,
        'user': 'boris'
    },
    chat_ids['b']: {
        'messages': 0,
        'user': 'b'
    },
    chat_ids['tony']: {
        'messages': 0,
        'user': 'tony'
    },
}

with TelegramClient('messages_counter', TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
    for message in client.iter_messages(-1001408213165):
        users[message.sender_id]['messages'] += 1
        print(f"{users[message.sender_id]['user']}={users[message.sender_id]['messages']}")

# async def get_messages():
#     logger.info('stating telethon client...')
#     channel_id = -1001408213165
#
#     client = TelegramClient('messages_counter', TELEGRAM_API_ID, TELEGRAM_API_HASH)
#     await client.start()
#
#     logger.info(f'getting messages from channel - {channel_id}...')
#
#     for message in await client.iter_messages(channel_id, limit=10):
#         print(message.message)
#
# if __name__ == '__main__':
#     get_messages()
