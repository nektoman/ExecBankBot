import telebot

"""
class Biba:
    class Boba:
        def __init__(self, parent):
            self.boba_attribute = parent.biba_attribute

    def __init__(self):
        self.biba_attribute = 1
        self.boba_object = Boba(self)
"""
""""
bot = telebot.TeleBot("token")


@bot.callback_query_handler(func=lambda call: True)
def callback_handle(call):
    print("do smth")
    """


class Clazz:
    def __init__(self):
        self.bot = telebot.TeleBot("token")

        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handle(call):
            print("Этот метод будет обернут в декоратор callback_query_handler")


