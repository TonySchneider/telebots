import os
import sys
import asyncio
from telethon import TelegramClient

from helpers.loggers import get_logger

logger = get_logger(__name__)


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

# initial objects
logger.basicConfig(level=logger.INFO, format='%(asctime)s | %(levelname)-10s | %(message)s', stream=sys.stdout)


async def write_dialogs():
    dialog_lines = []
    logger.info('stating telethon client...')
    client = TelegramClient('session_name', TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.start()

    logger.info('getting dialogs...')
    dialogs = await client.get_dialogs(limit=None)
    # To get the channel_id,group_id,user_id
    for chat in dialogs:
        dialog_lines.append('name:{0} ids:{1} is_user:{2} is_channel{3} is_group:{4}'.format(chat.name, chat.id, chat.is_user,
                                                                               chat.is_channel, chat.is_group))

    logger.info(f'got {len(dialogs)} chats. writing them to a file...')
    with open('../chat_ids.txt', mode='w') as chat_ids_file:
        chat_ids_file.write("\n".join(dialog_lines))


if __name__ == '__main__':
    asyncio.run(write_dialogs())
    logger.info('Done.')