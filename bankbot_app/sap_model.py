from nekto_man_SapConnect import SapConnect, ConnectError
from functools import wraps
from loguru import logger

class SapModelError(Exception):
    def __init__(self, text):
        self.txt = text

def __sap_call_wrapper(func, *args, **kwargs):
    try:
        connect = SapConnect.get_connection(kwargs['config'])
        result = func(*args, **dict(kwargs, connect=connect))
        connect.close()
        return result
    except ConnectError as CE:
        logger.error(CE.txt)
        raise SapModelError(CE.txt)

def __sap_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return __sap_call_wrapper(func, *args, **kwargs)
    return wrapper

@__sap_call
def get_users(**kwargs):
    #ET_USERS
    return kwargs['connect'].call('ZFM_NRA_TGBB_GET_USERSK')

@__sap_call
def get_last_trans(id, **kwargs):
    #ET_TRANS
    #EV_ERROR
    return kwargs['connect'].call('ZFM_NRA_TGBB_GET_LAST_TRANSK', IV_USER_ID=str(id).zfill(10))

@__sap_call
def get_balance(id, **kwargs):
    #EV_ERROR
    #EV_BALANCE
    result = kwargs['connect'].call('ZFM_NRA_TGBB_GET_BALANCEK', IV_USER_ID=str(id).zfill(10))
    balance = result.get('EV_BALANCE').lstrip()
    if balance.endswith('-'):
        balance = balance.rstrip('-')
        balance = '-' + balance
        result['EV_BALANCE'] = balance
    return result

@__sap_call
def set_new_user(id, SAP_LOGIN, **kwargs):
    #EV_ERROR
    return kwargs['connect'].call('ZFM_NRA_TGBB_SET_NEW_USERK',
                                  IV_USER_ID=str(id).zfill(10),
                                  IV_SAP_LOGIN=SAP_LOGIN)

@__sap_call
def create_trans(user_from, user_to, comment, sum, user_creator, **kwargs):
    #EV_ERROR
    return kwargs['connect'].call('ZFM_NRA_TGBB_CREATE_TRANSK',
                                  IV_USER_FROM=user_from,
                                  IV_USER_TO=user_to,
                                  IV_COMMENT=comment,
                                  IV_SUM=sum,
                                  IV_USER_CREATOR=user_creator)

from configparser import ConfigParser
from bankbot_app.nekto_man_BankUser import BankUser
if __name__ == "__main__":
    configs = ConfigParser()
    configs.read("config\sapnwrfc_test.cfg")
    try:
       result =  get_balance('1035660707', config=configs)
       print(result)
    except SapModelError as ex:
        print(ex)