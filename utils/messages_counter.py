import os
import sys

# from telethon import TelegramClient, events, errors
from telethon.sync import TelegramClient
from helpers.loggers import get_logger

logger = get_logger(__file__)

try:
    TELEGRAM_API_ID = os.environ["TELEGRAM_API_ID"]
    TELEGRAM_API_HASH = os.environ["TELEGRAM_API_HASH"]

    TELEGRAM_API_ID = int(TELEGRAM_API_ID)
except KeyError:
    logger.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, TONY_ENGLISH_BOT_TOKEN")
    sys.exit(1)
except AssertionError:
    logger.error("Please set the environment variables properly")
    sys.exit(1)

users = {
    475251416: {
        'messages': 0,
        'user': 'boris'
    },
    936405352: {
        'messages': 0,
        'user': 'beni'
    },
    239169883: {
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
