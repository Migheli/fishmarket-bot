import logging
import os
import requests
from api_handlers import get_auth_token, get_product_catalogue

logger = logging.getLogger(__name__)


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


def get_product_id_by_name(products, product_name):
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


def main():
    try:
        moltin_token = get_auth_token()
        product_name = os.getenv('PRODUCT_NAME')
        img_url = os.getenv('IMG_URL')
        file_id = upload_img_and_get_id(moltin_token, img_url)
        products = get_product_catalogue(moltin_token)['data']
        product_id = get_product_id_by_name(products, product_name)
        set_main_image_to_product(moltin_token, product_id, file_id)
    except Exception as err:
        logging.error('Ошибка в привязке фото к товару:')
        logging.exception(err)


if __name__ == '__main__':
    main()
