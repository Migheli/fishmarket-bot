import logging
import os
import time
from functools import partial

#import START as START
import products as products
import redis
from textwrap import dedent
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext
from api_handlers import get_product_catalogue, get_product_by_id, add_product_to_cart, get_cart_items, \
    delete_item_from_cart, create_new_customer, serialize_products_datasets, get_product_keyboard, get_token_dataset, \
    get_file_url
from validate_email import validate_email

logger = logging.getLogger(__name__)

_database = None
MAX_PRODUCTS_PER_PAGE = 1


def get_products_datasets(products, max_products_per_page):
    for product in range(0, len(products), max_products_per_page):
        yield products[product:product + max_products_per_page]


def serialize_products_catalogue(products, max_products_per_page):
    products_datasets = list(get_products_datasets(products, max_products_per_page))
    return products_datasets


def get_multipage_keyboard(products_datasets, index_of_page):
    index_of_page = int(index_of_page)
    target_product_dataset = products_datasets[index_of_page]
    keyboard = [[InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in
                target_product_dataset]

    back_products_button = InlineKeyboardButton('Предыдущие товары', callback_data='no_previous_products_page')
    next_products_button = InlineKeyboardButton('Следующие товары', callback_data='no_next_products_page')

    if index_of_page > 0:
        back_products_button = InlineKeyboardButton('Предыдущие товары', callback_data=f"show_products_page::{index_of_page - 1}")
    if index_of_page + 1 < len(products_datasets):
        next_products_button = InlineKeyboardButton('Следующие товары', callback_data=f"show_products_page::{index_of_page + 1}")

    navigation_buttons = [back_products_button, next_products_button]
    keyboard.append(navigation_buttons)
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])
    return InlineKeyboardMarkup(keyboard)


def show_main_menu(update: Update, context: CallbackContext, moltin_token, index_of_page=0):
    products = get_product_catalogue(moltin_token)['data']
    keyboard = [[InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in products]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if len(products) > MAX_PRODUCTS_PER_PAGE:
        products_datasets = serialize_products_catalogue(products, MAX_PRODUCTS_PER_PAGE)
        reply_markup= get_multipage_keyboard(products_datasets, index_of_page)

    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])
    context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='*Пожалуйста*, выберите товар:',
                                 parse_mode=constants.PARSEMODE_MARKDOWN_V2,
                                 reply_markup=reply_markup)

    return 'HANDLE_MENU'

'''
def show_main_menu(update: Update, context: CallbackContext, moltin_token):

    products = get_product_catalogue(moltin_token)['data']
    keyboard = [[InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in products]
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='at_cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Пожалуйста, выберите товар:',
                             reply_markup=reply_markup)

    return 'HANDLE_MENU'
'''

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

    if update.callback_query.data == 'no_previous_products_page':
        update.callback_query.answer('Это первая страница', show_alert=True)
        return 'HANDLE_MENU'

    if update.callback_query.data == 'no_next_products_page':
        update.callback_query.answer('Это последняя страница', show_alert=True)
        return 'HANDLE_MENU'

    if 'show_products_page' in update.callback_query.data:
        text, index_of_page = update.callback_query.data.split('::')
        product_dataset = get_product_catalogue(moltin_token)['data']
        serialized_products_datasets = serialize_products_catalogue(product_dataset, MAX_PRODUCTS_PER_PAGE)
        reply_markup = get_multipage_keyboard(serialized_products_datasets, index_of_page)
        context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                              message_id = update.callback_query['message']['message_id'],
                                              reply_markup=reply_markup)
        return 'HANDLE_MENU'

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
    chat_id = update.effective_chat.id
    message_id = update.callback_query['message']['message_id']

    reply_markup = InlineKeyboardMarkup(keyboard)

    product_main_img_id = product_dataset['relationships']['main_image']['data']['id']
    product_main_img_url = get_file_url(moltin_token, product_main_img_id)

    cart_items = get_cart_items(moltin_token, chat_id)
    products_in_cart = cart_items['data']
    quantity_in_cart = 0
    for product_in_cart in products_in_cart:
        if product_in_cart['product_id'] == product_id:
            quantity_in_cart = product_in_cart['quantity']

    context.bot.send_photo(chat_id=chat_id,
                           photo=product_main_img_url,
                           caption=dedent(f"""\
                           Предлагаем Вашему вниманию: {product_dataset['name']}
                           Цена: {product_dataset['price'][0]['amount']}{product_dataset['price'][0]['currency']}
                           Остатки на складе: {product_dataset['meta']['stock']['level']}
                           Описание товара: {product_dataset['description']}
                           Уже в корзине: {quantity_in_cart}
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
    is_valid = validate_email(customer_email, check_mx=False)
    if is_valid:
        create_new_customer(moltin_token, customer_first_name, customer_last_name, customer_email)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Спасибо. Ваши данные приняты. Мы обработаем Ваш заказ')
        return 'START'
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Кажется, Вы ошиблись в указании почты. Попробуйте еще раз')
    return 'WAITING_EMAIL'

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
