import os
import logging


import redis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext
from api_handlers import get_product_catalogue, get_product_by_id, add_product_to_cart, get_cart_items, \
    delete_item_from_cart, create_new_customer, serialize_products_datasets, get_product_keyboard, get_auth_token, \
    get_file_url


logger = logging.getLogger(__name__)

_database = None
MOLTIN_TOKEN = get_auth_token()


def show_main_menu(update: Update, context: CallbackContext):

    products = get_product_catalogue(MOLTIN_TOKEN)['data']
    keyboard = []
    for product in products:
        product_button = [InlineKeyboardButton(product['name'],
                                               callback_data=product['id'])]
        keyboard.append(product_button)

    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Пожалуйста, выберите товар:',
                             reply_markup=reply_markup)

    return 'HANDLE_MENU'


def show_cart_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    cart_items = get_cart_items(MOLTIN_TOKEN, chat_id)
    products_in_cart = cart_items['data']
    reply_markup = get_product_keyboard(products_in_cart)

    cart_items_text = serialize_products_datasets(cart_items)
    context.bot.send_message(chat_id=chat_id,
                             text=cart_items_text,
                             reply_markup=reply_markup
                             )


def handle_menu(update: Update, context: CallbackContext):

    if update.callback_query.data == 'at_cart':
        show_cart_menu(update, context)
        return 'HANDLE_CART'

    product_id = update.callback_query.data

    keyboard = [[InlineKeyboardButton('1', callback_data=f'{product_id}::1'),
                 InlineKeyboardButton('5', callback_data=f'{product_id}::5'),
                 InlineKeyboardButton('10', callback_data=f'{product_id}::10')],
                [InlineKeyboardButton('Назад', callback_data='back')]
                ]
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])

    product_dataset = get_product_by_id(MOLTIN_TOKEN, product_id)['data']
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_chat.id
    message_id = update.callback_query['message']['message_id']
    product_main_img_id = product_dataset['relationships']['main_image']['data']['id']
    product_main_img_url = get_file_url(MOLTIN_TOKEN, product_main_img_id)
    context.bot.send_photo(chat_id=chat_id,
                           photo=product_main_img_url,
                           caption=f"""
                           Предлагаем Вашему вниманию: {product_dataset['name']} \
                           \nЦена: {product_dataset['price'][0]['amount']}{product_dataset['price'][0]['currency']} \
                           \nОстатки на складе: {product_dataset['meta']['stock']['level']} \
                           \nОписание товара: {product_dataset['description']}
                           """,
                           reply_markup=reply_markup
                           )

    context.bot.delete_message(chat_id=chat_id, message_id=message_id)

    return 'HANDLE_DESCRIPTION'


def handle_description(update: Update, context: CallbackContext):
    message_id = update.callback_query['message']['message_id']
    if update.callback_query.data == 'back':
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        show_main_menu(update, context)
        return 'HANDLE_MENU'

    if update.callback_query.data == 'at_cart':
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        show_cart_menu(update, context)
        return 'HANDLE_CART'

    product_id, quantity = update.callback_query.data.split('::')
    add_product_to_cart(MOLTIN_TOKEN, product_id, update.effective_chat.id, quantity)


def handle_cart(update: Update, context: CallbackContext):
    message_id = update.callback_query['message']['message_id']
    if update.callback_query.data == 'at_payment':
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Пожалуйста, введите Ваш адрес электронной почты:')
        return 'WAITING_EMAIL'

    if update.callback_query.data == 'back':
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        show_main_menu(update, context)
        return 'HANDLE_MENU'

    cart_id = update.effective_chat.id
    product_in_cart_id = update.callback_query.data
    delete_item_from_cart(MOLTIN_TOKEN, cart_id, product_in_cart_id)


def handle_email(update: Update, context: CallbackContext):
    customer_first_name = update.message.from_user.first_name
    customer_last_name = update.message.from_user.last_name
    customer_email = update.message.text
    create_new_customer(MOLTIN_TOKEN, customer_first_name, customer_last_name, customer_email)


def handle_users_reply(update: Update, context: CallbackContext):
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
    chat_id = update.effective_chat.id
    if update.message:
        user_reply = update.message.text
    elif update.callback_query:
        user_reply = update.callback_query.data
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': show_main_menu,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': handle_email,
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(update, context)
    if next_state:
        db.set(chat_id, next_state)


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = os.getenv('REDIS_PASSWORD')
        database_host = os.getenv('REDIS_HOST')
        database_port = os.getenv('REDIS_PORT')
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


if __name__ == '__main__':

    logging.basicConfig(format='TG-bot: %(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    while True:
        try:
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            updater = Updater(token, use_context=True)
            logger.info('Бот в Telegram успешно запущен')
            dispatcher = updater.dispatcher
            dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
            dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
            dispatcher.add_handler(CommandHandler('start', handle_users_reply))
            updater.start_polling()
            updater.idle()

        except Exception as err:
            logging.error('Телеграм бот упал с ошибкой:')
            logging.exception(err)
