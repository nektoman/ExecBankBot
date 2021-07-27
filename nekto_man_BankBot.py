from nekto_man_states import States
from nekto_man_BankUser import BankUser
from nekto_man_SapConnect import SapConnect, ABAPRuntimeError, ABAPApplicationError, CommunicationError, LogonError
from nekto_man_ButtonHandlerFactory import ButtonHandlerFactory
from requests.exceptions import ReadTimeout
from requests.exceptions import ConnectionError
from urllib3.exceptions import ReadTimeoutError
from telebot import types
import time
import telebot
import re
import copy
import configparser


class BankBot:
    NAMES_IN_PAGE = 10
    TRANS_IN_CHECK_TRANS = 7
    R_LOGIN_BUTTON_PREF = "R_LOGIN_BUTTON_PREF"
    R_NAVIGATION_BUTTON_PREF = "R_NAVIGATION_BUTTON_PREF"

    def __init__(self):
        self.states = States()
        self.users = self.__get_users()
        config = configparser.ConfigParser()
        config.read('sapnwrfc.cfg')
        self.__bot = telebot.TeleBot(config.get("bot", "token"))
        self.commands = {
            'start': 'Начало работы'
        }

        @self.__bot.message_handler(commands=['start'])
        def start(message):
            # Проверить текущего пользователя в списке пользователей
            print("start for "+str(message.chat.id).zfill(10))
            for element in self.users:
                if element.id == str(message.chat.id).zfill(10):
                    # Перейти к начальному меню
                    # перевести в состояние "Авторизован, ожидаю меню"
                    self.states.set_step(message.chat.id, self.states.STEP_MAIN_MENU)
                    self.show_start_directory(message)
                    return
            # Пользователя нет- он не зарегестрирован - требуется авторизация
            self.__bot.send_message(message.chat.id, "Вы не авторизованы, введите SAP логин")
            # перевести в состояние "ожидание логина"
            self.states.set_step(message.from_user.id, self.states.STEP_WAIT_LOGIN_AUTH)

        @self.__bot.message_handler(commands=['refresh_users'])
        def refresh(message):
            self.users = self.__get_users()


        # Ввод логина(авторизация)
        @self.__bot.message_handler(content_types=["text"])
        def set_login(message):
            if self.states.get_step(message.from_user.id) == self.states.STEP_WAIT_LOGIN_AUTH:
                # Если статус пользователя - "ожидание логина"
                try:
                    # Мы получили логин от пользователя, нужно передать их в БД
                    conn = SapConnect.get_connection()
                    result = conn.call('ZFM_NRA_TGBB_SET_NEW_USER', IV_USER_ID=str(message.from_user.id).zfill(10),
                                       IV_SAP_LOGIN=message.text)
                    conn.close()

                    if result.get('EV_RESULT') == '2':
                        # Такой пользователь не зарегистрирован в системе банка
                        self.__bot.send_message(message.chat.id,
                                                "Такой пользователь не зарегистрирован в системе банка. "
                                                "Зарегистрируйтесь в банке внутри SAP или проверьте правильность ввода")
                        self.__bot.send_message(message.chat.id, "Вы не авторизованы, введите SAP логин")
                        return
                    if result.get('EV_RESULT') == '3':
                        # Такой пользователь уже авторизован в телеграмме
                        self.__bot.send_message(message.chat.id,
                                                "Такой пользователь уже авторизован в телеграмме, обратитесь к "
                                                "администратору")
                        return
                    if result.get('EV_RESULT') == '1':
                        # Успешно, обновить список пользователей
                        self.users = self.__get_users()
                        # Перейти к начальному меню
                        # перевести в состояние "Авторизован, ожидаю меню"
                        self.states.set_step(message.chat.id, self.states.STEP_MAIN_MENU)
                        self.show_start_directory(message)
                        return

                    self.__bot.send_message(message.chat.id, "Произошла непредвиденная ошибка")
                    return
                except (ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError):
                    print("Ошибки на стороне SAP")
                    self.__bot.send_message(message.chat.id, "Ошибки на стороне SAP")
                    self.states.set_step(message.chat.id, self.states.STEP_MAIN_MENU)
                    self.show_start_directory(message)
            elif self.states.get_step(message.from_user.id) == self.states.STEP_WAIT_LOGIN_RECEIVER:
                # Если статус пользователя - "ожидание ограничений логина"
                # удалить лидирующие и замыкающие '?' и '*'
                search_text = message.text
                while len(search_text) > 0 and (search_text[0] == '*' or search_text[0] == '?'):
                    search_text = search_text[1:]
                while len(search_text) > 0 and (search_text[-1] == '*' or search_text[-1] == '?'):
                    search_text = search_text[:-1]
                self.states.set_name_search(message.chat.id, search_text.upper())
                # Найти последнее отправленное ботом сообщение со списком пользователей и переотправить его
                last_message_id = self.states.get_last_name_list(message.chat.id)
                if last_message_id is not None:
                    self.get_bot().delete_message(chat_id=message.chat.id,
                                                  message_id=last_message_id)
                    self.show_c_rec_name_dir(message)
            elif self.states.get_step(message.from_user.id) == self.states.STEP_WAIT_SUM:
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
                    user_to = self.states.get_receiver_login(message.from_user.id)
                    user_from = None
                    for user in self.users:
                        if user.id == str(message.from_user.id).zfill(10):
                            user_from = user.sap_login
                    if trans_sum < 0:
                        trans_sum = trans_sum * -1
                        user_from, user_to = user_to, user_from
                    creator_login = None
                    for user in self.users:
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
                        self.__bot.send_message(message.chat.id, error_text)
                    else:
                        self.__bot.send_message(message.chat.id, "Успешно")
                    # Перевести статус в "Авторизован, ожидаю меню"
                    self.states.set_step(message.chat.id, self.states.STEP_MAIN_MENU)
                    self.show_start_directory(message)

                except ValueError:
                    # Ввод не удалось распознать как число
                    print("Ввод не удалось распознать как число")
                    self.__bot.send_message(message.chat.id, "Не удалось распознать сумму, попробуйте еще раз")
                except (ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError):
                    print("Ошибки на стороне SAP")
                    self.__bot.send_message(message.chat.id, "Ошибки на стороне SAP")
                    self.states.set_step(message.chat.id, self.states.STEP_MAIN_MENU)
                    self.show_start_directory(message)

        # Нажатие на кнопку
        @self.__bot.callback_query_handler(func=lambda call: True)
        def callback_handle(call):
            ButtonHandlerFactory.get_handler(call, self).process(call, self)

    def show_start_directory(self, message):
        # Пользователь авторизован, показать меню
        keyboard = types.InlineKeyboardMarkup()

        check_valet_button = types.InlineKeyboardButton(text="Проверить баланс", callback_data="check_valet")
        create_trans_button = types.InlineKeyboardButton(text="Создать транзакцию", callback_data="create_trans")
        check_trans_button = types.InlineKeyboardButton(text="Проверить последние транзакции",
                                                        callback_data="check_trans")

        keyboard.add(create_trans_button)
        keyboard.add(check_valet_button)
        keyboard.add(check_trans_button)

        self.__bot.send_message(message.chat.id, "Выберите действие", reply_markup=keyboard)

    def show_sum_req(self, message):
        self.__bot.send_message(message.chat.id, "Введите сумму транзакции, через пробел можно добавить описание")

    def show_c_rec_name_dir(self, message):
        keyboard = self.get_keyboard_rec(message.chat.id)
        new_message = self.__bot.send_message(message.chat.id,
                                              "Выберите получателя или воспользуйтесь поиском",
                                              reply_markup=keyboard)
        self.states.set_last_name_list(message.chat.id, new_message.id)

    def get_keyboard_rec(self, for_user):
        keyboard = types.InlineKeyboardMarkup()
        # Получить список для показа
        name_list_to_show, is_roll_left, is_roll_right = self.__get_current_name_list(for_user)
        # Кнопки с именами пользователей
        for user in name_list_to_show:
            keyboard.add(types.InlineKeyboardButton(text=user.full_name,
                                                    callback_data=self.R_LOGIN_BUTTON_PREF + user.sap_login))
        # Кнопки навигации
        # Левая стрелка\заглушка
        # Если влево еще есть куда листать
        if is_roll_left:
            button_left_nav = types.InlineKeyboardButton(text="◀",
                                                         callback_data=self.R_NAVIGATION_BUTTON_PREF + "left_arrow")
        else:
            button_left_nav = None

        # Правая стрелка\заглушка
        # Если вправо еще есть куда листать
        if is_roll_right:
            button_right_nav = types.InlineKeyboardButton(text="▶",
                                                          callback_data=self.R_NAVIGATION_BUTTON_PREF + "right_arrow")
        else:
            button_right_nav = None

        if button_left_nav is not None:
            if button_right_nav is not None:
                # Добавить кнопочки в ряд
                keyboard.row(button_left_nav, button_right_nav)
            else:
                keyboard.add(button_left_nav)
        elif button_right_nav is not None:
            keyboard.add(button_right_nav)

        return keyboard

    def __get_current_name_list(self, for_user):
        current_name_list = []
        # Получить весь список с ограничением по имени
        name_list_with_search = self.__get_users_list_with_search(for_user)

        # Получить список для текущей страницы
        current_position = self.states.get_page(for_user) * self.NAMES_IN_PAGE
        if len(name_list_with_search) <= (current_position + self.NAMES_IN_PAGE):
            end_position = len(name_list_with_search)
            is_roll_right = False
        else:
            end_position = current_position + self.NAMES_IN_PAGE
            is_roll_right = True

        while current_position < end_position:
            current_name_list.append(name_list_with_search[current_position])
            current_position = current_position + 1
        if self.states.get_page(for_user) == 0:
            is_roll_left = False
        else:
            is_roll_left = True
        return current_name_list, is_roll_left, is_roll_right

    def __get_users_list_with_search(self, for_user):
        # Исключить самого пользователя
        all_users = copy.deepcopy(self.users)
        for user in all_users:
            if user.id == str(for_user).zfill(10):
                all_users.remove(user)
                break
        # Оставить пользователей подходящих по маске, если маска не пуста
        name_search = self.states.get_name_search(for_user)
        if name_search == '':
            # Если поисковый запрос не заполнен- ничего не меняем
            users_list_with_search = all_users
        else:
            # Если поисковый запрос заполнен- возвращаем только те записи в которых есть вхождение искомой строки
            users_list_with_search = []
            for user in all_users:
                if re.search(name_search, user.full_name.upper()) is not None:
                    temp = re.search(name_search, user.full_name.upper())
                    users_list_with_search.append(user)
        return users_list_with_search

    def __get_users(self):
        try:
            conn = SapConnect.get_connection()

            result = conn.call('ZFM_NRA_TGBB_GET_USERS')
            conn.close()
            raw_users_list = result.get('ET_USERS')
            users_list = []
            for element in raw_users_list:
                users_list.append(BankUser(element.get('UNAME'), element.get('FULLNAME'), element.get('TG_ID')))

            return users_list
        except (ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError):
            print("Ошибки на стороне SAP, не удалось получить список пользователей")

    def run(self):
        while True:
            try:
                print("Server up")
                self.__bot.polling()
            except ConnectionError:
                print("Server down: ConnectionError")
                time.sleep(5)
                continue
            except (ReadTimeoutError, ReadTimeout):
                print("Server down: ReadTimeoutError")
                time.sleep(5)
                continue

    def get_bot(self):
        return self.__bot
