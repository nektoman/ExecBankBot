from pyrfc import Connection, LogonError, CommunicationError
from loguru import logger

class ConnectError(Exception):
    def __init__(self, text):
        self.txt = text

class SapConnect:
    @staticmethod
    def get_connection(config):
        try:
            params_connection = config._sections["connection"]
            conn = Connection(**params_connection)
            return conn
        except CommunicationError:
            logger.error("Could not connect to server.")
            raise ConnectError("Could not connect to server.")
        except LogonError:
            logger.error("Could not log in. Wrong credentials?")
            raise ConnectError("Could not log in. Wrong credentials?")
