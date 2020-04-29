import vk_api
import requests
import os
from wiki import get_summary
from make_board import create_board
import json
from database import check_id, add_users, use_prompt, check_update
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import random
from io import BytesIO
from screenshot import Map
from PIL import Image
import datetime

vk_session = vk_api.VkApi(
    token=TOKEN)
longpoll = VkBotLongPoll(vk_session, 194275944)
vk = vk_session.get_api()

COUNTER = 0
CORRECT = 0


def get_image():
    with open('cities.txt') as fi:
        cities = fi.read().split('\n')
    city = random.sample(cities, 1)
    while city in used_cities:
        city = random.sample(cities, 1)
    print(city)
    used_cities.append(city)
    n = Map()
    return n.draw_map(city)


def check_register(user_id):
    result = check_id(user_id)
    print(result)
    if result:
        res = True
    else:
        res = False
    return res


def photo(peer_id, user_id):
    global COUNTER, CORRECT
    COUNTER += 1
    if COUNTER > 15:
        text = f'Правильных ответов: {CORRECT} из 15'
        vk.messages.send(user_ids=user_id, message=text,
                         random_id=0, keyboard=json.dumps(keyboard_in_game))
        return
    photo = get_image()
    res = vk.photos.getMessagesUploadServer()
    Image.open(photo).save('result.jpg')
    create_board('result.jpg')
    b = requests.post(res["upload_url"], files={
                      "photo": open('result.jpg', 'rb')}).json()
    c = vk.photos.saveMessagesPhoto(
        photo=b["photo"], server=b["server"], hash=b["hash"])[0]
    res_photo = "photo{}_{}".format(c["owner_id"], c["id"])
    vk.messages.send(user_ids=user_id, peer_id=peer_id, message=f'Вопрос №{COUNTER} из {15}',
                     attachment=res_photo, random_id=0, keyboard=json.dumps(keyboard_in_game))
    os.remove('result.jpg')


def send_message(us_id, msg, keyboard):
    vk.messages.send(user_id=us_id, message=msg,
                     random_id=random.randint(0, 2 ** 64), keyboard=json.dumps(keyboard))


def main():
    global COUNTER, CORRECT
    TOWN = False
    RIVER = False
    WIKI = False
    LEVEL = '-'
    ANSWER = 15
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            response = vk.users.get(user_ids=event.obj.message['from_id'])
            text = event.obj.message['text'].lower()
            user_id = event.obj.message['from_id']

            '''Проверка регистрации пользователя, в случае, если id пользователя
            отсутствует в базе данных - в БД добаляется id, имя, количество подсказок и время последнего обновления'''

            if check_register(user_id):
                pass
            else:
                nickname = response[0]['first_name'] + ' ' + \
                    response[0]['last_name'][0] + '.'
                time = datetime.datetime.now().timestamp()
                add_users(user_id, nickname, 5, int(time))
                send_message(
                    user_id, 'Вы успешно зарегистрированы!', keyboard_main_menu)

            '''Обработка запросов пользователя'''

            if text.rsplit(maxsplit=1)[0] == 'выйти в меню':
                LEVEL = '-'
                TOWN = False
                RIVER = False
                COUNTER = 0
                CORRECT = 0
                WIKI = False
                used_cities.clear()
                send_message(
                    user_id, 'Вы успешно вышли из игры!', keyboard_main_menu)
            elif text == 'города':
                send_message(user_id, 'Выберите сложность: ', keyboard_level)
                TOWN = True
            elif text == 'википедия':
                WIKI = True
                msg = 'Введите объект и мы расскажем Вам о нём! '
                send_message(user_id, msg, keyboard_wiki)
            elif WIKI:
                msg = get_summary(text)
                if msg:
                    send_message(user_id, msg, keyboard_wiki)
                else:
                    msg = 'Кажется, мы всё же знаем не обо всём...'
                    send_message(user_id, msg, keyboard_wiki)
            elif TOWN and LEVEL == '-':
                LEVEL = text
                photo(event.object.peer_id, user_id)
            elif text.split()[0] == 'подсказка':
                length = len(used_cities[-1][0])
                string = length * '_ '
                check_update(user_id)
                ok = use_prompt(user_id)
                if ok == -1:
                    messag = 'У вас больше нет подсказок'
                    send_message(user_id, messag, keyboard_in_game)
                else:
                    messag = f'У вас осталось {ok} подсказок'
                    send_message(user_id, f'Подсказка &#128161;: {string}\n{messag}',
                                 keyboard_in_game)
            elif text == 'пропустить':
                photo(event.object.peer_id, user_id)
            elif TOWN and (LEVEL == 'лёгкий' or LEVEL == 'сложный'):
                if text == used_cities[-1][0].lower():
                    send_message(user_id, f'Верно!', keyboard_in_game)
                    CORRECT = CORRECT + 1
                    photo(event.object.peer_id, user_id)
                else:
                    send_message(user_id, f'Неправильно! Вы можете воспользоваться подсказкой или пропустить вопрос.', keyboard_in_game)


'''
Клавиатура, которая активируется при выборе уровня сложности
'''
keyboard_level = {
    "one_time": True,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Лёгкий"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"2\"}",
                "label": "Сложный"
            },
            "color": "primary"
        }
        ]
    ]
}


'''
Клавиатура, которая активируется во время прохождения уровня
'''
keyboard_in_game = {
    "one_time": False,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Подсказка &#128161;"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"2\"}",
                "label": "Пропустить"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Выйти в меню &#9940;"
            },
            "color": "primary"
        }
        ]
    ]
}

'''Клавиатура, которая активируется в главном меню.'''
keyboard_main_menu = {
    "one_time": False,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Города"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"2\"}",
                "label": "Википедия"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Режимы"
            },
            "color": "primary"
        }
        ],
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"4\"}",
                "label": "Топ игроков"
            },
            "color": "primary"
        }
        ]
    ]
}


keyboard_wiki = {
    "one_time": False,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Подробнее &#128161;"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Выйти в меню &#9940;"
            },
            "color": "primary"
        }
        ]
    ]
}

used_cities = []

if __name__ == '__main__':
    main()
