# Fish-market-bot

Запускаем бота-магазин для Telegram на Python с использованием БД Redis и Moltin

### Как установить

Python3 должен быть уже установлен. Затем используйте pip для установки зависимостей:
```
pip install -r requirements.txt
```

### Перед запуском 

##### Переменные окружения и их настройка
В проекте будут использованы следующие переменные окружения:  
`MOLTIN_CLIENT_SECRET`
`MOLTIN_STORE_ID`
`MOLTIN_CLIENT_ID`
`TELEGRAM_BOT_TOKEN`
`REDIS_HOST`
`REDIS_PORT`
`REDIS_DB`
`REDIS_PASSWORD`
`PRODUCT_NAME`
`IMG_URL`
 
Данные переменные должны быть прописаны в файле с именем `.env`, лежащим в корневом каталоге проекта.
Подробнее о том, какие значения присвоить каждой из них в инструкции далее.


##### 1. Создаем учетную запись Moltin
Используем данные Вашей учетной записи для заполнения переменных окружения файла `.env` проекта:: 

```
`MOLTIN_CLIENT_SECRET`='YOUR_MOLTIN_CLIENT_SECRET'
`MOLTIN_STORE_ID`='YOUR_MOLTIN_STORE_ID'
`MOLTIN_CLIENT_ID`='YOUR_MOLTIN_CLIENT_ID'
```

##### 2. Создаем телеграмм чат-бота. 
Инструкция по регистрации бота и получению токена здесь: https://smmplanner.com/blog/otlozhennyj-posting-v-telegram/ или здесь: https://habr.com/ru/post/262247/.
Кратко: просто напишите в телеграмм боту @BotFather и следуйте его инструкциям. 
Полученный токен сохраните в переменную `TG_BOT_TOKEN` файла `.env` проекта:
```
TG_BOT_TOKEN='YOUR_TELEGRAM_BOT_TOKEN'
```



##### 3. Создаем базу данных Redis. 
Переходим по ссылке: https://redislabs.com/

Адрес Вашей БД до двоеточия укажите в переменную:
`REDIS_HOST`
Порт пишется прямо в адресе, через двоеточие. Впишите его в переменную окружения:
`REDIS_PORT`
Переменную окружения `REDIS_DB` по умолчанию укажите равной "0".
Пароль от базы данных укажите в переменную окружения:
`REDIS_PASSWORD`
##### 4. Создаем товары в Moltin
Создаем "продукты", которые будут продаваться в нашем боте.
Для этого переходим по ссылке: https://euwest.cm.elasticpath.com/app/catalogue/products
Вместо SKU в тестовой версии можно поставить любое значение

##### 4. "Прикручиваем" изображения продуктов по их названию
В проекте предусмотрен специальный скрипт
`main_image_setter.py`
запуск которого "прикручивает" главное изображение товара (которое будет отправляться пользователю) к созданному Вами в Moltin товару.
Чтобы осуществить такую привязку кладем для каждого целевого товара его product_name в переменную окружения
`PRODUCT_NAME`
и url картинки в переменную окружения
`IMG_URL`
"Под капотом" скрипт `main_image_setter.py` загрузит картинку на сервер Moltin и привяжет ее к товару с указанным в переменной 
`PRODUCT_NAME` именем.
Данный шаг обязателен, в противном случае бот не сможет отправить сообщение с фото товара.

### Тестовый запуск (без деплоя)
Теперь, когда мы заполнили все требуемые переменные окружения можно приступать к запуску бота.
В тестовом режиме (без деплоя) скрипт бота запускается простым выполнением команды из терминала:

```  
$python telegram_bot.py
```  

### Примеры работы ботов
Пример работы бота:

<img src="https://i.ibb.co/WHWNkwj/Tg-bot.gif">

#### Ссылка на задеплоенный тестовый бот:

Телеграм: 
https://t.me/dvmn_quiz_telebot

### Деплоим проект с помощью Heroku
Необязательный шаг. Бот может работать и непосредственно на Вашем сервере (при наличии такового). 
Чтобы развернуть наш бот на сервере бесплатно можно использовать сервис Heroku https://heroku.com. Инструкция по деплою здесь: https://ru.stackoverflow.com/questions/896229/%D0%94%D0%B5%D0%BF%D0%BB%D0%BE%D0%B9-%D0%B1%D0%BE%D1%82%D0%B0-%D0%BD%D0%B0-%D1%81%D0%B5%D1%80%D0%B2%D0%B5%D1%80%D0%B5-heroku или здесь (инструкция для ВК-приложений на Python, но все работает аналогично): https://blog.disonds.com/2017/03/20/python-bot-dlya-vk-na-heroku/ 
Важно отметить, что создать приложение на Heroku можно и без использования Heroku CLI, но оно будет крайне полезно для сбора наших логов.

Кратко:

создаем и или используем существующий аккаунт GitHub https://github.com/;
"клонируем" данный репозиторий к себе в аккаунт;
регистрируемся в Heroku и создаем приложение по инструкции выше;
"привязываем" учетную запись GitHub к учетной записи Heroku;
в качестве репозитория в Deployment Method на странице Deploy Вашего приложения в Heroku указываем GitHub и добавляем ссылку на данный репозиторий;
запускаем бота на сервере, нажав кнопку connect.

### Цель проекта
Код написан в образовательных целях на онлайн-курсе для веб-разработчиков dvmn.org.