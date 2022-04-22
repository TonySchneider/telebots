from typing import Union, Optional, List
from telebot import TeleBot, types
from telebot.async_telebot import REPLY_MARKUP_TYPES

from helpers.loggers import get_logger
from wrappers.requets_wrapper import RequestWrapper

logger = get_logger(__name__)


class BaseTelebotExtension(TeleBot):
    MESSAGES = []

    def __init__(self, token: str):
        super().__init__(token)
        self.token = token

    def send_message(
            self, chat_id: Union[int, str], text: str,
            parse_mode: Optional[str] = None,
            entities: Optional[List[types.MessageEntity]] = None,
            disable_web_page_preview: Optional[bool] = None,
            disable_notification: Optional[bool] = None,
            protect_content: Optional[bool] = None,
            reply_to_message_id: Optional[int] = None,
            allow_sending_without_reply: Optional[bool] = None,
            reply_markup: Optional[REPLY_MARKUP_TYPES] = None,
            timeout: Optional[int] = None) -> types.Message:
        logger.debug(f"sending message to '{chat_id}'. (text- '{text}')")

        msg_obj = super().send_message(chat_id, text, reply_markup=reply_markup)
        self.MESSAGES.append(msg_obj.message_id)
        return msg_obj

    def clean_chat(self, chat_id):
        request_obj = RequestWrapper()

        chat_history = request_obj.perform_request(url=f"https://api.telegram.org/bot{self.token}/getUpdates?chat_id={chat_id}")

        try:
            for message_id in self.MESSAGES:
                try:
                    self.delete_message(chat_id=chat_id, message_id=message_id)
                    self.MESSAGES.remove(message_id)
                except Exception:
                    pass

            assert chat_history
            assert hasattr(chat_history, 'result')
            assert all(hasattr(message, 'message') for message in chat_history['result'])
            assert all(hasattr(message['message'], 'message_id') for message in chat_history['result'])

            for message_id in [message['message']['message_id'] for message in chat_history['result']]:
                try:
                    self.delete_message(chat_id=chat_id, message_id=message_id)
                except Exception:
                    pass

        except AssertionError:
            pass