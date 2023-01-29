import json
import os
import sys
import time

# from telethon import TelegramClient, events, errors
from telethon.sync import TelegramClient
from helpers.loggers import get_logger
from wrappers.config_wrapper import ConfigWrapper

logger = get_logger(__file__)

try:
    TELEGRAM_API_ID = os.environ["TELEGRAM_API_ID"]
    TELEGRAM_API_HASH = os.environ["TELEGRAM_API_HASH"]

    TELEGRAM_API_ID = int(TELEGRAM_API_ID)
except KeyError:
    logger.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, TONY_ENGLISH_BOT_TOKEN")
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

print("counting...")
start_time = time.time()

with TelegramClient('messages_counter', TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
    for message in client.iter_messages(-1001408213165):
        users[message.sender_id]['messages'] += 1
        # print(f"{users[message.sender_id]['user']}={users[message.sender_id]['messages']}")

print(f"Finished. took {start_time - time.time()} seconds.")
print("results:\n")
print(json.dumps(users, indent=4))
