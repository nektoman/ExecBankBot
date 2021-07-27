import re
from nekto_man_SapConnect import SapConnect, ABAPRuntimeError, ABAPApplicationError, CommunicationError, LogonError


class TextHandlerFactory:
    @staticmethod
    def get_handler(message, bankbot):
        if bankbot.states.get_step(message.from_user.id) == bankbot.states.STEP_WAIT_LOGIN_AUTH:
            return Authorization()
        elif bankbot.states.get_step(message.from_user.id) == bankbot.states.STEP_WAIT_LOGIN_RECEIVER:
            return SearchName()
        elif bankbot.states.get_step(message.from_user.id) == bankbot.states.STEP_WAIT_SUM:
            return FillSum()
        else:
            return Dummy()


class Dummy:
    @staticmethod
    def process(message, bankbot):
        return


class Authorization:
    @staticmethod
    def process(message, bankbot):
        # Если статус пользователя - "ожидание логина"
        try:
            # Мы получили логин от пользователя, нужно передать их в БД
            conn = SapConnect.get_connection()
            result = conn.call('ZFM_NRA_TGBB_SET_NEW_USER', IV_USER_ID=str(message.from_user.id).zfill(10),
                               IV_SAP_LOGIN=message.text)
            conn.close()

            if result.get('EV_RESULT') == '2':
                # Такой пользователь не зарегистрирован в системе банка
                bankbot.__bot.send_message(message.chat.id,
                                        "Такой пользователь не зарегистрирован в системе банка. "
                                        "Зарегистрируйтесь в банке внутри SAP или проверьте правильность ввода")
                bankbot.__bot.send_message(message.chat.id, "Вы не авторизованы, введите SAP логин")
                return
            if result.get('EV_RESULT') == '3':
                # Такой пользователь уже авторизован в телеграмме
                bankbot.__bot.send_message(message.chat.id,
                                        "Такой пользователь уже авторизован в телеграмме, обратитесь к "
                                        "администратору")
                return
            if result.get('EV_RESULT') == '1':
                # Успешно, обновить список пользователей
                bankbot.users = bankbot.__get_users()
                # Перейти к начальному меню
                # перевести в состояние "Авторизован, ожидаю меню"
                bankbot.states.set_step(message.chat.id, bankbot.states.STEP_MAIN_MENU)
                bankbot.show_start_directory(message)
                return

            bankbot.__bot.send_message(message.chat.id, "Произошла непредвиденная ошибка")
            return
        except (ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError):
            print("Ошибки на стороне SAP")
            bankbot.__bot.send_message(message.chat.id, "Ошибки на стороне SAP")
            bankbot.states.set_step(message.chat.id, bankbot.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(message)


class SearchName:
    @staticmethod
    def process(message, bankbot):
        # Если статус пользователя - "ожидание ограничений логина"
        # удалить лидирующие и замыкающие '?' и '*'
        search_text = message.text
        while len(search_text) > 0 and (search_text[0] == '*' or search_text[0] == '?'):
            search_text = search_text[1:]
        while len(search_text) > 0 and (search_text[-1] == '*' or search_text[-1] == '?'):
            search_text = search_text[:-1]
        bankbot.states.set_name_search(message.chat.id, search_text.upper())
        # Найти последнее отправленное ботом сообщение со списком пользователей и переотправить его
        last_message_id = bankbot.states.get_last_name_list(message.chat.id)
        if last_message_id is not None:
            bankbot.get_bot().delete_message(chat_id=message.chat.id,
                                             message_id=last_message_id)
            bankbot.show_c_rec_name_dir(message)


class FillSum:
    @staticmethod
    def process(message, bankbot):
        # Получили ввод во время ожидания суммы
        try:
            trans = re.split(' ', message.text, maxsplit=1)
            sum_text = trans[0].replace(',', '.')
            if len(sum_text) > 13:
                # Олигархи бл
                raise ValueError
            trans_sum = round(float(sum_text), 2)
            if len(trans) > 1:
                trans_comment = trans[1]
            else:
                trans_comment = ''
            # Сумма успешно получена, передаем данные в SAP
            user_to = bankbot.states.get_receiver_login(message.from_user.id)
            user_from = None
            for user in bankbot.users:
                if user.id == str(message.from_user.id).zfill(10):
                    user_from = user.sap_login
            if trans_sum < 0:
                trans_sum = trans_sum * -1
                user_from, user_to = user_to, user_from
            creator_login = None
            for user in bankbot.users:
                if user.id == str(message.from_user.id).zfill(10):
                    creator_login = user.sap_login
            conn = SapConnect.get_connection()
            result = conn.call('ZFM_NRA_TGBB_CREATE_TRANS',
                               IV_USER_FROM=user_from,
                               IV_USER_TO=user_to,
                               IV_COMMENT=trans_comment,
                               IV_SUM=trans_sum,
                               IV_USER_CREATOR=creator_login)
            conn.close()
            error_text = result.get("EV_ERROR")
            if error_text != '':
                bankbot.__bot.send_message(message.chat.id, error_text)
            else:
                bankbot.__bot.send_message(message.chat.id, "Успешно")
            # Перевести статус в "Авторизован, ожидаю меню"
            bankbot.states.set_step(message.chat.id, bankbot.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(message)

        except ValueError:
            # Ввод не удалось распознать как число
            print("Ввод не удалось распознать как число")
            bankbot.__bot.send_message(message.chat.id, "Не удалось распознать сумму, попробуйте еще раз")
        except (ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError):
            print("Ошибки на стороне SAP")
            bankbot.__bot.send_message(message.chat.id, "Ошибки на стороне SAP")
            bankbot.states.set_step(message.chat.id, bankbot.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(message)