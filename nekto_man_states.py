class UserState:
    def __init__(self, step):
        self.__name_search = ''
        self.__step = step
        self.__page = 0
        self.__last_name_list = None
        self.__receiver_login = None

    def set_step(self, step):
        self.set_name_search('')
        self.__step = step

    def get_step(self):
        return self.__step

    def set_page(self, page):
        self.__page = page

    def get_page(self):
        return self.__page

    def set_name_search(self, name_search):
        self.set_page(0)
        self.__name_search = name_search

    def get_name_search(self):
        return self.__name_search

    def set_last_name_list(self, last_name_list):
        self.__last_name_list = last_name_list

    def get_last_name_list(self):
        return self.__last_name_list

    def set_receiver_login(self, receiver_login):
        self.__receiver_login = receiver_login

    def get_receiver_login(self):
        return self.__receiver_login


class States:
    # Возможные этапы:
    STEP_INIT = 0  # Инициализация
    STEP_WAIT_LOGIN_AUTH = 1  # Ожидание логина
    STEP_MAIN_MENU = 2  # Авторизован, ожидаю меню
    STEP_WAIT_LOGIN_RECEIVER = 3  # Ожидание логина получателя транзакции
    STEP_WAIT_SUM = 4  # Ожидание суммы транзакции

    def __init__(self):
        self.user_states = {}

    def __create_user(self, user):
        new_state = UserState(self.STEP_INIT)
        self.user_states[user] = new_state
        return new_state

    def __get_state(self, user):
        state = self.user_states.get(user)
        if state is None:
            state = self.__create_user(user)
        return state

    def set_step(self, user, step):
        self.__get_state(user).set_step(step)

    def get_step(self, user):
        return self.__get_state(user).get_step()

    def set_page(self, user, page):
        self.__get_state(user).set_page(page)

    def get_page(self, user):
        return self.__get_state(user).get_page()

    def set_name_search(self, user, name_search):
        self.__get_state(user).set_name_search(name_search)

    def get_name_search(self, user):
        return self.__get_state(user).get_name_search()

    def set_last_name_list(self, user, last_name_list):
        self.__get_state(user).set_last_name_list(last_name_list)

    def get_last_name_list(self, user):
        return self.__get_state(user).get_last_name_list()

    def set_receiver_login(self, user, receiver_login):
        self.__get_state(user).set_receiver_login(receiver_login)

    def get_receiver_login(self, user):
        return self.__get_state(user).get_receiver_login()
