from nekto_man_SapConnect import SapConnect, ConnectError
from functools import wraps
from loguru import logger

class SapModelError(Exception):
    def __init__(self, text):
        self.txt = text

def __sap_call_wrapper(func, config, *args):
    try:
        connect = SapConnect.get_connection(config)
        result = func(connect=connect, *args)
        connect.close()
        return result
    except ConnectError as CE:
        logger.error(CE.txt)
        raise SapModelError(CE.txt)

def __sap_call(func):
    @wraps(func)
    def wrapper(*args):
        return __sap_call_wrapper(func, config, *args)
    return wrapper

@__sap_call
def get_users(config, connect=None):
    #ET_USERS
    return connect.call('ZFM_NRA_TGBB_GET_USERS')

@__sap_call
def get_last_trans(config, id, connect=None):
    #ET_TRANS
    #EV_ERROR
    return connect.call('ZFM_NRA_TGBB_GET_LAST_TRANS', IV_USER_ID=str(id).zfill(10))

@__sap_call
def get_balance(config, id, connect=None):
    #EV_ERROR
    #EV_BALANCE
    result = connect.call('ZFM_NRA_TGBB_GET_BALANCEK', IV_USER_ID=str(id).zfill(10))
    balance = result.get('EV_BALANCE').lstrip()
    if balance.endswith('-'):
        balance = balance.rstrip('-')
        balance = '-' + balance
        result['EV_BALANCE'] = balance
    return result

@__sap_call
def set_new_user(config, id, SAP_LOGIN, connect=None):
    #EV_ERROR
    return connect.call('ZFM_NRA_TGBB_SET_NEW_USERK',
                        IV_USER_ID=str(id).zfill(10),
                        IV_SAP_LOGIN=SAP_LOGIN)

@__sap_call
def create_trans(config, user_from, user_to, comment, sum, user_creator, connect=None):
    #EV_ERROR
    return connect.call('ZFM_NRA_TGBB_CREATE_TRANSK',
                        IV_USER_FROM=user_from,
                        IV_USER_TO=user_to,
                        IV_COMMENT=comment,
                        IV_SUM=sum,
                        IV_USER_CREATOR=user_creator)

from configparser import ConfigParser
from bankbot_app.nekto_man_BankUser import BankUser
if __name__ == "__main__":
    config = ConfigParser()
    config.read("config\sapnwrfc_test.cfg")
    try:
       result =  get_balance(config, '1035660707')
       print(result)
    except SapModelError as ex:
        print(ex)