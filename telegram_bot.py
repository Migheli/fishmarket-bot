import logging
import os
import time
from functools import partial
import redis
from textwrap import dedent
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext
from api_handlers import get_product_catalogue, get_product_by_id, add_product_to_cart, get_cart_items, \
    delete_item_from_cart, create_new_customer, serialize_products_datasets, get_product_keyboard, get_token_dataset, \
    get_file_url

logger = logging.getLogger(__name__)

_database = None


def show_main_menu(update: Update, context: CallbackContext, moltin_token):

    products = get_product_catalogue(moltin_token)['data']
    keyboard = [[InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in products]
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Пожалуйста, выберите товар:',
                             reply_markup=reply_markup)

    return 'HANDLE_MENU'


def show_cart_menu(update: Update, context: CallbackContext, moltin_token):
    chat_id = update.effective_chat.id
    cart_items = get_cart_items(moltin_token, chat_id)
    products_in_cart = cart_items['data']
    reply_markup = get_product_keyboard(products_in_cart)

    cart_items_text = serialize_products_datasets(cart_items)
    context.bot.send_message(chat_id=chat_id,
                             text=cart_items_text,
                             reply_markup=reply_markup
                             )


def handle_menu(update: Update, context: CallbackContext, moltin_token):

    if update.callback_query.data == 'at_cart':
        show_cart_menu(update, context, moltin_token)
        return 'HANDLE_CART'

    product_id = update.callback_query.data

    keyboard = [[InlineKeyboardButton('1', callback_data=f'{product_id}::1'),
                 InlineKeyboardButton('5', callback_data=f'{product_id}::5'),
                 InlineKeyboardButton('10', callback_data=f'{product_id}::10')],
                [InlineKeyboardButton('Назад', callback_data='back')]
                ]
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])

    product_dataset = get_product_by_id(moltin_token, product_id)['data']
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_chat.id
    message_id = update.callback_query['message']['message_id']
    product_main_img_id = product_dataset['relationships']['main_image']['data']['id']
    product_main_img_url = get_file_url(moltin_token, product_main_img_id)
    context.bot.send_photo(chat_id=chat_id,
                           photo=product_main_img_url,
                           caption=dedent(f"""\
                           Предлагаем Вашему вниманию: {product_dataset['name']}
                           Цена: {product_dataset['price'][0]['amount']}{product_dataset['price'][0]['currency']}
                           Остатки на складе: {product_dataset['meta']['stock']['level']}
                           Описание товара: {product_dataset['description']}
                           """),
                           reply_markup=reply_markup
                           )

    context.bot.delete_message(chat_id=chat_id, message_id=message_id)

    return 'HANDLE_DESCRIPTION'


def handle_description(update: Update, context: CallbackContext, moltin_token):
    message_id = update.callback_query['message']['message_id']
    if update.callback_query.data == 'back':
        show_main_menu(update, context, moltin_token)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        return 'HANDLE_MENU'

    if update.callback_query.data == 'at_cart':
        show_cart_menu(update, context, moltin_token)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        return 'HANDLE_CART'

    product_id, quantity = update.callback_query.data.split('::')
    add_product_to_cart(moltin_token, product_id, update.effective_chat.id, quantity)
    update.callback_query.answer('Товар добавлен в корзину', show_alert=True)

def handle_cart(update: Update, context: CallbackContext, moltin_token):
    message_id = update.callback_query['message']['message_id']
    if update.callback_query.data == 'at_payment':
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Пожалуйста, введите Ваш адрес электронной почты:')
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        return 'WAITING_EMAIL'

    if update.callback_query.data == 'back':
        show_main_menu(update, context, moltin_token)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        return 'HANDLE_MENU'

    cart_id = update.effective_chat.id
    product_in_cart_id = update.callback_query.data
    delete_item_from_cart(moltin_token, cart_id, product_in_cart_id)


def handle_email(update: Update, context: CallbackContext, moltin_token):
    customer_first_name = update.message.from_user.first_name
    customer_last_name = update.message.from_user.last_name
    customer_email = update.message.text
    create_new_customer(moltin_token, customer_first_name, customer_last_name, customer_email)


def handle_users_reply(update: Update, context: CallbackContext, moltin_token_dataset):
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
    moltin_token_dataset = check_token_status(moltin_token_dataset)
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
    next_state = state_handler(update, context, moltin_token_dataset)
    if next_state:
        db.set(chat_id, next_state)


def check_token_status(moltin_token_dataset):
    """
    Проверяет актуальность токена по времени его действия и, в случае необходимости, обновляет его.
    """
    if int(time.time()) >= moltin_token_dataset['expires']:
        moltin_token_dataset = get_token_dataset()
    return moltin_token_dataset


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


def main():

    logging.basicConfig(format='TG-bot: %(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    while True:
        try:
            moltin_token_dataset = get_token_dataset()
            handle_users_reply_token_prefilled = partial(handle_users_reply, moltin_token_dataset=moltin_token_dataset)
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            updater = Updater(token, use_context=True)
            logger.info('Бот в Telegram успешно запущен')
            dispatcher = updater.dispatcher
            dispatcher.add_handler(CallbackQueryHandler(handle_users_reply_token_prefilled))
            dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply_token_prefilled))
            dispatcher.add_handler(CommandHandler('start', handle_users_reply_token_prefilled))
            updater.start_polling()
            updater.idle()

        except Exception as err:
            logging.error('Телеграм бот упал с ошибкой:')
            logging.exception(err)


if __name__ == '__main__':
    main()
