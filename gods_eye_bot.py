import os
import sys
import time

from core._base_telebot_extension import BaseTelebotExtension
from core.gods_eye_user import GodsEyeUser
from helpers.loggers import get_logger
from wrappers.db_wrapper import DBWrapper

logger = get_logger(__name__)

try:
    TOKEN = os.environ["GODS_EYE_BOT_TOKEN"]
    MYSQL_HOST = os.environ["MYSQL_HOST"]
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASS = os.environ["MYSQL_PASS"]
except KeyError:
    logger.error("Please set the environment variables: MYSQL_USER, MYSQL_PASS, GODS_EYE_BOT_TOKEN")
    sys.exit(1)

db_connector = DBWrapper(host=MYSQL_HOST, mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database='gods_eye')
bot = BaseTelebotExtension(TOKEN)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    current_user: "GodsEyeUser" = GodsEyeUser.get_user_by_chat_id(chat_id)

    data = call.data


@bot.message_handler(commands=['start'])
def start_the_bot(message):
    chat_id = message.chat.id
    current_user: "GodsEyeUser" = GodsEyeUser.get_user_by_chat_id(chat_id)

    if current_user:
        pass
    else:
        GodsEyeUser(chat_id=chat_id,
                    db_connector=db_connector,
                    global_bot=bot)
        db_connector.insert_row(table_name='users', keys_values={'chat_id': chat_id})

        bot.send_message(chat_id, 'ברוך הבא')


@bot.message_handler(func=lambda message: message.text)
def catch_every_user_message(message):
    logger.debug(f"catching user message ({message.text})")
    chat_id = message.chat.id
    current_user: "GodsEyeUser" = GodsEyeUser.get_user_by_chat_id(chat_id)

    if current_user:
        current_user.messages.append(message.message_id)


if __name__ == '__main__':
    try:
        logger.info('Starting gods eye bot... Press CTRL+C to quit.')

        logger.debug(f"Initializing users")
        fetched_users = db_connector.get_all_values_by_field(table_name='users')
        for user in fetched_users:
            GodsEyeUser(chat_id=user['chat_id'],
                        db_connector=db_connector,
                        global_bot=bot)

        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        logger.info('Quitting... (CTRL+C pressed)\n Exits...')
    except Exception:  # Catch-all for unexpected exceptions, with stack trace
        logger.exception(f'Unhandled exception occurred!\n Aborting...')
    finally:
        logger.info('Existing...')

        bot.close()
        db_connector.close_connection()
        sys.exit(0)
