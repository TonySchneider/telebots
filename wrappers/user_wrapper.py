import logging
from wrappers.db_wrapper import DBWrapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-10s | %(message)s', stream=sys.stdout)


class UserWrapper:
    def __init__(self, user_details: dict):
        self.user_details = user_details
        self.db_obj = DBWrapper()

    def __del__(self):
        logging.debug("updating DBs")
        self.update_user()

    def update_user(self):
        pass
