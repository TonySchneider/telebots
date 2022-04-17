import asyncio
import time
from datetime import datetime, timedelta
from telethon import TelegramClient, events, errors


api_id = 000
api_hash = ''



async def get_messages_by_word(chat, word, limit):
    result = []
    messages = await global_client.get_messages(000, limit=200)
    # async for msg in global_client.iter_messages(chat, search=word, limit=limit):
    #     print(msg.text)
    #     result.append(msg.text)

    return messages


async def get_messages_at_date(chat, date):
    result = []
    tomorrow = date + timedelta(days=1)
    async for msg in global_client.iter_messages(chat, offset_date=tomorrow):
        if msg.date < date:
            return result
        result.append(msg)


async def get_ids(client):
    dialogs = await client.get_dialogs()
    # To get the channel_id,group_id,user_id
    for chat in dialogs:
        print('name:{0} ids:{1} is_user:{2} is_channel{3} is_group:{4}'.format(chat.name, chat.id, chat.is_user,
                                                                               chat.is_channel, chat.is_group))


async def get_client():
    client = TelegramClient('session_name', api_id, api_hash)
    await client.start()
    messages = await client.get_messages(000, limit=50, search="אשקלון")
    # print(messages)

    print('waiting...')
    async for message in client.iter_messages(000):
        sent = False
        while not sent:
            try:
                status = await client.send_message('me', message=message)
                sent = True
            except errors.rpcerrorlist.FloodWaitError:
                print('exception, sleeping 5 seconds...')
                time.sleep(5)
        print(message)

    print('done')
    # for message in messages:
    #     status = await client.send_message('me', message=message)
    return client

if __name__ == '__main__':
    global_client = asyncio.run(get_client())