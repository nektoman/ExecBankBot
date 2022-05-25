import re
from nekto_man_SapConnect import SapConnect
from pyrfc import ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError


class HandlerChooseLogin:
    @staticmethod
    def process(call, bankbot):
        receiver_fullname = None
        receiver_login = None
        for user in bankbot.users:
            call_text = call.data
            if re.sub(bankbot.R_LOGIN_BUTTON_PREF, '', call_text) == user.sap_login:
                receiver_fullname = user.full_name
                receiver_login = user.sap_login
                break
        # Убрать кнопки
        bankbot.get_bot().edit_message_text(chat_id=call.message.chat.id,
                                            message_id=call.message.message_id,
                                            text="Получатель- "+receiver_fullname)
        # Сохранить получателя
        bankbot.states.set_receiver_login(call.message.chat.id, receiver_login)
        # Перейти к запросу суммы
        # Перевести в состояние- ожидание суммы транзакции
        bankbot.states.set_step(call.message.chat.id, bankbot.states.STEP_WAIT_SUM)
        bankbot.show_sum_req(call.message)


class HandlerLogNavigation:
    @staticmethod
    def process(call, bankbot):
        # Устанавливаем необходимую страницу
        old_page = bankbot.states.get_page(call.message.chat.id)
        if re.search("left_arrow", call.data) is not None:
            bankbot.states.set_page(call.message.chat.id, old_page - 1)
        elif re.search("right_arrow", call.data) is not None:
            bankbot.states.set_page(call.message.chat.id, old_page + 1)
        elif re.search("reset", call.data) is not None:
            bankbot.states.set_name_search(call.message.chat.id, '')
        keyboard = bankbot.get_keyboard_rec(call.message.chat.id)
        bankbot.get_bot().edit_message_text(chat_id=call.message.chat.id,
                                            message_id=call.message.message_id,
                                            text="Выберите получателя или воспользуйтесь поиском",
                                            reply_markup=keyboard)


class HandlerCreateTrans:
    @staticmethod
    def process(call, bankbot):
        # Убрать кнопки
        bankbot.get_bot().edit_message_text(chat_id=call.message.chat.id,
                                            message_id=call.message.message_id,
                                            text="Создать транзакцию")
        # Создать транзакцию
        # Отрисовать кнопки для выбора получателя
        # перевести в состояние "ожидание логина получателя транзакции"(3)
        bankbot.states.set_step(call.message.chat.id, bankbot.states.STEP_WAIT_LOGIN_RECEIVER)
        bankbot.show_c_rec_name_dir(call.message)


class HandlerCheckTrans:
    @staticmethod
    def process(call, bankbot):
        # Убрать кнопки
        bankbot.get_bot().edit_message_text(chat_id=call.message.chat.id,
                                            message_id=call.message.message_id,
                                            text="Просмотреть транзакции")
        # Вывести транзакции
        try:
            conn = SapConnect.get_connection(bankbot.config)
            result = conn.call('ZFM_NRA_TGBB_GET_LAST_TRANSK', IV_USER_ID=str(call.message.chat.id).zfill(10))
            conn.close()
            error = result.get('EV_ERROR')
            if error != '':
                # Возникли предвиденные ошибки
                bankbot.get_bot().send_message(call.message.chat.id, error)
                return

            transactions_list = result.get('ET_TRANS')
            text = "Последние транзакции в которых вы учавствовали:\n" \
                   + "--------------------------------------\n"
            if len(transactions_list) < bankbot.TRANS_IN_CHECK_TRANS:
                count = len(transactions_list)
            else:
                count = bankbot.TRANS_IN_CHECK_TRANS
            for i in range(count):
                line = transactions_list[i]
                summ = str(line.get('SUMM'))
                waers = str(line.get('WAERS'))
                timestamp = str(line.get('TIMESTAMPCRT'))
                timestamp = timestamp[8:10] + ":" + timestamp[10:12] + ":" + timestamp[12:14] + " " + \
                            timestamp[6:8] + "." + timestamp[4:6] + "." + timestamp[0:4]
                reason = str(line.get('REASONCRT'))
                name_from = str(line.get('USERFROM_FULL'))
                name_to = str(line.get('USERTO_FULL'))

                text = text + name_from + " -> " + name_to + " " + summ + " " + waers + "\n" + timestamp

                if reason != '':
                    text = text + "\n  C подписью: " + reason

                text = text + ".\n--------------------------------------\n"

                i = i + 1

            bankbot.get_bot().send_message(call.message.chat.id, text)

            # Успешно, перейти к начальному меню
            # перевести в состояние "Авторизован, ожидаю меню"
            bankbot.states.set_step(call.message.chat.id, bankbot.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(call.message)

        except (ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError):
            print("Ошибки на стороне SAP")
            bankbot.get_bot().send_message(call.message.chat.id, "Ошибки на стороне SAP")
            bankbot.states.set_step(call.message.chat.id, bankbot.self.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(call.message)


class HandlerCheckValet:
    @staticmethod
    def process(call, bankbot):
        # Убрать кнопки
        bankbot.get_bot().edit_message_text(chat_id=call.message.chat.id,
                                            message_id=call.message.message_id,
                                            text="Проверить баланс")
        # Показать Счет
        try:
            conn = SapConnect.get_connection(bankbot.config)
            result = conn.call('ZFM_NRA_TGBB_GET_BALANCEK', IV_USER_ID=str(call.message.chat.id).zfill(10))
            conn.close()
            error = result.get('EV_ERROR')
            if error != '':
                # Возникли ожидаемые ошибки
                bankbot.get_bot().send_message(call.message.chat.id, error)
                return

            # Привожу к нормальному формату: удаляю лидирующие пробелы и переношу знак минуса влево
            balance = result.get('EV_BALANCE')
            balance = balance.lstrip()
            if balance.endswith('-'):
                balance = balance.rstrip('-')
                balance = '-' + balance

            text = "Ваш баланс : " + balance + " руб"
            bankbot.get_bot().send_message(call.message.chat.id, text)

            # Успешно, перейти к начальному меню
            # перевести в состояние "Авторизован, ожидаю меню"
            bankbot.states.set_step(call.message.chat.id, bankbot.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(call.message)

        except (ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError):
            print("Ошибки на стороне SAP")
            bankbot.get_bot().send_message(call.message.chat.id, "Ошибки на стороне SAP")
            bankbot.states.set_step(call.message.chat.id, bankbot.self.states.STEP_MAIN_MENU)
            bankbot.show_start_directory(call.message)


class HandlerMistake:
    @staticmethod
    def process(call, bankbot):
        bankbot.get_bot().delete_message(chat_id=call.message.chat.id,
                                         message_id=call.message.message_id)
        # перевести в состояние "Авторизован, ожидаю меню"
        bankbot.states.set_step(call.message.chat.id, bankbot.states.STEP_MAIN_MENU)
        bankbot.show_start_directory(call.message)


class ButtonHandlerFactory:
    @staticmethod
    def get_handler(call, bankbot):
        if call.message:
            if bankbot.states.get_step(call.message.chat.id) == bankbot.states.STEP_MAIN_MENU:
                if call.data == "create_trans":
                    return HandlerCreateTrans()
                elif call.data == "check_valet":
                    return HandlerCheckValet()
                elif call.data == "check_trans":
                    return HandlerCheckTrans()
                else:
                    return HandlerMistake()
            elif bankbot.states.get_step(call.message.chat.id) == bankbot.states.STEP_WAIT_LOGIN_RECEIVER:
                if re.search(bankbot.R_LOGIN_BUTTON_PREF, call.data) is not None:
                    return HandlerChooseLogin()
                elif re.search(bankbot.R_NAVIGATION_BUTTON_PREF, call.data) is not None:
                    return HandlerLogNavigation()
                else:
                    return HandlerMistake()
            else:
                return HandlerMistake()
