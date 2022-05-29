"""
Работает с этими модулями:
python-telegram-bot==11.1.0
redis==3.2.1
"""
import os
import logging

#import Inline as Inline
import redis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from api_handlers import get_product_catalogue, get_product_by_id, add_product_to_cart, get_cart_items, \
    create_cart_and_get_it_id, get_cart_id, delete_item_from_cart, create_a_customer

_database = None


def show_main_menu(bot, update):

    products = get_product_catalogue()['data']
    keyboard = []
    for product in products:
        product_button = [InlineKeyboardButton(product['name'], callback_data=product['id'])]
        keyboard.append(product_button)
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        update.message.reply_text('Пожалуйста, выберите товар:', reply_markup=reply_markup)

    if update.callback_query.data == 'at_cart':
        chat_id = update['callback_query']['message']['chat']['id']
        get_cart_items(chat_id)

    chat_id = update['callback_query']['message']['chat']['id']
    bot.send_message(chat_id=chat_id, text='Пожалуйста, выберите товар:', reply_markup=reply_markup)


def start(bot, update):
    show_main_menu(bot, update)
    return "HANDLE_MENU"


def handle_menu(bot, update):
    if update.callback_query.data == 'at_cart':
        chat_id = update['callback_query']['message']['chat']['id']
        get_cart_items(chat_id)

    query = update.callback_query
    print(query.data)
    product = get_product_by_id(query.data)['data']
    product_id = product['id']
    message_id = update.callback_query['message']['message_id']

    keyboard = [[InlineKeyboardButton("1", callback_data=f'1 {product_id}'),
                 InlineKeyboardButton("5", callback_data=f'5 {product_id}'),
                 InlineKeyboardButton("10", callback_data=f'10 {product_id}')],
                [InlineKeyboardButton("Назад", callback_data='back')]
                ]

    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_photo(chat_id=query.message.chat_id,
                   photo=open('red_fish.jpg', 'rb'),
                   caption=f"""Предлагаем Вашему вниманию: {product["name"]}
                                  цена: {product["price"][0]["amount"]}{product["price"][0]['currency']}
                                  остатки на складе: {product["meta"]["stock"]["level"]}
                                  описание товара: {product["description"]}""",
                   reply_markup=reply_markup
                   )

    bot.delete_message(chat_id=query.message.chat_id,
                       message_id=message_id)


    return "HANDLE_DESCRIPTION"


def handle_description(bot, update):
    print(f'что прилетело в апдейте: {update.callback_query.data}')
    if update.callback_query.data == 'back':
        products = get_product_catalogue()['data']
        keyboard = []
        for product in products:
            product_button = [InlineKeyboardButton(product['name'], callback_data=product['id'])]
            keyboard.append(product_button)
        keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        chat_id = update['callback_query']['message']['chat']['id']
        bot.send_message(chat_id=chat_id, text='Пожалуйста, выберите товар:', reply_markup=reply_markup)
        return "HANDLE_MENU"


    if update.callback_query.data == 'at_cart':
        print('сработало это условие!')
        cart_id = update.callback_query.message.chat_id
        cart_items = get_cart_items(cart_id)
        print(f'результат вызова функции-гетера товаров {cart_items}')

        def serialized_cart_items(cart_item):
            products = cart_item['data']
            products_data_sets = []
            products_data_sets.append('Dear Customer! In your cart now:')
            for product in products:
                product_dataset = \
                f""" \n {product['name']} \n {product['description']} \n {product['unit_price']['amount']} {product['value']['currency']} for a unit
                In cart {product['quantity']} units for {product['value']['amount']} {product['value']['currency']}"""

                products_data_sets.append(product_dataset)

            products_data_sets.append(f""" \n Total cost of Your cart: {cart_item['meta']['display_price']['with_tax']['amount']}""")
            serialized_cart_items = ' '.join(products_data_sets)
            return serialized_cart_items

        products_in_cart = cart_items['data']

        keyboard = []
        for product_in_cart in products_in_cart:
            delete_product_button = [InlineKeyboardButton(f"Удалить из корзины: {product_in_cart['name']}", callback_data=product_in_cart['id'])]
            keyboard.append(delete_product_button)
        keyboard.append([InlineKeyboardButton('В меню', callback_data='back')])
        keyboard.append([InlineKeyboardButton('Оплатить', callback_data='at_payment')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        cart_items_text = serialized_cart_items(cart_items)
        print(f' Текст карт итем {cart_items_text}')
        #print('Код сработал до отправки сообщения')
        bot.send_message(chat_id=cart_id,
                         text=cart_items_text,
                         reply_markup = reply_markup
                         )
        return "HANDLE_CART"

    else:
        cart_id = update.callback_query.message.chat_id
        print(update.callback_query.data)
        splitted = update.callback_query.data.split()
        print(splitted)
        quantity, product_id = splitted
        print(product_id, cart_id, quantity)
        add_product_to_cart(product_id, cart_id, quantity)


def handle_cart(bot, update):

    if update.callback_query.data == 'at_payment':
        chat_id = update['callback_query']['message']['chat']['id']
        bot.send_message(chat_id=chat_id, text='Пожалуйста, введите Ваш адрес электронной почты:')
        return "WAITING_EMAIL"

    if update.callback_query.data == 'back':
        products = get_product_catalogue()['data']
        keyboard = []
        for product in products:
            product_button = [InlineKeyboardButton(product['name'], callback_data=product['id'])]
            keyboard.append(product_button)
        keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        chat_id = update['callback_query']['message']['chat']['id']
        bot.send_message(chat_id=chat_id, text='Пожалуйста, выберите товар:', reply_markup=reply_markup)

        return "HANDLE_MENU"
    else:
        cart_id = update.callback_query.message.chat_id
        product_in_cart_id = update.callback_query.data

        products_in_cart = get_cart_items(cart_id)['data']
        delete_item_from_cart(cart_id, product_in_cart_id)



def handle_email(bot, update):
    #if is_email(update.message.text):

    customer_first_name = update.message.from_user.first_name
    customer_last_name = update.message.from_user.last_name
    customer_email = update.message.text

    create_a_customer(customer_first_name, customer_last_name, customer_email)


def handle_users_reply(bot, update):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': handle_email,
    }
    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    try:
        next_state = state_handler(bot, update)
        print('Следующее состояние:' + next_state)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = os.getenv("REDIS_PASSWORD")
        database_host = os.getenv("REDIS_HOST")
        database_port = os.getenv("REDIS_PORT")
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    updater = Updater(token)
    logging.info('Бот в Telegram успешно запущен')
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()

