import logging
from telethon import TelegramClient,sync, utils, errors
from telethon.tl.types import PeerUser, PeerChat
from telethon import functions, types
import pandas as pd
import time
import re
import asyncio
from contextlib import suppress
import traceback

log = logging.getLogger(__name__)
format = '%(asctime)s %(levelname)s:%(message)s'
logging.basicConfig(format=format, level=logging.INFO)

api_id = ""
api_hash = ""

filename_excel = "project_for_export_no_formulas_31_10_18.xlsx"
filename_numbers = "number.txt"

queue_entity = asyncio.Queue()
numbers = []
count_thread = 8

def load_numbers(filename):
    with open(filename, "r") as file:
        content = file.read().split("\n")
        for conten in content:
            numbers.append(conten)

def load_excel(output_filename):
    data = pd.read_excel(output_filename, 'Projects', dtype=str)
    for item in data["Telegram link"]:
        if item != "nan":
            queue_entity.put_nowait(item)


async def create_client(number):
    return await TelegramClient(number, api_id, api_hash).start()

async def parse_entity(entity, client):
    result = None
    try:
        result = client(functions.channels.GetFullChannelRequest(
            channel=entity
        ))
        print("Успешно")
    except TypeError:
        try:
            result = client(functions.users.GetFullUserRequest(
                id=entity
            ))
        except TypeError:
            result = client(functions.messages.GetFullChatRequest(
                chat_id=entity
            ))
    except errors.UsernameInvalidError:
        print("Не найден пользователь, канал или чат")
    except errors.InviteHashExpiredError:
        print("Чата больше нет")
    except errors.InviteHashInvalidError:
        print("Ссылка приглашения не валидна")
    except ValueError:
        print("Невозможно получить entity. Для начала нужно вступить в группу или чат")
    except errors.FloodWaitError:
        print("Ожидание суток")
    return result


async def crawl(future):
    futures = []
    numbers = await future
    for f in asyncio.as_completed([asyncio.ensure_future(create_client(number)) for number in numbers]):
        client = await f
        while queue_entity.qsize() > 0:
            futures.append(asyncio.ensure_future(parse_entity(queue_entity.get_nowait(), client)))
    if futures:
        await asyncio.wait(futures)

async def start_main(root):
    loop = asyncio.get_event_loop()
    initial_future = loop.create_future()
    initial_future.set_result(root)
    await crawl(initial_future)

if __name__ == '__main__':
    start = time.time()
    load_numbers(filename_numbers) #Загрузка телефонов
    #load_excel(filename_excel)     #Загрузка Excel
    loop = asyncio.get_event_loop()
    # loop.set_debug(True)
    try:
        loop.run_until_complete(start_main(numbers))
    except KeyboardInterrupt:
        for task in asyncio.Task.all_tasks():
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
    finally:
        loop.stop()
    log.info("Time work: %s", time.time() - start)
