import requests
import os


def get_auth_token():
    data = {
        'client_id': os.getenv('MOLTIN_CLIENT_ID'),
        'client_secret': os.getenv('MOLTIN_CLIENT_SECRET'),
        'grant_type': 'client_credentials',
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    oauth_token = response.json()['access_token']
    return oauth_token


TOKEN = get_auth_token()


def get_product_catalogue():

    headers = {'Authorization': f'Bearer {TOKEN}'}
    response = requests.get('https://api.moltin.com/v2/products', headers=headers)
    answer = response.json()
    print(answer)
    return answer

#get_product_catalogue()

def get_product_by_id(id):
    headers = {'Authorization': f'Bearer {TOKEN}',
               }

    response = requests.get(f'https://api.moltin.com/v2/products/{id}', headers=headers)
    return response.json()


def add_product_to_cart(product_id, cart_id, quantity):
    headers = {'Authorization': f'Bearer {TOKEN}'}

    json_data = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': int(quantity),
        },
    }

    response = requests.post(f'https://api.moltin.com/v2/carts/{cart_id}/items', headers=headers, json=json_data)
    print(f'В КОРЗИНУ ПОЛОЖЕНО: {response.json()}')

    #serialized_response = response.json()


red_fish_id = '450802f5-c8c6-43b7-a52a-c7132bb62a2a'


def create_cart_and_get_it_id(cart_name):
    headers = {'Authorization': f'Bearer {TOKEN}'}

    json_data = {
        'data': {
            'name': cart_name,
        },
    }

    response = requests.post('https://api.moltin.com/v2/carts', headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()['data']['id']


my_cart_id = create_cart_and_get_it_id('228686255')


def get_cart_id(cart_name):
    headers = {'Authorization': f'Bearer {TOKEN}'}
    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_name}', headers=headers)
    response.raise_for_status()
    return response.json()['data']['links']['self']

add_product_to_cart(red_fish_id, my_cart_id, 1)


def get_cart_items(cart_id):

    headers = {'Authorization': f'Bearer {TOKEN}'}
    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}/items', headers=headers)
    response.raise_for_status()
    serialized_response = response.json()
    print(f'Товары в корзине: {serialized_response}')
    return serialized_response


def delete_item_from_cart(cart_id, cart_item_id):

    headers = {'Authorization': f'Bearer {TOKEN}'}
    response = requests.delete(f'https://api.moltin.com/v2/carts/{cart_id}/items/{cart_item_id}', headers=headers)
    response.raise_for_status()


def create_a_customer(first_name, last_name, email):

    headers = {'Authorization': f'Bearer {TOKEN}'}

    json_data = {
        'data': {
            'type': 'customer',
            'name': f'{first_name} {last_name}',
            'email': f'{email}',
            #'password': 'mysecretpassword',
        },
    }

    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=json_data)
    response.raise_for_status()
    current_id = response.json()['data']['id']
    print(current_id)

    response = requests.get(f'https://api.moltin.com/v2/customers/{current_id}', headers=headers)
    response.raise_for_status()
    print(response.json())


#def get_customer_id()

def upload_and_get_file_id(url):
    headers = {'Authorization': f'Bearer {TOKEN}'}

    files = {
        'file': open(url, 'rb'),
        'public': (None, 'true'),
              }

    response = requests.post('https://api.moltin.com/v2/files', headers=headers, files=files)
    response.raise_for_status()
    return response.json()['data']['id']

def upload_img_and_get_id(url):
    headers = {'Authorization': f'Bearer {TOKEN}'
               }

    files = {
        'file_location': (None, url),
    }

    response = requests.post('https://api.moltin.com/v2/files', headers=headers, files=files)
    response.raise_for_status()
    print(response.json()['data']['id'])
    return response.json()['data']['id']


red_fish_img_url = 'https://img.povar.ru/main/9e/5a/19/65/krasnaya_riba_na_skovorode-133692.jpg'
red_fish_img_id = upload_img_and_get_id(red_fish_img_url)


def set_image_to_product(product_id, file_id):
    headers = {'Authorization': f'Bearer {TOKEN}'}

    json_data = {
        'data': {
            'type': 'main_image',
            'id': file_id,
        },
    }

    response = requests.post(f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image', headers=headers,
                             json=json_data)
    response.raise_for_status()


set_image_to_product(red_fish_id, red_fish_img_id)


def get_id_of_product_file(product_id):
    headers = {'Authorization': f'Bearer {TOKEN}'}

    json_data = {
        'data': [
            {
                'type': 'file',
                'id': '82c51711-35f9-403e-aa73-8e6c80c2258b',
            },
        ],
    }

    response = requests.post(f'https://api.moltin.com/v2/products/{product_id}/relationships/files', headers=headers,
                             json=json_data)


def get_file_url(file_id):
    headers = {'Authorization': f'Bearer {TOKEN}'}

    response = requests.get(f'https://api.moltin.com/v2/files/{file_id}', headers=headers)
    response.raise_for_status()
    img_file_url = response.json()['data']['link']['href']
    return img_file_url


def download_img(img_url, path_to_save):
    response = requests.get(img_url)
    response.raise_for_status()
    with open(path_to_save, 'wb') as file:
        file.write(response.content)


download_img(get_file_url(red_fish_img_id), 'red_fish.jpg')