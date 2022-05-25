import re
from nekto_man_SapConnect import SapConnect, ABAPRuntimeError, ABAPApplicationError, CommunicationError, LogonError
from sap_model import ConnectError, set_new_user, create_trans

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
            result = set_new_user(bankbot.config, message.from_user.id, message.text)
        except ConnectError:
            bankbot.get_bot().send_message(message.chat.id, "Ошибки на стороне SAP")
            bankbot.states.set_step(message.chat.id, bankbot.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(message)
            return

        res_code = result.get('EV_RESULT')
        if res_code == '2':
            # Такой пользователь не зарегистрирован в системе банка
            bankbot.get_bot().send_message(message.chat.id,
                                    "Такой пользователь не зарегистрирован в системе банка. "
                                    "Зарегистрируйтесь в банке внутри SAP или проверьте правильность ввода")
            bankbot.get_bot().send_message(message.chat.id, "Вы не авторизованы, введите SAP логин")
        elif res_code == '3':
            # Такой пользователь уже авторизован в телеграмме
            bankbot.get_bot().send_message(message.chat.id,
                                    "Такой пользователь уже авторизован в телеграмме, обратитесь к "
                                    "администратору")
        elif res_code == '1':
            # Успешно, обновить список пользователей
            bankbot.refresh()
            # Перейти к начальному меню
            # перевести в состояние "Авторизован, ожидаю меню"
            bankbot.states.set_step(message.chat.id, bankbot.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(message)
        else:
            bankbot.get_bot().send_message(message.chat.id, "Произошла непредвиденная ошибка")


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
            try:
                result = create_trans(bankbot.config, user_from, user_to, trans_comment, trans_sum, creator_login)
            except ConnectError:
                bankbot.get_bot().send_message(message.chat.id, "Ошибки на стороне SAP")
                bankbot.states.set_step(message.chat.id, bankbot.states.STEP_MAIN_MENU)
                bankbot.show_start_directory(message)
                return

            if result.get("EV_ERROR") != '':
                bankbot.get_bot().send_message(message.chat.id, result.get("EV_ERROR"))
            else:
                bankbot.get_bot().send_message(message.chat.id, "Успешно")
            # Перевести статус в "Авторизован, ожидаю меню"
            bankbot.states.set_step(message.chat.id, bankbot.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(message)

        except ValueError:
            # Ввод не удалось распознать как число
            print("Ввод не удалось распознать как число")
            bankbot.get_bot().send_message(message.chat.id, "Не удалось распознать сумму, попробуйте еще раз")

