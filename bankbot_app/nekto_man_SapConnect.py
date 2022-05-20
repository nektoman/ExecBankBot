import configparser
from pyrfc import Connection, ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError


class SapConnect:
    @staticmethod
    def get_connection(config):
        try:
            params_connection = config._sections["connection"]
            conn = Connection(**params_connection)
            return conn
        except CommunicationError:
            print("Could not connect to server.")
            raise
        except LogonError:
            print("Could not log in. Wrong credentials?")
            raise