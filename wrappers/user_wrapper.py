import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-10s | %(message)s', stream=sys.stdout)


class UserWrapper:
    db_obj = None

    def __init__(self, user_details: dict):
        self.user_details = user_details

    def __del__(self):
        logging.debug("updating DBs")
        self.update_user()

    def update_user(self):
        pass

    @staticmethod
    def set_db_obj(db_obj): UserWrapper.db_obj = db_obj
