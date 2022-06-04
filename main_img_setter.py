import logging
import os
import requests
from api_handlers import get_auth_token, get_product_catalogue

logger = logging.getLogger(__name__)

MOLTIN_TOKEN = get_auth_token()


def upload_img_and_get_id(moltin_token, url):
    headers = {'Authorization': f'Bearer {moltin_token}'}

    files = {
        'file_location': (None, url),
    }

    response = requests.post('https://api.moltin.com/v2/files',
                             headers=headers,
                             files=files)
    response.raise_for_status()
    return response.json()['data']['id']


def get_product_id_by_name(product_name):
    products = get_product_catalogue(MOLTIN_TOKEN)['data']
    for product in products:
        if product['name'] == product_name:
            return product['id']


def set_main_image_to_product(moltin_token, product_id, file_id):
    headers = {'Authorization': f'Bearer {moltin_token}'}

    json_data = {
        'data': {
            'type': 'main_image',
            'id': file_id,
        },
    }

    response = requests.post(f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image',
                             headers=headers,
                             json=json_data)
    response.raise_for_status()


def set_main_image_by_product_name(url, product_name):
    file_id = upload_img_and_get_id(MOLTIN_TOKEN, url)
    product_id = get_product_id_by_name(product_name)
    set_main_image_to_product(MOLTIN_TOKEN, product_id, file_id)


if __name__ == '__main__':
    try:
        product_name = os.getenv('PRODUCT_NAME')
        img_url = os.getenv('IMG_URL')
        set_main_image_by_product_name(img_url, product_name)
    except Exception as err:
        logging.error('Ошибка в привязке фото к товару:')
        logging.exception(err)